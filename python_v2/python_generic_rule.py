#!/usr/bin/env python3
"""
Python Generic Rule Engine - Enhanced Version

A generic rule engine that can apply any rule based on JSON metadata to Python AST.
Handles AST traversal, rule applicability checking, and pattern matching.
"""

import re
import ast
import json
import logic_implementations
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


class PythonGenericRule:
    """
    Generic rule engine for Python AST processing.
    """

    def __init__(self, metadata):
        self.metadata = metadata
        self.logic = metadata.get("logic", {})
        self.rule_id = metadata.get("rule_id", "unknown_rule")
        self.message = metadata.get("title", "Rule violation")

    def is_applicable(self, ast_tree):
        # Check if we have valid metadata
        if not self.metadata or not self.rule_id:
            return False

        # Get custom function if it exists
        function_name = None
        if isinstance(self.logic.get('checks'), list):
            for check in self.logic.get('checks', []):
                if check.get('type') == 'custom_function':
                    function_name = check.get('function')
                    break
        
        custom_function = self._get_custom_function(function_name)
        
        # Check if required node types are present
        required_node_types = self.logic.get("node_types", [])
        matching_nodes = []
        if required_node_types:
            matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types)

        # Rule is applicable if either:
        # 1. We have matching node types OR
        # 2. We have a valid custom function
        return len(matching_nodes) > 0 or custom_function is not None
        
    def check(self, ast_tree, filename):
        """
        Enhanced check method that applies generic logic first, then custom functions as fallback.
        
        Process:
        1. Apply generic logic (regex, property_comparison, exists/not_exists)
        2. If no findings from generic logic AND custom_function exists, call custom function
        3. Return all findings from both approaches
        """
        findings = []
        seen_findings = set()  # For deduplication
        
        # Step 1: Apply generic logic first
        generic_findings = self._apply_generic_logic(ast_tree, filename, seen_findings)
        findings.extend(generic_findings)
        
        # Step 2: If no findings from generic logic AND custom function exists, use custom function
        custom_function_name = self._get_custom_function_name()
        if len(findings) == 0 and custom_function_name:
            custom_findings = self._apply_custom_function(ast_tree, filename, custom_function_name, seen_findings)
            findings.extend(custom_findings)
        
        print(f"[DEBUG] Found {len(findings)} violations in {filename} (Generic: {len(generic_findings)}, Custom: {len(findings) - len(generic_findings)})")
        return findings

    def _get_custom_function_name(self):
        """Extract custom function name from logic checks or root logic dict."""
        # Check inside checks array
        if isinstance(self.logic.get('checks'), list):
            for check in self.logic.get('checks', []):
                if check.get('type') == 'custom_function' and check.get('function'):
                    return check.get('function')
        # Check at root level
        if self.logic.get('custom_function'):
            return self.logic.get('custom_function')
        return None

    def _apply_generic_logic(self, ast_tree, filename, seen_findings):
        """Apply generic logic checks (regex, property_comparison, exists, not_exists, etc.)."""
        findings = []
        
        # Handle old-style logic format (single check at root level)
        if not isinstance(self.logic.get('checks'), list):
            findings.extend(self._apply_single_check(ast_tree, filename, self.logic, seen_findings))
        else:
            # Handle new-style logic format (multiple checks in array)
            for check in self.logic.get("checks", []):
                if check.get("type") != "custom_function":  # Skip custom functions in generic logic
                    findings.extend(self._apply_single_check(ast_tree, filename, check, seen_findings))
        
        return findings

    def _apply_single_check(self, ast_tree, filename, check, seen_findings):
        """Apply a single generic check (regex, property_comparison, etc.)."""
        findings = []
        check_type = check.get("type") or check.get("check_type")

        # Get required node types
        required_node_types = self.logic.get("node_types", [])
        if not required_node_types:
            required_node_types = check.get("node_types", [])

        # Find matching nodes
        matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types) if required_node_types else [ast_tree]
        source_lines = ast_tree.get('source_lines') if isinstance(ast_tree, dict) else None

        # Only apply property checks to nodes of the correct type
        for node in matching_nodes:
            if isinstance(node, dict):
                node_type = node.get('node_type', 'unknown')
                node_name = node.get('name', 'unknown')
            else:
                node_type = 'root'
                node_name = 'root'

            # Debug: print before property extraction
            if check_type in ["property_comparison", "exists", "not_exists", "numeric_bounds", "required_present", "ast_property"]:
                print(f"[GENERIC LOGIC] Applying {check_type} to node_type={node_type}, node_name={node_name}, property={check.get('property') or check.get('property_path')}")

            # Apply different check types
            if check_type in ["regex", "pattern"]:
                findings.extend(self._apply_regex_check(check, node, filename, node_type, node_name, source_lines, seen_findings))
            elif check_type == "property_comparison":
                findings.extend(self._apply_property_comparison_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "exists":
                findings.extend(self._apply_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "not_exists":
                findings.extend(self._apply_not_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type in ["numeric_bounds", "required_present", "ast_property"]:
                findings.extend(self._apply_other_checks(check, node, filename, node_type, node_name, seen_findings))

        return findings

    def _apply_regex_check(self, check, node, filename, node_type, node_name, source_lines, seen_findings):
        """Apply regex pattern checks."""
        findings = []
        regex_pattern = check.get("pattern")
        property_path = check.get("property") or check.get("property_path")
        
        if not regex_pattern:
            return findings

        # If we have source lines and node line info, check against source code
        if source_lines and isinstance(node, dict):
            lineno = node.get('lineno')
            end_lineno = node.get('end_lineno', lineno)
            if lineno and end_lineno and lineno <= end_lineno:
                code_block = '\n'.join(source_lines[lineno-1:end_lineno])
                print(f"[DEBUG] Checking regex pattern '{regex_pattern}' against code block: {code_block}")
                if re.search(regex_pattern, code_block):
                    finding = self._make_finding(
                        filename, node_type, node_name, [], code_block,
                        check.get('message', 'Pattern match'), node
                    )
                    unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                    if unique_key not in seen_findings:
                        print(f"[DEBUG] Found regex match at line {finding.get('line', 0)}")
                        seen_findings.add(unique_key)
                        findings.append(finding)

        # Also check against property values if property path is specified
        if property_path:
            property_values = self._get_property_values(node, property_path)
            for found_path, value in property_values:
                if isinstance(value, str) and re.search(regex_pattern, value):
                    finding = self._make_finding(
                        filename, node_type, node_name, found_path, value,
                        check.get('message', 'Pattern match'), node
                    )
                    unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                    if unique_key not in seen_findings:
                        seen_findings.add(unique_key)
                        findings.append(finding)

        return findings

    def _apply_property_comparison_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply property comparison checks, only to nodes of the correct type and structure."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        starts_with = check.get("starts_with")
        match_keyword = check.get("match_keyword")

        expected_types = self.logic.get("node_types", [])
        if expected_types and node_type not in expected_types:
            return findings

        # Special handling for Call.keywords Namespace
        if node_type == "Call" and property_path == ["keywords", "arg", "value"] and starts_with and match_keyword:
            for kw in node.get("keywords", []):
                if kw.get("arg") == match_keyword:
                    val = kw.get("value")
                    # Handle string value node
                    if isinstance(val, dict) and val.get("node_type") in ["Str", "Constant"]:
                        strval = val.get("s") if "s" in val else val.get("value")
                        if isinstance(strval, str) and strval.startswith(starts_with):
                            finding = self._make_finding(
                                filename, node_type, node_name, property_path, strval,
                                check.get('message', self.message), node
                            )
                            unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                            if unique_key not in seen_findings:
                                seen_findings.add(unique_key)
                                findings.append(finding)
        return findings

    def _apply_exists_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply exists checks (property must exist)."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        
        if not property_path:
            return findings

        property_values = self._get_property_values(node, property_path)
        
        # If no property values found, it means the property doesn't exist
        if not property_values:
            finding = self._make_finding(
                filename, node_type, node_name, property_path if isinstance(property_path, list) else [property_path], 
                None, check.get('message', 'Required property missing'), node
            )
            unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
            if unique_key not in seen_findings:
                seen_findings.add(unique_key)
                findings.append(finding)

        return findings

    def _apply_not_exists_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply not_exists checks (property must not exist)."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        
        if not property_path:
            return findings

        property_values = self._get_property_values(node, property_path)
        
        # If property values found, it means the property exists (violation)
        for found_path, value in property_values:
            finding = self._make_finding(
                filename, node_type, node_name, found_path, value,
                check.get('message', 'Property should not exist'), node
            )
            unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
            if unique_key not in seen_findings:
                seen_findings.add(unique_key)
                findings.append(finding)

        return findings

    def _apply_other_checks(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply other check types (numeric_bounds, required_present, ast_property)."""
        findings = []
        check_type = check.get("type") or check.get("check_type")
        property_path = check.get("property") or check.get("property_path")
        
        property_values = self._get_property_values(node, property_path)
        
        for found_path, value in property_values:
            finding = None
            
            if check_type == "numeric_bounds":
                if not isinstance(value, (int, float)):
                    finding = self._make_finding(
                        filename, node_type, node_name, found_path, value, 
                        "Value not numeric", node
                    )
            elif check_type == "required_present" and (value is None or value == ""):
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value, 
                    "Required property missing", node
                )
            elif check_type == "ast_property":
                # Handle AST property checks safely and directly (avoid deep traversal)
                prop_name = check.get("property_name")
                expected_value = check.get("expected_value")

                if isinstance(node, dict) and node.get('node_type') == 'Call' and prop_name:
                    # Safe direct iteration over keywords
                    keywords = node.get('keywords', []) or []
                    for kw in keywords:
                        # kw is expected to be dict like {'arg': 'timeout', 'value': {...}}
                        if not isinstance(kw, dict):
                            continue
                        if kw.get('arg') == prop_name:
                            value_node = kw.get('value', {})
                            # only treat simple constant matches as a finding
                            if isinstance(value_node, dict) and value_node.get('node_type') == 'Constant':
                                if str(value_node.get('value')) == str(expected_value):
                                    finding = self._make_finding(
                                        filename, node_type, node_name, found_path,
                                        f"{prop_name}={expected_value}",
                                        check.get('message', 'Property match'), node
                                    )
                                    break
                            # If the value_node is a simple primitive already (unlikely), compare directly
                            elif not isinstance(value_node, dict) and str(value_node) == str(expected_value):
                                finding = self._make_finding(
                                    filename, node_type, node_name, found_path,
                                    f"{prop_name}={expected_value}",
                                    check.get('message', 'Property match'), node
                                )
                                break

            if finding:
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)

        return findings

    def _get_property_values(self, node, property_path, visited=None, depth=0, max_depth=60):
        if depth <= 2:
            node_type = node.get('node_type') if isinstance(node, dict) else type(node)
            print(f"[DEBUG] _get_property_values called: property_path={property_path}, node_type={node_type}, depth={depth}")
        """
        Get property values from node, handling both new and old path formats.
        This is recursion-safe (uses visited set and depth guard), and short-circuits
        for common patterns like Call -> keywords where deep traversal is unnecessary.
        Returns list of tuples: (property_path_tuple_or_list, value)
        """
        if visited is None:
            visited = set()

        # Depth & recursion guard
        if depth > max_depth:
            print(f"[SAFE EXIT] Max depth reached while extracting property {property_path}")
            return []

        # Normalize property_path
        if not property_path:
            return [([], node)]
        if isinstance(property_path, str):
            property_path = property_path.split('.')

        # Ensure node is dict-like
        if not isinstance(node, dict):
            return []

        # Cycle detection
        try:
            obj_id = id(node)
        except Exception:
            obj_id = None
        if obj_id is not None:
            if obj_id in visited:
                # already visited this object -> avoid cycle
                return []
            visited.add(obj_id)

        # Quick short-circuit: handle Call->keywords without deep wildcard traversal
        # Many rules that inspect Call keywords only need to iterate node['keywords'] directly.
        if node.get('node_type') == 'Call':
            # If property_path points to keywords or matches pattern like ['keywords','*','value']
            if property_path and (property_path[0] == 'keywords' or property_path[0] == 'keywords[*]' or property_path[0] == 'keywords' and len(property_path) == 1):
                results = []
                keywords = node.get('keywords', [])
                if isinstance(keywords, list):
                    for idx, kw in enumerate(keywords):
                        # kw is typically a dict with 'arg' and 'value'
                        # expose both arg and value for rule checks
                        results.append(([f"keywords[{idx}]", "arg"], kw.get('arg')))
                        results.append(([f"keywords[{idx}]", "value"], kw.get('value')))
                return results

        # Default behavior: walk prop_path step by step, but keep visited+depth to avoid explosion
        first_key = property_path[0]
        rest = property_path[1:]

        # If first_key not present, nothing to return
        if first_key not in node:
            return []

        value = node[first_key]

        # If we've exhausted path, return the found value
        if not rest:
            return [([first_key], value)]

        results = []
        # If next value is a list, try each item
        if isinstance(value, list):
            for idx, item in enumerate(value):
                sub_results = []
                if isinstance(item, dict):
                    sub_results = self._get_property_values(item, rest, visited, depth + 1, max_depth)
                else:
                    # primitive inside list
                    if not rest:
                        sub_results = [([f"[{idx}]"], item)]
                for path, val in sub_results:
                    results.append(([first_key, f"[{idx}]"] + list(path), val))
        elif isinstance(value, dict):
            sub_results = self._get_property_values(value, rest, visited, depth + 1, max_depth)
            for path, val in sub_results:
                results.append(([first_key] + list(path), val))
        else:
            # primitive and more path remaining -> no match
            return []

        return results

    def _apply_custom_function(self, ast_tree, filename, function_name, seen_findings):
        """
        Apply a custom function from logic_implementations.py to all AST nodes.
        """
        findings = []
        # Import logic_implementations and get the function
        import logic_implementations
        custom_fn = getattr(logic_implementations, function_name, None)
        if not custom_fn:
            print(f"[DEBUG] Custom function {function_name} not found or not callable")
            return findings
        # Traverse AST and apply custom function to each node
        def visit_node(node):
            if custom_fn(node):
                finding = {
                    "rule_id": self.rule_id,
                    "message": self.message,
                    "file": filename,
                    "line": node.get('lineno', 0),
                    "status": "violation"
                }
                findings.append(finding)
        def traverse(node):
            if isinstance(node, dict):
                visit_node(node)
                for v in node.values():
                    traverse(v)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        traverse(ast_tree.get('module', ast_tree))
        return findings

    def _get_custom_function(self, function_name):
        """Get a custom function by name from logic_implementations module."""
        if function_name is None:
            return None
        
        # Clean up the function name - remove _metadata suffix if present
        if function_name.endswith('_metadata'):
            function_name = function_name[:-9]
        
        import logic_implementations
        # First check the logic_implementations module
        if hasattr(logic_implementations, function_name):
            # print(f"[DEBUG] Found custom function {function_name} in logic_implementations")
            return getattr(logic_implementations, function_name)
        
        # Fallback to check this class (for backward compatibility)
        if hasattr(self, function_name):
            # print(f"[DEBUG] Found custom function {function_name} in class")
            return getattr(self, function_name)
        
    # print(f"[DEBUG] No custom function found for {function_name}")
        return None

    def _find_nodes_by_type(self, ast_tree, node_types):
        """
        Find all nodes of specified types in the Python AST.
        """
        found_nodes = []
        def traverse(node, path=None):
            if path is None:
                path = []
            if isinstance(node, dict):
                if node.get('node_type') in node_types:
                    # print(f"[DEBUG] Found node_type {node.get('node_type')} at path: {path}")
                    found_nodes.append(node)
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        traverse(value, path + [key])
            elif isinstance(node, list):
                for idx, item in enumerate(node):
                    traverse(item, path + [f"[{idx}]"])
        traverse(ast_tree)
        return found_nodes

    def _get_properties_with_wildcard(self, obj, prop_path, depth=0, max_depth=100):
        # Recursion-safe: track visited objects
        visited = getattr(self, '_visited_wildcard', None)
        if visited is None:
            visited = set()
            self._visited_wildcard = visited

        obj_id = id(obj)
        if obj_id in visited:
            print(f"[SAFE EXIT] Already visited object at depth {depth}, avoiding recursion.")
            return []
        visited.add(obj_id)

        if depth > max_depth:
            print(f"[RECURSION WARNING] Max recursion depth ({max_depth}) reached at path: {prop_path}")
            return []

        if not isinstance(obj, (dict, list)):
            if not prop_path:
                return [([], obj)]
            return []

        if not prop_path:
            return [([], obj)]

        results = []
        key = prop_path[0]
        rest = prop_path[1:]
        # Expanded skip_keys to include more cycle-prone fields
        skip_keys = ['lineno', 'col_offset', 'node_type', '__parent__', 'ctx', 'body', 'args', 'keywords']

        if isinstance(obj, dict):
            if key == "*":
                for k, v in obj.items():
                    if k in skip_keys:
                        continue
                    sub_results = self._get_properties_with_wildcard(v, rest, depth + 1, max_depth)
                    for path, value in sub_results:
                        results.append(([k] + path, value))
            elif key in obj and key not in skip_keys:
                sub_results = self._get_properties_with_wildcard(obj[key], rest, depth + 1, max_depth)
                for path, value in sub_results:
                    results.append(([key] + path, value))

        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                sub_results = self._get_properties_with_wildcard(item, rest, depth + 1, max_depth)
                for path, value in sub_results:
                    results.append(([f"[{idx}]"] + path, value))

        return results

    def _make_finding(self, filename, node_type, node_name, property_path, value, message=None, node=None):
        """Create a finding with Python-specific information."""
        finding = {
            "rule_id": self.rule_id,
            "message": message or self.message,
            "node": f"{node_type}.{node_name}",
            "file": filename,
            "property_path": property_path,
            "value": value,
            "status": "violation"
        }
        
        if node:
            finding["line"] = node.get('lineno', 1)
            finding["column"] = node.get('col_offset', 0)
        
        if "severity" in self.metadata:
            finding["severity"] = self.metadata["severity"]
        elif "defaultSeverity" in self.metadata:
            finding["severity"] = self.metadata["defaultSeverity"]
            
        return finding

# For backward compatibility
GenericRule = PythonGenericRule