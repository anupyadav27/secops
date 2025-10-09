#!/usr/bin/env python3
"""
Python Generic Rule Engine - Enhanced Version

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
        """
        Determines if the rule is applicable to the given AST tree.
        A rule is applicable if:
        1. It has valid metadata
        2. The rule's target features are present in the code
        3. The rule's conditions could potentially be violated
        """
        # Check if we have valid metadata
        if not self.metadata or not self.rule_id:
            return False

        # Get module content from AST
        module_content = ast_tree.get('source_lines', [])
        module_text = '\n'.join(module_content) if module_content else ''

        # Check based on rule category and features
        rule_category = self.metadata.get('category', '')
        rule_id = self.rule_id.lower()

        # Skip rules that are clearly not applicable based on content
        if any(x in rule_id for x in ['django', 'flask']) and 'django' not in module_text.lower() and 'flask' not in module_text.lower():
            return False
        if 'aws' in rule_id and 'boto' not in module_text.lower() and 'aws' not in module_text.lower():
            return False
        if 'async' in rule_id and 'async' not in module_text and 'await' not in module_text:
            return False
        if 'regex' in rule_id and not any(x in module_text for x in ['re.', 'import re', 'from re']):
            return False
        if 'sql' in rule_id and not any(x in module_text.lower() for x in ['sql', 'database', 'query']):
            return False
        if 'numpy' in rule_id and 'numpy' not in module_text and 'np.' not in module_text:
            return False
        if 'pandas' in rule_id and 'pandas' not in module_text and 'pd.' not in module_text:
            return False
        if 'tensorflow' in rule_id and 'tensorflow' not in module_text and 'tf.' not in module_text:
            return False
        if 'torch' in rule_id and 'torch' not in module_text:
            return False

        # If there's a custom function, check if it's potentially applicable
        custom_function = self._get_custom_function(self.rule_id)
        if custom_function:
            # Pre-check AST for relevant features
            feature_exists = self._check_ast_features(ast_tree, rule_id)
            return feature_exists

        # Check if we have valid logic defined in metadata
        if not self.logic:
            print(f"Rule {self.rule_id} has no logic defined")
            return False

        # Check if required node types are present in the AST
        required_node_types = self.logic.get("node_types", [])
        if required_node_types:
            # Search for nodes of the required types
            matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types)
            if not matching_nodes:
                return False
            
            # Additional check: see if the rule's conditions could be violated
            for node in matching_nodes:
                if self._could_violate_rule(node):
                    return True
            return False

        # If no specific requirements and no other checks passed, rule is not applicable
        return False
        
    def check(self, ast_tree, filename):
        """Check the AST tree for rule violations."""
        findings = []
        seen_findings = set()  # For deduplication

        # First try custom implementation
        custom_function = self._get_custom_function(self.rule_id)
        if custom_function:
            # Create a finding for each violation
            violations = custom_function(ast_tree)
            if violations:
                finding = self._make_finding(
                    filename=filename,
                    node_type="custom",
                    node_name=self.rule_id,
                    property_path=[],
                    value=None,
                    message=self.message
                )
                findings.append(finding)
            return findings

        # Fall back to generic implementation
        if not self.logic:
            return findings

        required_node_types = self.logic.get("node_types", [])
        if not required_node_types:
            return findings

        matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types)
        for node in matching_nodes:
            node_type = node.get('node_type')
            node_name = node.get('name', 'unknown')

            for check in self.logic.get("checks", []):
                check_type = check.get("type")
                property_path = check.get("property")
                regex_pattern = check.get("pattern")

                # Get property values using wildcard support
                property_values = []
                if property_path:
                    if isinstance(property_path, str):
                        property_path = property_path.split('.')
                    property_values = self._get_properties_with_wildcard(node, property_path)

                # If no specific property to check, evaluate the node itself
                if not property_values:
                    property_values = [([], node)]

                # Check each property value
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
                    elif check_type == "regex" and regex_pattern:
                        if not isinstance(value, str):
                            continue
                        if not re.match(regex_pattern, str(value)):
                            finding = self._make_finding(
                                filename, node_type, node_name, found_path, value, 
                                "Pattern mismatch", node
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

    def _check_ast_features(self, ast_tree, rule_id):
        """Check if the AST contains features relevant to the rule."""
        if 'class' in rule_id:
            return any(node.get('node_type') == 'ClassDef' for node in self._find_all_nodes(ast_tree))
        if 'function' in rule_id or 'method' in rule_id:
            return any(node.get('node_type') == 'FunctionDef' for node in self._find_all_nodes(ast_tree))
        if 'import' in rule_id:
            return any(node.get('node_type') in ['Import', 'ImportFrom'] for node in self._find_all_nodes(ast_tree))
        if 'exception' in rule_id or 'except' in rule_id:
            return any(node.get('node_type') in ['Try', 'ExceptHandler'] for node in self._find_all_nodes(ast_tree))
        if 'variable' in rule_id or 'assign' in rule_id:
            return any(node.get('node_type') == 'Assign' for node in self._find_all_nodes(ast_tree))
        # Default to True for other cases to avoid false negatives
        return True

    def _could_violate_rule(self, node):
        """Check if the node could potentially violate the rule's conditions."""
        # Get rule checks from logic
        checks = self.logic.get("checks", [])
        for check in checks:
            check_type = check.get("type")
            property_path = check.get("property")
            
            # Get property values
            if property_path:
                if isinstance(property_path, str):
                    property_path = property_path.split('.')
                values = self._get_properties_with_wildcard(node, property_path)
                if values:
                    return True

        return False

    def _find_all_nodes(self, ast_tree):
        """Find all nodes in the AST."""
        nodes = []
        def traverse(node):
            if isinstance(node, dict):
                nodes.append(node)
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        traverse(ast_tree)
        return nodes

    def _get_custom_function(self, function_name):
        """Get a custom function by name from logic_implementations module."""
        if function_name is None:
            return None
        
        import logic_implementations
        # First check the logic_implementations module
        if hasattr(logic_implementations, function_name):
            return getattr(logic_implementations, function_name)
        
        # Fallback to check this class (for backward compatibility)
        if hasattr(self, function_name):
            return getattr(self, function_name)
        
        return None

    def _find_nodes_by_type(self, ast_tree, node_types):
        """
        Find all nodes of specified types in the Python AST.
        """
        found_nodes = []
        def traverse(node):
            if isinstance(node, dict):
                if node.get('node_type') in node_types:
                    found_nodes.append(node)
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        traverse(ast_tree)
        return found_nodes

    def _get_properties_with_wildcard(self, obj, prop_path):
        """
        Get property values from object, supporting wildcards in the path.
        """
        if not prop_path:
            return [([], obj)]
            
        results = []
        key = prop_path[0]
        rest = prop_path[1:]
        
        if key == "*":
            if isinstance(obj, list):
                for idx, item in enumerate(obj):
                    sub_results = self._get_properties_with_wildcard(item, rest)
                    for path, value in sub_results:
                        results.append(([f"[{idx}]"] + path, value))
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if k not in ['lineno', 'col_offset', 'node_type']:
                        sub_results = self._get_properties_with_wildcard(v, rest)
                        for path, value in sub_results:
                            results.append(([k] + path, value))
        elif isinstance(obj, dict) and key in obj:
            sub_results = self._get_properties_with_wildcard(obj[key], rest)
            for path, value in sub_results:
                results.append(([key] + path, value))
                
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