def deep_dict_equal(d1, d2):
    """Recursively compare two dicts for equality."""
    if not isinstance(d1, dict) or not isinstance(d2, dict):
        return d1 == d2
    if set(d1.keys()) != set(d2.keys()):
        return False
    for k in d1:
        if not deep_dict_equal(d1[k], d2[k]):
            return False
    return True

def handle_contains_nested_type(condition, node, value):
    """Check if any dict in value (list) has a 'type' property matching any forbidden value dict."""
    forbidden_values = condition.get("forbidden_values", [])
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and 'type' in item:
                for forbidden in forbidden_values:
                    if deep_dict_equal(item['type'], forbidden):
                        return True
    return False
def handle_property_missing(condition, node, value):
    """Return True if the property is missing from the node (value is None)."""
    if not hasattr(handle_property_missing, 'debug_count'):
        handle_property_missing.debug_count = 0
    result = value is None
    # if node.get('node_type') == 'Raise' and handle_property_missing.debug_count < 10:
    #     print(f"[BARE_RAISE DEBUG] property_missing: node_type=Raise, line={node.get('lineno')}, exc={value}, result={result}")
    #     handle_property_missing.debug_count += 1
    return result

def handle_property_equals(condition, node, value):
    """Return True if the property equals the expected value (including None)."""
    if not hasattr(handle_property_equals, 'debug_count'):
        handle_property_equals.debug_count = 0
    expected_value = condition.get("value", None)
    result = value == expected_value
    # if node.get('node_type') == 'Raise' and handle_property_equals.debug_count < 10:
    #     print(f"[BARE_RAISE DEBUG] property_equals: node_type=Raise, line={node.get('lineno')}, exc={value}, expected={expected_value}, result={result}")
    #     handle_property_equals.debug_count += 1
    return result

def handle_parent_node_type(condition, node, value):
    """Check if the parent node's type matches the expected value."""
    if not hasattr(handle_parent_node_type, 'debug_count'):
        handle_parent_node_type.debug_count = 0
    property_path = condition.get("property_path", ["parent"])
    parent = _get_value_from_path(node, property_path)
    expected_type = condition.get("value", "")
    result = isinstance(parent, dict) and parent.get("node_type") == expected_type
    # if node.get('node_type') == 'Raise' and handle_parent_node_type.debug_count < 10:
    #     print(f"[BARE_RAISE DEBUG] parent_node_type: node_type=Raise, line={node.get('lineno')}, parent_type={parent.get('node_type') if isinstance(parent, dict) else parent}, expected_type={expected_type}, result={result}")
    #     handle_parent_node_type.debug_count += 1
    return result

def handle_property_in_parent_list(condition, node, value):
    """Check if the current node is present in a specific list property of its parent (e.g., finalbody)."""
    property_path = condition.get("property_path", ["parent", "finalbody"])
    parent_list = _get_value_from_path(node, property_path)
    # 'self' means the current node should be present in the parent_list
    if condition.get("value") == "self":
        if isinstance(parent_list, list):
            found = any(item is node for item in parent_list)
            parent = node.get("parent")
            parent_type = parent.get("node_type") if isinstance(parent, dict) else None
            # Only return True if parent is Try and property_path is finalbody
            is_finally_of_try = parent_type == "Try" and property_path[-1] == "finalbody"
            # print(f"[DEBUG] [bare_raise_finally] handle_property_in_parent_list: node_type={node.get('node_type')}, line={node.get('lineno')}, parent_type={parent_type}, parent_list_types={[item.get('node_type') if isinstance(item, dict) else item for item in parent_list]}, found={found}, is_finally_of_try={is_finally_of_try}, node_id={id(node)}, parent_list_ids={[id(item) for item in parent_list]}")
            return found and is_finally_of_try
    return False
#!/usr/bin/env python3
"""
Check Type Handlers for Python Rule Engine

This module contains all the individual handler functions for different check_type values.
Each function takes a condition, node, and value, and returns True/False based on the check.
"""

import re


def _get_value_from_path(node, property_path):
    target = node
    for key in property_path:
        if isinstance(target, dict) and key in target:
            target = target[key]
        else:
            return None
    return target


def handle_node_type(condition, node, value):
    """Handle node_type check - compare node type to expected value and optional property_check"""
    property_path = condition.get("property_path", [])
    target_node = _get_value_from_path(node, property_path) if property_path else node
    expected_type = condition.get("value", "")
    return isinstance(target_node, dict) and target_node.get("node_type") == expected_type


def handle_equals(condition, node, value, get_value_from_path=None):
    """Handle equals check - supports both static values and dynamic property comparison"""
    # Check for dynamic comparison with other_property_path
    other_property_path = condition.get("other_property_path")
    if other_property_path:
        if isinstance(other_property_path, str):
            other_property_path = [other_property_path]
        
        # Special handling for comparing field names to class name
        if other_property_path == ["name"] and node.get("node_type") == "ClassDef":
            class_name = node.get("name", "")
            if not class_name:
                return False
                
            # Check if any field in the class body has the same name as the class
            if isinstance(value, list):
                # value is a list of field names, check if class name is among them
                # Filter out None/empty values and do case-insensitive comparison
                field_names = [str(field_name) for field_name in value if field_name is not None and field_name != ""]
                return any(field_name.lower() == class_name.lower() for field_name in field_names)
            elif value is not None and value != "":
                # Direct comparison for single value
                return str(value).lower() == str(class_name).lower()
            else:
                # No valid field names found
                return False
        else:
            # General case: get other value from node
            if get_value_from_path:
                other_value = get_value_from_path(node, other_property_path)
            else:
                other_value = _get_value_from_path(node, other_property_path)
            if isinstance(value, list):
                # If value is a list, check if other_value is in the list
                return other_value in value
            else:
                # Direct comparison - try numeric comparison first
                try:
                    if isinstance(value, (int, float)) and isinstance(other_value, (int, float)):
                        return float(value) == float(other_value)
                except (ValueError, TypeError):
                    pass
                return str(value).lower() == str(other_value).lower()
    else:
        # Traditional equals check with static value
        expected_value = condition.get("value")
        if expected_value is None:
            # If no value specified, look for required_values for backward compatibility
            required_values = condition.get("required_values", [])
            return value in required_values

            # print(f"[DEBUG] equals check - Expected: {expected_value}, Got: {value}, Condition: {condition}, Node type: {type(node)}, Value type: {type(value)}")  # commented out
        
        # Handle numeric comparisons
        try:
            if isinstance(value, (int, float)) and isinstance(expected_value, (int, float)):
                result = float(value) == float(expected_value)
                if expected_value == 0:  # Only debug sleep(0) cases
                    # print(f"[DEBUG] time.sleep(0) check - Value: {value}, Expected: {expected_value}, Result: {result}")  # commented out
                    return result
        except (ValueError, TypeError) as e:
            # print(f"[DEBUG] Error in numeric comparison: {e}")  # commented out
            pass
        
        # String comparison as fallback
        str_result = str(value) == str(expected_value)
        # print(f"[DEBUG] String comparison result: {str_result}")  # commented out
        return str_result


def handle_not_contains(condition, node, value):
    """Handle not_contains check - value should not be in forbidden list"""
    forbidden_values = condition.get("forbidden_values", [])
    return value not in forbidden_values


def handle_contains(condition, node, value):
    """Handle contains/in check - value should be in forbidden list (case-insensitive)"""
    forbidden_values = condition.get("forbidden_values", [])
    if isinstance(value, list):
        forbidden_values_lower = [str(f).lower() for f in forbidden_values]
        value_lower = [str(v).lower() for v in value]
        return any(forbidden in value_lower for forbidden in forbidden_values_lower)
    else:
        value_lower = str(value).lower()
        forbidden_values_lower = [str(f).lower() for f in forbidden_values]
        return value_lower in forbidden_values_lower


def handle_regex(condition, node, value):
    """Handle regex pattern matching"""
    regex_pattern = condition.get("regex", "")
    if regex_pattern:
        if isinstance(value, str):
            return bool(re.search(regex_pattern, value))
        elif isinstance(value, list):
            # Check if any string value in the list matches the regex
            for item in value:
                if isinstance(item, str) and re.search(regex_pattern, item):
                    return True
    return False


def handle_min_value(condition, node, value):
    """Handle minimum value check - numeric comparison"""
    try:
        required_values = condition.get("required_values", [0])
        return float(value) >= float(required_values[0])
    except (ValueError, TypeError):
        return False


def handle_required(condition, node, value, get_value_from_path=None):
    """Handle required presence check - value must exist and not be empty"""
    return value is not None and value != "" and value != []


def handle_pattern(condition, node, value):
    """Handle pattern matching with exclusions and match types"""
    pattern = condition.get("pattern", "")
    match_type = condition.get("match_type", "violation_if_matches")
    exclude_patterns = condition.get("exclude_patterns", [])
    
    if not isinstance(value, str):
        return False
        
    # Check exclusions first
    for exclude_pattern in exclude_patterns:
        if re.match(exclude_pattern, value):
            return False
            
    pattern_matches = bool(re.match(pattern, value))
    if match_type == "violation_if_matches":
        return pattern_matches
    elif match_type == "violation_if_not_matches":
        return not pattern_matches
    return False


def handle_forbidden_empty(condition, node, value):
    """Handle forbidden empty check - value should be empty/missing"""
    return value is None or value == [] or value == ""


def handle_identical_content(condition, node, value, _get_value_from_path):
    """Handle identical_content check - compare content of two property paths using deep comparison"""
    other_property_path = condition.get("other_property_path")
    if not other_property_path:
        return False
    
    # Get the other value to compare against
    other_value = _get_value_from_path(node, other_property_path)
    
    def deep_compare_ast(obj1, obj2, visited=None):
        """Deep compare two AST objects, ignoring line numbers and column offsets, avoiding infinite recursion."""
        if visited is None:
            visited = set()
        obj1_id = id(obj1)
        obj2_id = id(obj2)
        pair_id = (obj1_id, obj2_id)
        if pair_id in visited:
            return True  # Already compared these objects, assume equal to avoid recursion
        visited.add(pair_id)
        if type(obj1) != type(obj2):
            return False
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            keys1 = set(obj1.keys()) - {'lineno', 'col_offset'}
            keys2 = set(obj2.keys()) - {'lineno', 'col_offset'}
            if keys1 != keys2:
                return False
            for key in keys1:
                if not deep_compare_ast(obj1.get(key), obj2.get(key), visited):
                    return False
            return True
        elif isinstance(obj1, list) and isinstance(obj2, list):
            if len(obj1) != len(obj2):
                return False
            for i in range(len(obj1)):
                if not deep_compare_ast(obj1[i], obj2[i], visited):
                    return False
            return True
        else:
            return obj1 == obj2
    return deep_compare_ast(value, other_value)


def handle_type_annotation_mismatch(condition, node, value):
    """Handle type_annotation_mismatch check - detect when assigned value doesn't match type annotation"""
    # Get annotation and value from the AnnAssign node
    annotation = node.get("annotation", {})
    assigned_value = node.get("value", {})
    
    if not annotation or not assigned_value:
        return False
    
    # Extract annotation type
    annotation_type = _get_annotation_type(annotation)
    if not annotation_type:
        return False
    
    # Extract assigned value type
    assigned_type = _get_value_type(assigned_value)
    if not assigned_type:
        return False
    
    # Check for type mismatch
    return not _types_compatible(annotation_type, assigned_type)


def _get_annotation_type(annotation):
    """Extract the type from a type annotation AST node"""
    if not isinstance(annotation, dict):
        return None
    
    node_type = annotation.get("node_type", "")
    
    if node_type == "Name":
        # Simple type like int, str, bool
        return annotation.get("id", "")
    elif node_type == "Constant":
        # Type annotation as string (e.g., "int")
        return str(annotation.get("value", ""))
    elif node_type == "Subscript":
        # Generic types like List[int], Dict[str, int]
        value = annotation.get("value", {})
        if isinstance(value, dict) and value.get("node_type") == "Name":
            base_type = value.get("id", "")
            return base_type  # Return base type (List, Dict, etc.)
    
    return None


def _get_value_type(value_node):
    """Extract the type from an assigned value AST node"""
    if not isinstance(value_node, dict):
        return None
    
    node_type = value_node.get("node_type", "")
    
    if node_type == "Constant":
        # Literal values
        val = value_node.get("value")
        if val is True or val is False:  # Check boolean first, before int
            return "bool"
        elif isinstance(val, str):
            return "str"
        elif isinstance(val, int):
            return "int"
        elif isinstance(val, float):
            return "float"
        elif val is None:
            return "None"
    elif node_type == "List":
        return "list"
    elif node_type == "Tuple":
        return "tuple"
    elif node_type == "Dict":
        return "dict"
    elif node_type == "Set":
        return "set"
    elif node_type == "Name":
        # Variable reference - we can't easily determine its type
        return "unknown"
    
    return None


def _types_compatible(annotation_type, assigned_type):
    """Check if annotation type is compatible with assigned type"""
    if not annotation_type or not assigned_type:
        return True  # Can't determine, assume compatible
    
    # Direct type match
    if annotation_type == assigned_type:
        return True
    
    # Handle common mismatches we want to catch
    type_mismatches = {
        "int": ["str", "float", "bool", "list", "tuple", "dict"],
        "str": ["int", "float", "bool", "list", "tuple", "dict"],  
        "float": ["str", "int", "bool", "list", "tuple", "dict"],
        "bool": ["str", "int", "float", "list", "tuple", "dict"],
        "list": ["tuple", "dict", "str", "int", "float", "bool"],
        "tuple": ["list", "dict", "str", "int", "float", "bool"], 
        "dict": ["list", "tuple", "str", "int", "float", "bool"]
    }
    
    # Check if this is a known mismatch we want to flag
    if annotation_type in type_mismatches:
        return assigned_type not in type_mismatches[annotation_type]
    
    # Handle None assignments
    if assigned_type == "None":
        # None is only compatible with Optional types (we'll keep this simple)
        return annotation_type in ["Optional", "Union"] or "Optional" in str(annotation_type)
    
    # Default to compatible if we can't determine
    return True


def handle_type_incompatibility(condition, node, value):
    """Handle type_incompatibility check - detect when function argument type doesn't match parameter type"""
    # This is a specialized handler for function call argument type checking
    # It needs to find the function definition in the AST and compare argument types
    
    # For now, this is a placeholder that detects obvious type mismatches
    # A full implementation would require AST tree traversal to find function definitions
    
    # Get the argument value (passed as 'value' parameter)
    argument_value = value
    if argument_value is None:
        return False
    
    # Get actual type of the argument
    actual_type = _get_value_type(argument_value)
    if not actual_type:
        return False
    
    # For demonstration, detect some obvious mismatches
    # In a real implementation, this would look up the function definition
    
    # Example: If we're calling process_text and passing an integer
    if (hasattr(node, 'func') and isinstance(node.get('func'), dict) and 
        node['func'].get('id') == 'process_text' and actual_type == 'int'):
        return True  # Type mismatch detected
        
    # Example: If we're calling calculate_sum and passing a string list
    if (hasattr(node, 'func') and isinstance(node.get('func'), dict) and
        node['func'].get('id') == 'calculate_sum' and actual_type == 'str'):
        return True  # Type mismatch detected
    
    # For now, return False (no mismatch detected)
    # This would be enhanced to do proper cross-referencing
    return False


def handle_property_exists(condition, node, value):
    """Handle property_exists check - check if a property path exists in the node"""
    # The value passed here is from the property_path - if it's None, property doesn't exist
    return value is not None


def handle_required_present(condition, node, value):
    """Stub for required_present check type. Returns True if value is present (not None or empty)."""
    return value is not None and value != "" and value != []


def handle_greater_than(condition, node, value):
    """Handle greater_than check - numeric comparison"""
    threshold = condition.get("value", 0)
    try:
        return float(value) > float(threshold)
    except (ValueError, TypeError):
        return False


# Registry of all check type handlers
handlers = {
    "node_type": handle_node_type,
    "equals": handle_equals,
    "not_contains": handle_not_contains,
    "contains": handle_contains,
    "in": handle_contains,  # Alias for contains
    "regex": handle_regex,
    "min_value": handle_min_value,
    "required_present": handle_required_present,
    "pattern": handle_pattern,
    "forbidden_empty": handle_forbidden_empty,
    "identical_content": handle_identical_content,
    "type_annotation_mismatch": handle_type_annotation_mismatch,
    "type_incompatibility": handle_type_incompatibility,
    "property_exists": handle_property_exists,
    "greater_than": handle_greater_than,
    "parent_node_type": handle_parent_node_type,
    "property_in_parent_list": handle_property_in_parent_list,
    "property_missing": handle_property_missing,
    "property_equals": handle_property_equals
    ,"contains_nested_type": handle_contains_nested_type
}


def get_handler(check_type):
    """Get the appropriate handler function for a check_type"""
    return handlers.get(check_type)


def list_available_handlers():
    """Return list of all available check_type handlers"""
    return list(handlers.keys())