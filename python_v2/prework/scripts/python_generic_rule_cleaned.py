#!/usr/bin/env python3
"""
Python Generic Rule Engine

A generic rule engine that can apply any rule based on JSON metadata to Python AST.
Handles AST traversal, rule applicability checking, and pattern matching.
"""

import re
import ast
import json
from typing import Any, Dict, List, Optional, Union

def collect_leaf_properties(obj, parent_path=None):
    """
    Recursively collect all leaf properties in a dict/list, returning a dict of {full_path: value}.
    Handles dicts, lists, and primitive values.
    """
    if parent_path is None:
        parent_path = []
    leaves = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            leaves.update(collect_leaf_properties(v, parent_path + [k]))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            leaves.update(collect_leaf_properties(item, parent_path + [f"[{idx}]"]))
    else:
        # Primitive value
        path_str = '.'.join(parent_path).replace('.[', '[')
        leaves[path_str] = obj
    return leaves


import ast
import json
import logic_implementations


class PythonGenericRule:
    """
    Generic rule engine for Python AST processing.
    
    Adapts generic rule concepts to Python:
    - node_type instead of resource_type (ClassDef, FunctionDef, etc.)
    - AST traversal instead of Terraform block navigation
    - Property path navigation through AST node attributes
    """

    def __init__(self, metadata):
        self.metadata = metadata
        self.logic = metadata.get("logic", {})
        self.rule_id = metadata.get("rule_id", "unknown_rule")
        self.message = metadata.get("title", "Rule violation")

    # ========== CUSTOM LOGIC FUNCTIONS ==========
    # All custom check functions are now in logic_implementations.py
    # They are dynamically loaded via _get_custom_function method below





    def _get_custom_function(self, function_name):
        """Get a custom function by name from logic_implementations module."""
        if function_name is None:
            return None
        
        # First check the logic_implementations module
        if hasattr(logic_implementations, function_name):
            return getattr(logic_implementations, function_name)
        
        # Fallback to check this class (for backward compatibility)
        if hasattr(self, function_name):
            return getattr(self, function_name)
        
        return None
    # ========== END CUSTOM LOGIC FUNCTIONS ==========

    def _get_properties_with_wildcard(self, obj, prop_path):
        """
        Recursively traverse obj following prop_path, supporting '*' as a wildcard for lists.
        Returns a list of (full_path, value) tuples found at the end of the path.
        Includes deduplication to avoid overcounting.
        """
        def helper(current, path, acc):
            if not path:
                return [(acc, current)]
            key = path[0]
            rest = path[1:]
            results = []
            seen_paths = set()  # Track seen paths to avoid duplicates
            
            if key == "*":
                if isinstance(current, list):
                    for idx, item in enumerate(current):
                        new_acc = acc + [f"[{idx}]"]
                        path_str = '.'.join(str(p) for p in new_acc).replace('.[', '[')
                        if path_str not in seen_paths:
                            seen_paths.add(path_str)
                            results.extend(helper(item, rest, new_acc))
                elif isinstance(current, dict):
                    for k, v in current.items():
                        if k not in ['lineno', 'col_offset', 'node_type']:  # Skip AST metadata
                            new_acc = acc + [k]
                            path_str = '.'.join(str(p) for p in new_acc)
                            if path_str not in seen_paths:
                                seen_paths.add(path_str)
                                results.extend(helper(v, rest, new_acc))
            elif isinstance(current, dict) and key in current:
                new_acc = acc + [key]
                results.extend(helper(current[key], rest, new_acc))
            elif isinstance(current, list):
                # Only traverse list if we haven't seen this path before
                for idx, item in enumerate(current):
                    path_str = '.'.join(str(p) for p in acc + [f"[{idx}]"])
                    if path_str not in seen_paths:
                        seen_paths.add(path_str)
                        results.extend(helper(item, path, acc + [f"[{idx}]"]))
            return results
        return helper(obj, prop_path, [])

    def _find_nodes_by_type(self, ast_tree, node_types):
        """
        Find all nodes of specified types in the Python AST.
        Normalizes Constant and Str nodes to avoid double-counting the same string values.
        """
        found_nodes = []
        seen_string_values = set()  # Track string values to avoid Constant/Str duplicates
        
        def traverse(node):
            if isinstance(node, dict):
                current_type = node.get('node_type')
                
                # Normalize Constant and Str to avoid duplicates
                if current_type in ['Constant', 'Str'] and any(t in ['Constant', 'Str'] for t in node_types):
                    value = node.get('value')
                    if isinstance(value, str):
                        # Create a unique key for this string value at this location
                        location_key = (value, node.get('lineno', 0), node.get('col_offset', 0))
                        if location_key not in seen_string_values:
                            seen_string_values.add(location_key)
                            # Only add if node type matches what we're looking for
                            if current_type in node_types:
                                found_nodes.append(node)
                    elif current_type in node_types:
                        # Non-string constant, add normally
                        found_nodes.append(node)
                elif current_type in node_types:
                    found_nodes.append(node)
                
                # Recursively traverse children
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        if isinstance(value, (dict, list)):
                            traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(ast_tree)
        return found_nodes

    def is_applicable(self, ast_tree):
        """
        Returns True if the AST contains at least one node of the rule's node_type
        and at least one property_path exists in any such node, using wildcard-aware traversal.
        If node_type or property_path is '*', treat as always applicable.
        """
        logic = self.logic
        node_types = logic.get("node_type", [])
        property_paths = logic.get("property_path", [])
        
        if node_types == "*" or property_paths == "*":
            return True
            
        check_type = self.logic.get("check_type", "")
        
        # Find all nodes of specified types in the AST
        target_nodes = self._find_nodes_by_type(ast_tree, node_types)
        
        for node in target_nodes:
            # For required_present, always applicable if node_type matches
            if check_type == "required_present":
                return True
            for prop_path in property_paths:
                prop_path_list = prop_path if isinstance(prop_path, list) else [prop_path]
                matches = self._get_properties_with_wildcard(node, prop_path_list)
                if matches:
                    return True
        return False

    def check(self, ast_tree, filename):
        """
        Apply the rule to the Python AST and return findings.
        """
        findings = []
        seen_findings = set()  # Deduplication set: (rule_id, file, line, property_path_str)
        logic = self.logic
        node_types = logic.get("node_type", [])  # Changed from resource_type
        property_paths = logic.get("property_path", [])
        check_type = logic.get("check_type", "")
        forbidden_values = logic.get("forbidden_values", [])
        required_values = logic.get("required_values", [])
        regex_pattern = logic.get("regex", None)

        # Find all relevant nodes in the AST
        if node_types == "*":
            target_nodes = [ast_tree]  # Process entire AST
        else:
            target_nodes = self._find_nodes_by_type(ast_tree, node_types)

        for node in target_nodes:
            node_type = node.get('node_type', 'Unknown')
            node_name = node.get('name', 'anonymous')
            
            if check_type == "custom":
                custom_func = logic.get("function") or logic.get("custom_function")
                
                # Use internal custom functions
                func = self._get_custom_function(custom_func)
                if func and func(node):
                    finding = self._make_finding(
                        filename, node_type, node_name, [], None, 
                        self.message, node
                    )
                    # Create unique key for deduplication
                    unique_key = (
                        self.rule_id, 
                        filename, 
                        finding.get('line', 0), 
                        str(finding.get('property_path', []))
                    )
                    if unique_key not in seen_findings:
                        seen_findings.add(unique_key)
                        findings.append(finding)
                continue
                
            for prop_path in property_paths:
                # Ensure prop_path_list is always a list
                if isinstance(prop_path, list):
                    prop_path_list = prop_path
                elif isinstance(prop_path, str):
                    prop_path_list = [prop_path]
                else:
                    continue
                    
                matches = self._get_properties_with_wildcard(node, prop_path_list)
                
                if check_type == "required_present" and not matches:
                    # Property is missing entirely
                    finding = self._make_finding(
                        filename, node_type, node_name, prop_path_list, 
                        None, "Required property missing", node
                    )
                    unique_key = (
                        self.rule_id, 
                        filename, 
                        finding.get('line', 0), 
                        str(prop_path_list)
                    )
                    if unique_key not in seen_findings:
                        seen_findings.add(unique_key)
                        findings.append(finding)
                    
                for found_path, value in matches:
                    # Apply check_type logic
                    finding = None
                    if check_type == "equals" and value not in required_values:
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value, None, node
                        )
                    elif check_type == "not_contains" and value in forbidden_values:
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value, None, node
                        )
                    elif check_type in ("in", "contains"):
                        # Normalize to lower for case-insensitive comparison
                        forbidden_values_lower = [str(f).lower() for f in forbidden_values]
                        if isinstance(value, list):
                            value_lower = [str(v).lower() for v in value]
                            for forbidden in forbidden_values_lower:
                                if forbidden in value_lower:
                                    finding = self._make_finding(
                                        filename, node_type, node_name, found_path, value, None, node
                                    )
                                    break
                        else:
                            value_lower = str(value).lower()
                            for forbidden in forbidden_values_lower:
                                if value_lower == forbidden:
                                    finding = self._make_finding(
                                        filename, node_type, node_name, found_path, value, None, node
                                    )
                                    break
                    elif check_type == "min_value":
                        try:
                            if float(value) < float(required_values[0]):
                                finding = self._make_finding(
                                    filename, node_type, node_name, found_path, value, None, node
                                )
                        except Exception:
                            finding = self._make_finding(
                                filename, node_type, node_name, found_path, value, 
                                "Value not numeric", node
                            )
                    elif check_type == "required_present" and (value is None or value == ""):
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value, 
                            "Required property missing", node
                        )
                    elif check_type == "regex" and regex_pattern:
                        # Check value_type filter if specified
                        value_type_filter = logic.get("value_type")
                        if value_type_filter:
                            # Only apply regex if value matches the specified type
                            if value_type_filter == "str" and not isinstance(value, str):
                                continue
                            elif value_type_filter == "int" and not isinstance(value, int):
                                continue
                            elif value_type_filter == "float" and not isinstance(value, float):
                                continue
                        
                        # For cipher and similar rules, only check string values
                        if self.rule_id in ["cipher_algorithms_should_be_robust", "string_literals_should_not_be_duplicated"] and not isinstance(value, str):
                            continue
                            
                        if not re.match(regex_pattern, str(value)):
                            finding = self._make_finding(
                                filename, node_type, node_name, found_path, value, None, node
                            )
                    elif check_type == "pattern":
                        # Simple pattern matching with exclusions
                        pattern = logic.get("pattern")
                        match_type = logic.get("match_type", "violation_if_matches")
                        exclude_patterns = logic.get("exclude_patterns", [])
                        
                        if pattern and isinstance(value, str):
                            # Check exclusions first
                            excluded = False
                            for exclude_pattern in exclude_patterns:
                                if re.match(exclude_pattern, value):
                                    excluded = True
                                    break
                            
                            if not excluded:
                                pattern_matches = re.match(pattern, value)
                                if match_type == "violation_if_matches" and pattern_matches:
                                    finding = self._make_finding(
                                        filename, node_type, node_name, found_path, value, None, node
                                    )
                                elif match_type == "violation_if_not_matches" and not pattern_matches:
                                    finding = self._make_finding(
                                        filename, node_type, node_name, found_path, value, None, node
                                    )
                    elif check_type == "forbidden_empty" and (value is None or value == [] or value == ""):
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value, 
                            "Property is empty or missing", node
                        )

                    # Add finding if it's unique
                    if finding:
                        unique_key = (
                            self.rule_id,
                            filename,
                            finding.get('line', 0),
                            str(finding.get('property_path', []))
                        )
                        if unique_key not in seen_findings:
                            seen_findings.add(unique_key)
                            findings.append(finding)

        return findings

    def _walk_dict(self, d, parent_key=None):
        """Recursively yield (key, value) for all values in a dict - adapted for Python AST"""
        if isinstance(d, dict):
            for k, v in d.items():
                if k in ['lineno', 'col_offset', 'node_type']:  # Skip AST metadata
                    continue
                full_key = k if parent_key is None else f"{parent_key}.{k}"
                if isinstance(v, dict):
                    yield from self._walk_dict(v, full_key)
                elif isinstance(v, list):
                    for idx, item in enumerate(v):
                        if isinstance(item, dict):
                            yield from self._walk_dict(item, f"{full_key}[{idx}]")
                        else:
                            yield f"{full_key}[{idx}]", item
                else:
                    yield full_key, v
        else:
            yield parent_key, d

    def _get_property(self, node_body, prop_path):
        """Get property from Python AST node - adapted from Terraform version"""
        if isinstance(prop_path, str):
            prop_path = [prop_path]
        current = node_body
        found_path = []
        for key in prop_path:
            if isinstance(current, dict) and key in current:
                current = current[key]
                found_path.append(key)
            elif isinstance(current, list):
                # If current is a list, try each item
                found = False
                for idx, item in enumerate(current):
                    if isinstance(item, dict) and key in item:
                        current = item[key]
                        found_path.append(f"{key}[{idx}]")
                        found = True
                        break
                if not found:
                    return None, found_path
            else:
                return None, found_path
        return current, found_path

    def _make_finding(self, filename, node_type, node_name, property_path, value, message=None, node=None):
        """Create a finding with Python-specific information."""
        finding = {
            "rule_id": self.rule_id,
            "message": message or self.message,
            "node": f"{node_type}.{node_name}",  # Changed from "resource"
            "file": filename,
            "property_path": property_path,
            "value": value,
            "status": "violation"
        }
        
        # Add line/column information from Python AST node
        if node:
            finding["line"] = node.get('lineno', 1)
            finding["column"] = node.get('col_offset', 0)
        
        # Add severity if present in metadata
        if "severity" in self.metadata:
            finding["severity"] = self.metadata["severity"]
        elif "defaultSeverity" in self.metadata:
            finding["severity"] = self.metadata["defaultSeverity"]
            
        return finding


# For backward compatibility, alias the main class
GenericRule = PythonGenericRule