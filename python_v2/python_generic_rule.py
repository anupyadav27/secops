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

def ast_to_dict_with_parent(node, parent=None):
    import ast
    if isinstance(node, ast.AST):
        result = {'node_type': type(node).__name__}
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_dict_with_parent(value, result)
        result['__parent__'] = parent
        for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
            if hasattr(node, attr):
                result[attr] = getattr(node, attr)
        return result
    elif isinstance(node, list):
        return [ast_to_dict_with_parent(item, parent) for item in node]
    else:
        return node
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
        try:
            # print(f"[DEBUG] Starting check for rule: {self.rule_id}")
            findings = []
            seen_findings = set()
            # ALWAYS apply generic logic
            generic_findings = self._apply_generic_logic(ast_tree, filename, seen_findings)
            # print(f"[DEBUG] Generic logic found {len(generic_findings)} findings")
            findings.extend(generic_findings)
            # THEN apply custom function if it exists
            custom_function_name = self._get_custom_function_name()
            if custom_function_name:
                # print(f"[DEBUG] Attempting to apply custom function: {custom_function_name}")
                custom_function = self._get_custom_function(custom_function_name)
                if custom_function:
                    custom_findings = self._apply_custom_function(ast_tree, filename, custom_function_name, seen_findings)
                    # print(f"[DEBUG] Custom function found {len(custom_findings)} findings")
                    findings.extend(custom_findings)
                else:
                    # print(f"[DEBUG] Custom function {custom_function_name} could not be loaded")
                    pass
            # print(f"[DEBUG] Rule {self.rule_id} returning {len(findings)} total findings")
            pass
            return findings
        except RecursionError as e:
            # print(f"[RECURSION ERROR] Rule {self.rule_id}: {e}")
            return []
        except Exception as e:
            # print(f"[ERROR] Rule {self.rule_id} failed: {e}")
            import traceback
            traceback.print_exc()
            return []

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
        # Old-style: single check at root level
        if not isinstance(self.logic.get('checks'), list):
            if self._is_valid_generic_check(self.logic):
                findings.extend(self._apply_single_check(ast_tree, filename, self.logic, seen_findings, is_root_check=True))
        else:
            # New-style: multiple checks in array
            for check in self.logic.get("checks", []):
                if self._is_valid_generic_check(check):
                    findings.extend(self._apply_single_check(ast_tree, filename, check, seen_findings, is_root_check=False))
        return findings

    def _apply_single_check(self, ast_tree, filename, check, seen_findings, is_root_check=False):
        """Apply a single generic check with proper node type resolution and error handling."""
        findings = []
        check_type = check.get("type") or check.get("check_type")
        node_types = check.get("node_types", self.logic.get("node_types", []))
        print(f"[DEBUG][_apply_single_check] Attempting check_type: {check_type} for node_types: {node_types}")

        # Resolve node_types: check-specific, fallback to root
        if is_root_check:
            required_node_types = self.logic.get("node_types", [])
        else:
            required_node_types = check.get("node_types", self.logic.get("node_types", []))

        matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types) if required_node_types else [ast_tree]
        source_lines = ast_tree.get('source_lines') if isinstance(ast_tree, dict) else None

        for node in matching_nodes:
            node_type = node.get('node_type', 'unknown') if isinstance(node, dict) else 'root'
            node_name = node.get('name', 'unknown') if isinstance(node, dict) else 'root'

            if check_type in ["regex", "pattern"]:
                findings.extend(self._apply_regex_check(check, node, filename, node_type, node_name, source_lines, seen_findings))
            elif check_type == "property_comparison":
                findings.extend(self._apply_property_comparison_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "exists":
                findings.extend(self._apply_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "not_exists":
                findings.extend(self._apply_not_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "numeric_bounds":
                findings.extend(self._apply_numeric_bounds_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "required_present":
                findings.extend(self._apply_required_present_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "ast_property":
                findings.extend(self._apply_ast_property_check(check, node, filename, node_type, node_name, seen_findings))
            else:
                # print(f"[ERROR] Unhandled check type in _apply_single_check: {check_type}")
                pass
        return findings
    def _is_valid_generic_check(self, check):
        """Validate if a check is a generic (non-custom) check that should be processed."""
        check_type = check.get("type") or check.get("check_type")
        # Skip custom functions and invalid check types
        if check_type == "custom_function":
            return False
        # Supported check types
        supported_types = ["regex", "pattern", "property_comparison", "exists", "not_exists", "numeric_bounds", "required_present", "ast_property"]
        if check_type and check_type not in supported_types:
            # print(f"[WARNING] Unsupported check type: {check_type}")
            return False
        return True

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
                # print(f"[DEBUG] Checking regex pattern '{regex_pattern}' against code block: {code_block}")
                if re.search(regex_pattern, code_block):
                    finding = self._make_finding(
                        filename, node_type, node_name, [], code_block,
                        check.get('message', 'Pattern match'), node
                    )
                    unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                    if unique_key not in seen_findings:
                        # print(f"[DEBUG] Found regex match at line {finding.get('line', 0)}")
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
        equals = check.get("equals")
        condition = check.get("condition")
        #print(f"[DEBUG] Property comparison check details:")
        #print(f"[DEBUG] - Property path: {property_path}")
        #print(f"[DEBUG] - Starts with: {starts_with}")
        #print(f"[DEBUG] - Node type: {node_type}")
        #print(f"[DEBUG] - Node structure: {node if isinstance(node, dict) else type(node)}")

        if not property_path:
            return findings

        # First check if condition is met (if any)
        if condition:
            cond_path = condition.get("property") or condition.get("path")
            cond_equals = condition.get("equals")
            # print(f"[DEBUG] Checking condition:")
            # print(f"[DEBUG] - Condition path: {cond_path}")
            # print(f"[DEBUG] - Condition equals: {cond_equals}")
            if cond_path and cond_equals:
                cond_values = self._get_property_values(node, cond_path)
                # print(f"[DEBUG] - Condition values found: {cond_values}")
                condition_met = False
                for found_path, value in cond_values:
                    # print(f"[DEBUG] - Checking condition value: {value}")
                    if value == cond_equals:
                        condition_met = True
                        # print(f"[DEBUG] - Condition met!")
                        break
                if not condition_met:
                    # print(f"[DEBUG] - Condition not met, skipping")
                    return findings

        # First check condition if present
        condition_met = True
        if condition:
            cond_property = condition.get('property')
            cond_equals = condition.get('equals')
            # print(f"[DEBUG] Checking condition: property={cond_property} equals={cond_equals}")
            
            cond_values = self._get_property_values(node, cond_property)
            condition_met = False
            for _, cond_value in cond_values:
                # print(f"[DEBUG] Checking condition value: {cond_value}")
                if cond_value == cond_equals:
                    condition_met = True
                    break
            
            if not condition_met:
                # print("[DEBUG] Condition not met, skipping value checks")
                return findings

        # Get property values to check
        # Enhanced: extract regex string from multiple possible keys in args[0]
        property_values = []
        if property_path == ["args", 0, "s"]:
            args = node.get("args", [])
            if args and isinstance(args[0], dict):
                regex_str = None
                for key in ["s", "value", "constant", "str", "text"]:
                    if isinstance(args[0].get(key), str):
                        regex_str = args[0][key]
                        break
                if regex_str is not None:
                    property_values.append((property_path, regex_str))
        else:
            property_values = self._get_property_values(node, property_path)
        # Custom logic for single-character character class in regex
        import re
        if self.rule_id == "character_classes_in_regular_expressions_should_not_contain_only_one_character":
            for found_path, value in property_values:
                if isinstance(value, str):
                    for match in re.finditer(r"\[(.*?)\]", value):
                        char_class = match.group(1)
                        if len(char_class) == 1:
                            finding = self._make_finding(
                                filename, node_type, node_name, found_path, value,
                                check.get('message', self.message), node
                            )
                            unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                            if unique_key not in seen_findings:
                                seen_findings.add(unique_key)
                                findings.append(finding)
        elif check.get("contains_duplicate_character_class"):
            for found_path, value in property_values:
                if isinstance(value, str):
                    for match in re.finditer(r"\[(.*?)\]", value):
                        char_class = match.group(1)
                        seen = set()
                        for c in char_class:
                            c_lower = c.lower()
                            if c_lower in seen:
                                finding = self._make_finding(
                                    filename, node_type, node_name, found_path, value,
                                    check.get('message', self.message), node
                                )
                                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                                if unique_key not in seen_findings:
                                    seen_findings.add(unique_key)
                                    findings.append(finding)
                                break
                            seen.add(c_lower)
        else:
            forbidden_values = check.get("forbidden_values", [])
            for found_path, value in property_values:
                if node_type == "ExceptHandler" and found_path == ["type", "node_type"]:
                    print(f"[DEBUG] Checking ExceptHandler at line {node.get('lineno')}, type.node_type: {value}")
                # Match forbidden values as both string and integer representations
                if forbidden_values and (value in forbidden_values or str(value) in forbidden_values):
                    finding = self._make_finding(
                        filename, node_type, node_name, found_path, value,
                        check.get('message', self.message), node
                    )
                    unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                    if unique_key not in seen_findings:
                        seen_findings.add(unique_key)
                        findings.append(finding)
                if starts_with and isinstance(value, str):
                    if value.startswith(starts_with):
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value,
                            check.get('message', self.message), node
                        )
                        unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                        if unique_key not in seen_findings:
                            seen_findings.add(unique_key)
                            findings.append(finding)
                # NEW: regex property_comparison support
                regex_pattern = check.get("regex")
                if regex_pattern and isinstance(value, str):
                    import re
                    if re.search(regex_pattern, value):
                        finding = self._make_finding(
                            filename, node_type, node_name, found_path, value,
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

    def _apply_numeric_bounds_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply numeric_bounds check."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            if not isinstance(value, (int, float)):
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value,
                    "Value not numeric", node
                )
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)
        return findings

    def _apply_required_present_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply required_present check."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            if value is None or value == "":
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value,
                    "Required property missing", node
                )
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)
        return findings

    def _apply_ast_property_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply ast_property check."""
        findings = []
        prop_name = check.get("property_name")
        expected_value = check.get("expected_value")
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            finding = None
            if isinstance(node, dict) and node.get('node_type') == 'Call' and prop_name:
                keywords = node.get('keywords', []) or []
                for kw in keywords:
                    if not isinstance(kw, dict):
                        continue
                    if kw.get('arg') == prop_name:
                        value_node = kw.get('value', {})
                        if isinstance(value_node, dict) and value_node.get('node_type') == 'Constant':
                            if str(value_node.get('value')) == str(expected_value):
                                finding = self._make_finding(
                                    filename, node_type, node_name, found_path,
                                    f"{prop_name}={expected_value}",
                                    check.get('message', 'Property match'), node
                                )
                                break
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

    def _get_property_values(self, node, property_path, visited=None, depth=0, max_depth=20):
        if not isinstance(node, dict) or not property_path:
            # print("[DEBUG] Early return: node is not dict or no property path")

            return []

        # Convert path to list if it's a string with dot notation
        if isinstance(property_path, str):
            # Split by dots but preserve array notation
            parts = []
            current = ""
            in_brackets = False
            for char in property_path:
                if char == '[':
                    in_brackets = True
                    if current:
                        parts.append(current)
                        current = ""
                    current = char
                elif char == ']':
                    in_brackets = False
                    current += char
                    parts.append(current)
                    current = ""
                elif char == '.' and not in_brackets:
                    if current:
                        parts.append(current)
                        current = ""
                else:
                    current += char
            if current:
                parts.append(current)
            property_path = parts

        # Use iterative approach with stack instead of recursion
        stack = [(node, property_path, [])]  # (current_node, remaining_path, full_path)
        results = []
        visited_nodes = set()  # Track visited nodes by id to prevent cycles

        while stack:
            current_node, current_path, full_path = stack.pop()
            # Safety check - skip if not a dict
            if not isinstance(current_node, dict):
                continue
            # Cycle detection
            node_id = id(current_node)
            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)
            if not current_path:
                continue
            current_key = current_path[0]
            remaining_path = current_path[1:] if len(current_path) > 1 else []
            # Handle wildcard (*) and array index notation - match all keys or specific index
            if current_key == '*':
                # For wildcard, iterate all items in dict
                items = current_node.items() if isinstance(current_node, dict) else enumerate(current_node)
                for key, value in items:
                    if isinstance(current_node, dict) and key in ['lineno', 'col_offset', 'end_lineno', 'node_type', '__parent__', 'ctx', 'parent']:
                        continue
                    key_str = str(key) if isinstance(current_node, dict) else f"[{key}]"
                    new_full_path = full_path + [key_str]
                    if not remaining_path:
                        results.append((new_full_path, value))
                    else:
                        if isinstance(value, dict):
                            stack.append((value, remaining_path, new_full_path))
                        elif isinstance(value, list):
                            stack.append((value, remaining_path, new_full_path))
            elif current_key == '[*]':
                # Wildcard for lists: iterate all items
                if isinstance(current_node, list):
                    for idx, item in enumerate(current_node):
                        new_full_path = full_path + [f"[{idx}]"]
                        if not remaining_path:
                            results.append((new_full_path, item))
                        else:
                            stack.append((item, remaining_path, new_full_path))
            elif isinstance(current_key, str) and current_key.startswith('[') and current_key.endswith(']'):
                # For array index, get specific item
                try:
                    idx = int(current_key[1:-1])
                except ValueError:
                    idx = None
                if idx is not None and isinstance(current_node, list) and 0 <= idx < len(current_node):
                    item = current_node[idx]
                    new_full_path = full_path + [current_key]
                    if not remaining_path:
                        results.append((new_full_path, item))
                    else:
                        stack.append((item, remaining_path, new_full_path))
            # Handle specific key
            elif current_key in current_node:
                value = current_node[current_key]
                new_full_path = full_path + [current_key]
                if not remaining_path:
                    # End of path - add to results
                    results.append((new_full_path, value))
                else:
                    # Continue traversal
                    if isinstance(value, dict):
                        stack.append((value, remaining_path, new_full_path))
                    elif isinstance(value, list):
                        for idx, item in enumerate(value):
                            if isinstance(item, dict):
                                stack.append((item, remaining_path, new_full_path + [f"[{idx}]"]))
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
            # print(f"[DEBUG] Custom function {function_name} not found or not callable")
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
        if not function_name:
            return None
        try:
            import logic_implementations
            if hasattr(logic_implementations, function_name):
                func = getattr(logic_implementations, function_name)
                if callable(func):
                    # print(f"[DEBUG] Successfully loaded custom function: {function_name}")
                    return func
                else:
                    # print(f"[DEBUG] {function_name} exists but is not callable")
                    return None
            else:
                # print(f"[DEBUG] Custom function {function_name} not found in logic_implementations")
                return None
        except ImportError as e:
            # print(f"[ERROR] Cannot import logic_implementations: {e}")
            pass
        except Exception as e:
            # print(f"[ERROR] Error loading custom function {function_name}: {e}")
            return None
        

    def _find_nodes_by_type(self, ast_tree, node_types):
        """
        Find all nodes of specified types in the Python AST using a stack-based approach.
        """
        found_nodes = []
        stack = [(ast_tree, [])]  # Stack of (node, path) tuples
        seen = set()  # Track visited object IDs to prevent cycles
        
        while stack:
            node, path = stack.pop()
            node_id = id(node)
            
            if node_id in seen:
                continue
            seen.add(node_id)
            
            if isinstance(node, dict):
                if node.get('node_type') in node_types:
                    found_nodes.append(node)
                    
                # Add children to stack
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        stack.append((value, path + [key]))
                        
            elif isinstance(node, list):
                # Add list items to stack
                for idx, item in enumerate(node):
                    stack.append((item, path + [f"[{idx}]"]))
        return found_nodes

    def _get_properties_with_wildcard(self, obj, prop_path, depth=0, max_depth=100):
        # Recursion-safe: track visited objects
        visited = getattr(self, '_visited_wildcard', None)
        if visited is None:
            visited = set()
            self._visited_wildcard = visited

        obj_id = id(obj)
        if obj_id in visited:
            # print(f"[SAFE EXIT] Already visited object at depth {depth}, avoiding recursion.")
            return []
        visited.add(obj_id)

        if depth > max_depth:
            # print(f"[RECURSION WARNING] Max recursion depth ({max_depth}) reached at path: {prop_path}")
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
'''
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
def ast_to_dict_with_parent(node, parent=None):
    import ast
    if isinstance(node, ast.AST):
        result = {'node_type': type(node).__name__}
        for field in node._fields:
            value = getattr(node, field)
            result[field] = ast_to_dict_with_parent(value, result)
        result['__parent__'] = parent
        for attr in ['lineno', 'col_offset', 'end_lineno', 'end_col_offset']:
            if hasattr(node, attr):
                result[attr] = getattr(node, attr)
        return result
    elif isinstance(node, list):
        return [ast_to_dict_with_parent(item, parent) for item in node]
    else:
        return node
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
        try:
            # print(f"[DEBUG] Starting check for rule: {self.rule_id}")
            findings = []
            seen_findings = set()
            # ALWAYS apply generic logic
            generic_findings = self._apply_generic_logic(ast_tree, filename, seen_findings)
            # print(f"[DEBUG] Generic logic found {len(generic_findings)} findings")
            findings.extend(generic_findings)
            # THEN apply custom function if it exists
            custom_function_name = self._get_custom_function_name()
            if custom_function_name:
                # print(f"[DEBUG] Attempting to apply custom function: {custom_function_name}")
                custom_function = self._get_custom_function(custom_function_name)
                if custom_function:
                    custom_findings = self._apply_custom_function(ast_tree, filename, custom_function_name, seen_findings)
                    # print(f"[DEBUG] Custom function found {len(custom_findings)} findings")
                    findings.extend(custom_findings)
                else:
                    # print(f"[DEBUG] Custom function {custom_function_name} could not be loaded")
                    pass
            # print(f"[DEBUG] Rule {self.rule_id} returning {len(findings)} total findings")
            pass
            return findings
        except RecursionError as e:
            # print(f"[RECURSION ERROR] Rule {self.rule_id}: {e}")
            return []
        except Exception as e:
            # print(f"[ERROR] Rule {self.rule_id} failed: {e}")
            import traceback
            traceback.print_exc()
            return []

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
        # Old-style: single check at root level
        if not isinstance(self.logic.get('checks'), list):
            if self._is_valid_generic_check(self.logic):
                findings.extend(self._apply_single_check(ast_tree, filename, self.logic, seen_findings, is_root_check=True))
        else:
            # New-style: multiple checks in array
            for check in self.logic.get("checks", []):
                if self._is_valid_generic_check(check):
                    findings.extend(self._apply_single_check(ast_tree, filename, check, seen_findings, is_root_check=False))
        return findings

    def _apply_single_check(self, ast_tree, filename, check, seen_findings, is_root_check=False):
        """Apply a single generic check with proper node type resolution and error handling."""
        findings = []
        check_type = check.get("type") or check.get("check_type")

        # Resolve node_types: check-specific, fallback to root
        if is_root_check:
            required_node_types = self.logic.get("node_types", [])
        else:
            required_node_types = check.get("node_types", self.logic.get("node_types", []))

        matching_nodes = self._find_nodes_by_type(ast_tree, required_node_types) if required_node_types else [ast_tree]
        source_lines = ast_tree.get('source_lines') if isinstance(ast_tree, dict) else None

        for node in matching_nodes:
            node_type = node.get('node_type', 'unknown') if isinstance(node, dict) else 'root'
            node_name = node.get('name', 'unknown') if isinstance(node, dict) else 'root'

            if check_type in ["regex", "pattern"]:
                findings.extend(self._apply_regex_check(check, node, filename, node_type, node_name, source_lines, seen_findings))
            elif check_type == "property_comparison":
                findings.extend(self._apply_property_comparison_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "exists":
                findings.extend(self._apply_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "not_exists":
                findings.extend(self._apply_not_exists_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "numeric_bounds":
                findings.extend(self._apply_numeric_bounds_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "required_present":
                findings.extend(self._apply_required_present_check(check, node, filename, node_type, node_name, seen_findings))
            elif check_type == "ast_property":
                findings.extend(self._apply_ast_property_check(check, node, filename, node_type, node_name, seen_findings))
            else:
                # print(f"[ERROR] Unhandled check type in _apply_single_check: {check_type}")
                pass
        return findings
    def _is_valid_generic_check(self, check):
        """Validate if a check is a generic (non-custom) check that should be processed."""
        check_type = check.get("type") or check.get("check_type")
        # Skip custom functions and invalid check types
        if check_type == "custom_function":
            return False
        # Supported check types
        supported_types = ["regex", "pattern", "property_comparison", "exists", "not_exists", "numeric_bounds", "required_present", "ast_property"]
        if check_type and check_type not in supported_types:
            # print(f"[WARNING] Unsupported check type: {check_type}")
            return False
        return True

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
                # print(f"[DEBUG] Checking regex pattern '{regex_pattern}' against code block: {code_block}")
                if re.search(regex_pattern, code_block):
                    finding = self._make_finding(
                        filename, node_type, node_name, [], code_block,
                        check.get('message', 'Pattern match'), node
                    )
                    unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                    if unique_key not in seen_findings:
                        # print(f"[DEBUG] Found regex match at line {finding.get('line', 0)}")
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
        equals = check.get("equals")
        condition = check.get("condition")
        
        # print(f"[DEBUG] Property comparison check details:")
        # print(f"[DEBUG] - Property path: {property_path}")
        # print(f"[DEBUG] - Starts with: {starts_with}")
        # print(f"[DEBUG] - Node type: {node_type}")
        # print(f"[DEBUG] - Node structure: {node if isinstance(node, dict) else type(node)}")

        if not property_path:
            return findings

        # First check if condition is met (if any)
        if condition:
            cond_path = condition.get("property") or condition.get("path")
            cond_equals = condition.get("equals")
            # print(f"[DEBUG] Checking condition:")
            # print(f"[DEBUG] - Condition path: {cond_path}")
            # print(f"[DEBUG] - Condition equals: {cond_equals}")
            if cond_path and cond_equals:
                cond_values = self._get_property_values(node, cond_path)
                # print(f"[DEBUG] - Condition values found: {cond_values}")
                condition_met = False
                for found_path, value in cond_values:
                    # print(f"[DEBUG] - Checking condition value: {value}")
                    if value == cond_equals:
                        condition_met = True
                        # print(f"[DEBUG] - Condition met!")
                        break
                if not condition_met:
                    # print(f"[DEBUG] - Condition not met, skipping")
                    return findings

        # First check condition if present
        condition_met = True
        if condition:
            cond_property = condition.get('property')
            cond_equals = condition.get('equals')
            # print(f"[DEBUG] Checking condition: property={cond_property} equals={cond_equals}")
            
            cond_values = self._get_property_values(node, cond_property)
            condition_met = False
            for _, cond_value in cond_values:
                # print(f"[DEBUG] Checking condition value: {cond_value}")
                if cond_value == cond_equals:
                    condition_met = True
                    break
            
            if not condition_met:
                # print("[DEBUG] Condition not met, skipping value checks")
                return findings

        # Get property values to check
        property_values = self._get_property_values(node, property_path)
        # print(f"[DEBUG] Found {len(property_values)} values for path {property_path}")
        
        forbidden_values = check.get("forbidden_values", [])
        for found_path, value in property_values:
            print(f"[DEBUG][property_comparison] found_path: {found_path}, value: {value}, forbidden_values: {forbidden_values}")
            # Debug print for ExceptHandler node type
            if node_type == "ExceptHandler" and found_path == ["type", "node_type"]:
                print(f"[DEBUG] Checking ExceptHandler at line {node.get('lineno')}, type.node_type: {value}")
            # Check forbidden_values
            if forbidden_values and value in forbidden_values:
                print(f"[DEBUG][property_comparison] MATCHED forbidden value: {value}")
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value,
                    check.get('message', self.message), node
                )
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)
            # Existing starts_with logic
            if starts_with and isinstance(value, str):
                if value.startswith(starts_with):
                    finding = self._make_finding(
                        filename, node_type, node_name, found_path, value,
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

    def _apply_numeric_bounds_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply numeric_bounds check."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            if not isinstance(value, (int, float)):
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value,
                    "Value not numeric", node
                )
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)
        return findings

    def _apply_required_present_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply required_present check."""
        findings = []
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            if value is None or value == "":
                finding = self._make_finding(
                    filename, node_type, node_name, found_path, value,
                    "Required property missing", node
                )
                unique_key = (self.rule_id, filename, finding.get('line', 0), str(finding.get('property_path', [])))
                if unique_key not in seen_findings:
                    seen_findings.add(unique_key)
                    findings.append(finding)
        return findings

    def _apply_ast_property_check(self, check, node, filename, node_type, node_name, seen_findings):
        """Apply ast_property check."""
        findings = []
        prop_name = check.get("property_name")
        expected_value = check.get("expected_value")
        property_path = check.get("property") or check.get("property_path")
        property_values = self._get_property_values(node, property_path)
        for found_path, value in property_values:
            finding = None
            if isinstance(node, dict) and node.get('node_type') == 'Call' and prop_name:
                keywords = node.get('keywords', []) or []
                for kw in keywords:
                    if not isinstance(kw, dict):
                        continue
                    if kw.get('arg') == prop_name:
                        value_node = kw.get('value', {})
                        if isinstance(value_node, dict) and value_node.get('node_type') == 'Constant':
                            if str(value_node.get('value')) == str(expected_value):
                                finding = self._make_finding(
                                    filename, node_type, node_name, found_path,
                                    f"{prop_name}={expected_value}",
                                    check.get('message', 'Property match'), node
                                )
                                break
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

    def _get_property_values(self, node, property_path, visited=None, depth=0, max_depth=20):
        if not isinstance(node, dict) or not property_path:
            # print("[DEBUG] Early return: node is not dict or no property path")

            return []

        # Convert path to list if it's a string with dot notation
        if isinstance(property_path, str):
            # Split by dots but preserve array notation
            parts = []
            current = ""
            in_brackets = False
            for char in property_path:
                if char == '[':
                    in_brackets = True
                    if current:
                        parts.append(current)
                        current = ""
                    current = char
                elif char == ']':
                    in_brackets = False
                    current += char
                    parts.append(current)
                    current = ""
                elif char == '.' and not in_brackets:
                    if current:
                        parts.append(current)
                        current = ""
                else:
                    current += char
            if current:
                parts.append(current)
            property_path = parts

        # Use iterative approach with stack instead of recursion
        stack = [(node, property_path, [])]  # (current_node, remaining_path, full_path)
        results = []
        visited_nodes = set()  # Track visited nodes by id to prevent cycles

        while stack:
            current_node, current_path, full_path = stack.pop()
            # Safety check - skip if not a dict
            if not isinstance(current_node, dict):
                continue
            # Cycle detection
            node_id = id(current_node)
            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)
            if not current_path:
                continue
            current_key = current_path[0]
            remaining_path = current_path[1:] if len(current_path) > 1 else []
            # Handle wildcard (*) and array index notation - match all keys or specific index
            if current_key == '*':
                # For wildcard, iterate all items in dict
                items = current_node.items() if isinstance(current_node, dict) else enumerate(current_node)
                for key, value in items:
                    if isinstance(current_node, dict) and key in ['lineno', 'col_offset', 'end_lineno', 'node_type', '__parent__', 'ctx', 'parent']:
                        continue
                    key_str = str(key) if isinstance(current_node, dict) else f"[{key}]"
                    new_full_path = full_path + [key_str]
                    if not remaining_path:
                        results.append((new_full_path, value))
                    else:
                        if isinstance(value, dict):
                            stack.append((value, remaining_path, new_full_path))
                        elif isinstance(value, list):
                            stack.append((value, remaining_path, new_full_path))
            elif current_key == '[*]':
                # Wildcard for lists: iterate all items
                if isinstance(current_node, list):
                    for idx, item in enumerate(current_node):
                        new_full_path = full_path + [f"[{idx}]"]
                        if not remaining_path:
                            results.append((new_full_path, item))
                        else:
                            stack.append((item, remaining_path, new_full_path))
            elif current_key.startswith('[') and current_key.endswith(']'):
                # For array index, get specific item
                try:
                    idx = int(current_key[1:-1])
                except ValueError:
                    idx = None
                if idx is not None and isinstance(current_node, list) and 0 <= idx < len(current_node):
                    item = current_node[idx]
                    new_full_path = full_path + [current_key]
                    if not remaining_path:
                        results.append((new_full_path, item))
                    else:
                        stack.append((item, remaining_path, new_full_path))
            # Handle specific key
            elif current_key in current_node:
                value = current_node[current_key]
                new_full_path = full_path + [current_key]
                if not remaining_path:
                    # End of path - add to results
                    results.append((new_full_path, value))
                else:
                    # Continue traversal
                    if isinstance(value, dict):
                        stack.append((value, remaining_path, new_full_path))
                    elif isinstance(value, list):
                        for idx, item in enumerate(value):
                            if isinstance(item, dict):
                                stack.append((item, remaining_path, new_full_path + [f"[{idx}]"]))
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
            # print(f"[DEBUG] Custom function {function_name} not found or not callable")
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
        if not function_name:
            return None
        try:
            import logic_implementations
            if hasattr(logic_implementations, function_name):
                func = getattr(logic_implementations, function_name)
                if callable(func):
                    # print(f"[DEBUG] Successfully loaded custom function: {function_name}")
                    return func
                else:
                    # print(f"[DEBUG] {function_name} exists but is not callable")
                    return None
            else:
                # print(f"[DEBUG] Custom function {function_name} not found in logic_implementations")
                return None
        except ImportError as e:
            # print(f"[ERROR] Cannot import logic_implementations: {e}")
            pass
        except Exception as e:
            # print(f"[ERROR] Error loading custom function {function_name}: {e}")
            return None
        

    def _find_nodes_by_type(self, ast_tree, node_types):
        """
        Find all nodes of specified types in the Python AST using a stack-based approach.
        """
        found_nodes = []
        stack = [(ast_tree, [])]  # Stack of (node, path) tuples
        seen = set()  # Track visited object IDs to prevent cycles
        
        while stack:
            node, path = stack.pop()
            node_id = id(node)
            
            if node_id in seen:
                continue
            seen.add(node_id)
            
            if isinstance(node, dict):
                if node.get('node_type') in node_types:
                    found_nodes.append(node)
                    
                # Add children to stack
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'node_type']:
                        stack.append((value, path + [key]))
                        
            elif isinstance(node, list):
                # Add list items to stack
                for idx, item in enumerate(node):
                    stack.append((item, path + [f"[{idx}]"]))
        return found_nodes

    def _get_property_values(self, node, property_path, visited=None, depth=0, max_depth=20):
        if not isinstance(node, dict) or not property_path:
            return []
        # Convert path to list if it's a string with dot notation
        if isinstance(property_path, str):
            parts = []
            current = ""
            in_brackets = False
            for char in property_path:
                if char == '[':
                    in_brackets = True
                    if current:
                        parts.append(current)
                    current = char
                elif char == ']':
                    in_brackets = False
                    current += char
                    parts.append(current)
                    current = ""
                elif char == '.' and not in_brackets:
                    if current:
                        parts.append(current)
                        current = ""
                else:
                    current += char
            if current:
                parts.append(current)
            property_path = parts
        stack = [(node, property_path, [])]
        results = []
        visited_nodes = set()
        while stack:
            current_node, current_path, full_path = stack.pop()
            if not isinstance(current_node, (dict, list)):
                continue
            node_id = id(current_node)
            if node_id in visited_nodes:
                continue
            visited_nodes.add(node_id)
            if not current_path:
                continue
            current_key = current_path[0]
            remaining_path = current_path[1:] if len(current_path) > 1 else []
            if current_key == '*':
                items = current_node.items() if isinstance(current_node, dict) else enumerate(current_node)
                for key, value in items:
                    if isinstance(current_node, dict) and key in ['lineno', 'col_offset', 'end_lineno', 'node_type', '__parent__', 'ctx', 'parent']:
                        continue
                    key_str = str(key) if isinstance(current_node, dict) else f"[{key}]"
                    new_full_path = full_path + [key_str]
                    if not remaining_path:
                        results.append((new_full_path, value))
                    else:
                        if isinstance(value, dict) or isinstance(value, list):
                            stack.append((value, remaining_path, new_full_path))
            elif current_key == '[*]':
                if isinstance(current_node, list):
                    for idx, item in enumerate(current_node):
                        new_full_path = full_path + [f"[{idx}]"]
                        if not remaining_path:
                            results.append((new_full_path, item))
                        else:
                            stack.append((item, remaining_path, new_full_path))
            elif (isinstance(current_key, str) and current_key.startswith('[') and current_key.endswith(']')):
                try:
                    idx = int(current_key[1:-1])
                except ValueError:
                    idx = None
                if idx is not None and isinstance(current_node, list) and 0 <= idx < len(current_node):
                    item = current_node[idx]
                    new_full_path = full_path + [current_key]
                    if not remaining_path:
                        results.append((new_full_path, item))
                    else:
                        stack.append((item, remaining_path, new_full_path))
            elif isinstance(current_key, int):
                if isinstance(current_node, list) and 0 <= current_key < len(current_node):
                    item = current_node[current_key]
                    new_full_path = full_path + [f"[{current_key}]"]
                    if not remaining_path:
                        results.append((new_full_path, item))
                    else:
                        stack.append((item, remaining_path, new_full_path))
            elif isinstance(current_node, dict) and current_key in current_node:
                value = current_node[current_key]
                new_full_path = full_path + [current_key]
                if not remaining_path:
                    results.append((new_full_path, value))
                else:
                    stack.append((value, remaining_path, new_full_path))
        return results
'''