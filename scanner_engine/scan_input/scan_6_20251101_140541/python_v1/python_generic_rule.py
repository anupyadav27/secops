#!/usr/bin/env python3
import re
import ast
import json
import re
import ast
import json
import check_type_handlers


# Step 1: Logic operation helper functions
def and_logic(*conditions):
    """Return True if ALL conditions are True"""
    return all(conditions)


def or_logic(*conditions):
    """Return True if ANY condition is True"""
    return any(conditions)


def xor_logic(*conditions):
    """Return True if EXACTLY ONE condition is True"""
    return sum(conditions) == 1


# Step 2: Map operator names to functions
logic_map = {
    "and": and_logic,
    "or": or_logic,
    "xor": xor_logic
}


# Step 3: Enhanced condition evaluation function (now modular!)
def evaluate_condition(condition, node):
    """
    Evaluate a single condition on a given node using modular check_type handlers.
    
    Args:
        condition (dict): Condition with check_type, property_path, and check-specific parameters
        node (dict): AST node to evaluate against
        
    Returns:
        bool: True if condition matches, False otherwise
    """
    if not isinstance(condition, dict):
        return False
    check_type = condition.get("check_type", "")
    property_path = condition.get("property_path", [])
    # Debug print for condition evaluation
    # if check_type:
    #     print(f"[COND DEBUG] Checking type: {check_type}, property_path: {property_path}, node_type: {node.get('node_type')}, line: {node.get('lineno')}")
    # Handle node_type check specially (doesn't need property_path extraction)
    if check_type == "node_type":
        handler = check_type_handlers.get_handler(check_type)
        if handler:
            result = handler(condition, node, None)
            # print(f"[COND DEBUG] node_type result: {result}")
            return result
        return False
    # For other checks, extract the value using property_path
    if isinstance(property_path, str):
        property_path = [property_path]
    value = _get_value_from_path(node, property_path)
    # print(f"[COND DEBUG] Extracted value for {check_type}: {value}")
    handler = check_type_handlers.get_handler(check_type)
    if handler:
        if check_type in ["equals", "identical_content"]:
            result = handler(condition, node, value, _get_value_from_path)
        else:
            result = handler(condition, node, value)
        # print(f"[COND DEBUG] Handler result for {check_type}: {result}")
        return result
    return False


# Step 4: Combine results with logic operator using logic_map
def evaluate_logic(logic, node):
    """
    Recursively evaluate logic with operator (and/or/xor).
    
    Args:
        logic (dict): Logic structure with operator and conditions
        node (dict): AST node to evaluate against
        
    Returns:
        bool: Result of logical evaluation
        
    Example:
        logic = {
          "operator": "and",
          "conditions": [
             { "check_type": "node_type", "value": "ClassDef" },
             { "check_type": "regex", "property_path": ["name"], "regex": ".*Person.*" }
          ]
        }
    """
    if not isinstance(logic, dict):
        return False
        
    operator = logic.get("operator", "and")
    conditions = logic.get("conditions", [])
    
    if not conditions:
        return True
        
    results = []
    for condition in conditions:
        if not isinstance(condition, dict):
            results.append(False)
            continue
            
        if "operator" in condition:
            # Nested logic structure - recursive call
            results.append(evaluate_logic(condition, node))
        else:
            # Single condition
            results.append(evaluate_condition(condition, node))
    
    # Use logic_map to apply the operator
    if operator in logic_map:
        return logic_map[operator](*results)
    else:
        # Default to 'and' behavior for unknown operators
        return logic_map["and"](*results)


# Step 5: High-level rule evaluation function
def evaluate_rule(rule_metadata, node):
    """
    Evaluate a complete rule against an AST node.
    
    Args:
        rule_metadata (dict): Complete rule metadata with logic section
        node (dict): AST node to evaluate against
        
    Returns:
        bool: True if the rule matches the node, False otherwise
        
    Example:
        rule = {
            "rule_id": "test_rule",
            "logic": {
                "operator": "and",
                "conditions": [
                    { "check_type": "node_type", "value": "ClassDef" },
                    { "check_type": "equals", "property_path": ["body", "*", "targets", "*", "id"], "other_property_path": ["name"] }
                ]
            }
        }
    """
    logic = rule_metadata.get("logic", {})
    
    # Handle new data-driven logic with operators
    if "operator" in logic:
        return evaluate_logic(logic, node)
    
    # Fallback for legacy rules without operators
    return False


def _get_value_from_path(obj, path):
    """
    Extract value from nested object using property path.
    Supports wildcards (*) and list indexing.
    """
    if not path:
        return obj
        
    current = obj
    for key in path:
        if key == "*":
            # Wildcard - collect all values from current level
            if isinstance(current, list):
                values = []
                for item in current:
                    if isinstance(item, dict):
                        values.append(item)
                return values
            elif isinstance(current, dict):
                return list(current.values())
            return []
        elif isinstance(current, dict):
            if key in current:
                current = current[key]
            else:
                return None
        elif isinstance(current, list) and isinstance(key, int):
            if 0 <= key < len(current):
                current = current[key]
            else:
                return None
        else:
            return None
    return current


def _get_all_values(obj, visited=None):
    """Helper to recursively get all primitive values from a nested structure."""
    if visited is None:
        visited = set()
    
    # Prevent infinite recursion by tracking visited objects
    obj_id = id(obj)
    if obj_id in visited:
        return []
    
    visited.add(obj_id)
    values = []
    
    if isinstance(obj, dict):
        # Skip circular references
        if obj.get('circular_reference'):
            return values
            
        for k, v in obj.items():
            if k not in ['lineno', 'col_offset', 'node_type', 'circular_reference']:
                if isinstance(v, (dict, list)):
                    values.extend(_get_all_values(v, visited))
                else:
                    values.append(v)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                values.extend(_get_all_values(item, visited))
            else:
                values.append(item)
    else:
        values.append(obj)
    
    return values


class PythonGenericRule:
    """
    Generic rule engine for Python AST processing.
    
    Adapts generic rule concepts to Python:
    - node_type instead of resource_type (ClassDef, FunctionDef, etc.)
    - AST traversal instead of Terraform block navigation
    - Property path navigation through AST node attributes
    """

    def __init__(self, metadata):
        """Initialize rule with metadata dictionary.
        
        Args:
            metadata (dict): Rule metadata containing rule_id, title, and logic
        """
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary")
            
        self.metadata = metadata
        self.logic = metadata.get("logic", {})
        if not isinstance(self.logic, dict):
            self.logic = {}  # Initialize empty dict if logic is not a dictionary
            
        self.rule_id = metadata.get("rule_id", "unknown_rule") 
        self.message = metadata.get("title", "Rule violation")

    # ========== CUSTOM LOGIC FUNCTIONS MOVED TO logic_implementations.py ==========

    def _get_custom_function(self, function_name):
        """Get a custom function by name (legacy support)."""
        if function_name is None:
            return None
        
        # Check this class for backward compatibility
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
        visited = set()  # Track visited objects to prevent infinite recursion
        
        def traverse(node):
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)
            
            if isinstance(node, dict):
                # Skip circular references
                if node.get('circular_reference'):
                    return
                    
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
                    if key not in ['lineno', 'col_offset', 'node_type', 'circular_reference']:
                        if isinstance(value, (dict, list)):
                            traverse(value)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
        
        traverse(ast_tree)
        return found_nodes

    def is_applicable(self, ast_tree):
        """
        Returns True if the AST contains at least one node that could potentially match this rule.
        For new data-driven rules with operators, check if any node in AST could satisfy the conditions.
        For legacy rules, use the old logic.
        
        Args:
            ast_tree (dict): The AST to check for applicability
            
        Returns:
            bool: True if the rule could potentially match any node in the tree
        """
        logic = self.logic
        if not isinstance(logic, dict):
            return False
            
        # Handle new data-driven logic with operators
        if "operator" in logic:
            # Check if any node in the AST could potentially match
            return self._check_applicability_recursive(ast_tree, logic)
            
        # Legacy logic handling
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
    
    def _check_applicability_recursive(self, ast_tree, logic):
        """
        Check if any node in the AST tree could potentially satisfy the logic conditions.
        """
        def traverse_and_check(node, visited=None):
            if visited is None:
                visited = set()
            node_id = id(node)
            if node_id in visited:
                return False
            visited.add(node_id)
            if isinstance(node, dict):
                # Skip circular references
                if node.get('circular_reference'):
                    return False
                    
                # Check if this node could match any of the conditions
                if self._could_node_match_logic(node, logic):
                    return True
                # Recursively check children
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'circular_reference']:
                        if isinstance(value, (dict, list)) and traverse_and_check(value, visited):
                            return True
            elif isinstance(node, list):
                for item in node:
                    if traverse_and_check(item, visited):
                        return True
            return False
        
        return traverse_and_check(ast_tree)
    
    def _check_all_nodes_recursive(self, ast_tree, logic, filename, findings, seen_findings):
        def debug_node(node, result):
            # if self.rule_id == "bare_raise_statements_should_only_be_used_in_except_blocks":
            #     print(f"[DEBUG] Rule '{self.rule_id}' at line {node.get('lineno')}, node_type={node.get('node_type')}, exc={node.get('exc', 'MISSING')}, parent_type={node.get('parent', {}).get('node_type') if isinstance(node.get('parent'), dict) else None}, result={result}")
            pass
        """
        Recursively check all nodes in the AST tree against the logic conditions.
        
        Args:
            ast_tree (dict): The AST to traverse
            logic (dict): Logic conditions to evaluate
            filename (str): Name of the file being checked
            findings (list): List to store rule violations
            seen_findings (set): Set to track unique findings
        """
        if not isinstance(logic, dict):
            return
            
        def traverse_and_evaluate(node, visited=None, depth=0):
            if visited is None:
                visited = set()
            if depth > 100:  # Prevent infinite recursion
                return
            node_id = id(node)
            if node_id in visited:
                return
            visited.add(node_id)
            if isinstance(node, dict):
                # Skip circular references
                if node.get('circular_reference'):
                    return
                    
                # Check if this node matches the logic
                result = evaluate_logic(logic, node)
                debug_node(node, result)
                if result:
                    node_type = node.get('node_type', 'Unknown')
                    node_name = node.get('name', 'anonymous')
                    finding = self._make_finding(
                        filename, node_type, node_name, [], None,
                        self.message, node
                    )
                    unique_key = (
                        self.rule_id,
                        filename,
                        finding.get('line', 0),
                        str(finding.get('property_path', []))
                    )
                    if unique_key not in seen_findings:
                        seen_findings.add(unique_key)
                        findings.append(finding)
                # Recursively check children
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'circular_reference']:
                        if isinstance(value, (dict, list)):
                            traverse_and_evaluate(value, visited, depth + 1)
            elif isinstance(node, list):
                for item in node:
                    traverse_and_evaluate(item, visited, depth + 1)
        traverse_and_evaluate(ast_tree)
    
    def _could_node_match_logic(self, node, logic):
        """
        Check if a node could potentially match the given logic.
        This is a lightweight check for applicability.
        
        Args:
            node (dict): The AST node to check
            logic (dict): The logic structure to match against
            
        Returns:
            bool: True if the node could potentially match the logic
        """
        if not isinstance(logic, dict):
            return False
            
        if "operator" in logic:
            conditions = logic.get("conditions", [])
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                    
                if "operator" in condition:
                    if self._could_node_match_logic(node, condition):
                        return True
                else:
                    # Simple condition check
                    check_type = condition.get("check_type", "")
                    if check_type == "node_type":
                        expected_type = condition.get("value", "")
                        if node.get("node_type") == expected_type:
                            return True
                    elif check_type in ["regex", "equals", "contains", "pattern"]:
                        # If node has the structure that could be checked, it's applicable
                        property_path = condition.get("property_path", [])
                        if property_path and self._has_property_path(node, property_path):
                            return True
        return False
    
    def _has_property_path(self, node, property_path):
        """
        Check if a node has a property path (even if the value doesn't match conditions).
        Used for applicability checking.
        """
        if not property_path:
            return True
        
        if isinstance(property_path, str):
            property_path = [property_path]
        
        current = node
        for key in property_path:
            if key == "*":
                # Wildcard means we can traverse further
                return True
            elif isinstance(current, dict) and key in current:
                current = current[key]
            elif isinstance(current, list):
                # If current is a list, check if any item has the key
                for item in current:
                    if isinstance(item, dict) and key in item:
                        current = item[key]
                        break
                else:
                    return False
            else:
                return False
        return True

    def check(self, ast_tree, filename):
        """
        Apply the rule to the Python AST and return findings.
        
        Args:
            ast_tree (dict): The AST to check
            filename (str): Name of the file being checked
            
        Returns:
            list: List of findings (rule violations)
        """
        findings = []
        seen_findings = set()  # Deduplication set: (rule_id, file, line, property_path_str)
        logic = self.logic
        
        if not isinstance(logic, dict):
            return findings  # Return empty list if logic is not properly formatted
        node_types = logic.get("node_type", [])  # Changed from resource_type
        property_paths = logic.get("property_path", [])
        check_type = logic.get("check_type", "")
        forbidden_values = logic.get("forbidden_values", [])
        required_values = logic.get("required_values", [])
        regex_pattern = logic.get("regex", None)

        # Handle new data-driven logic with operators
        if "operator" in logic:
            # For new logic system, traverse all nodes in AST
            self._check_all_nodes_recursive(ast_tree, logic, filename, findings, seen_findings)
            return findings
        
        # Legacy logic handling
        # Find all relevant nodes in the AST
        if node_types == "*":
            target_nodes = [ast_tree]  # Process entire AST
        else:
            target_nodes = self._find_nodes_by_type(ast_tree, node_types)

        for node in target_nodes:
            node_type = node.get('node_type', 'Unknown')
            node_name = node.get('name', 'anonymous')
            
            # Handle legacy custom functions for backward compatibility
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

    def _make_finding(self, filename, node_type, node_name, property_path, value, message=None, node=None):
        """Create a finding with Python-specific information."""
        finding = {
            "rule_id": self.rule_id,
            "message": message or self.message,
            "node": f"{node_type}.{node_name}",  # Changed from "resource"
            "file": filename,
            "property_path": property_path,
            "value": value,
            "status": "violation",
            "line": 1,
            "column": 0
        }
        
        # Add line/column information from Python AST node
        if node and isinstance(node, dict):
            finding["line"] = node.get('lineno', 1)
            finding["column"] = node.get('col_offset', 0)
        
        # Add severity if present in metadata
        if "severity" in self.metadata:
            finding["severity"] = self.metadata["severity"]
        elif "defaultSeverity" in self.metadata:
            finding["severity"] = self.metadata["defaultSeverity"]
            
        return finding 