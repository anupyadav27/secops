# Custom function to detect deeply nested control flow statements
def is_deeply_nested_control_flow(node, ast_root=None, max_depth=3):
    """
    Returns True if the node is a control flow statement (If, For, While, Try, With) and is nested deeper than max_depth.
    Calculates nesting depth by traversing from AST root if __parent__ is missing.
    """
    CONTROL_FLOW_TYPES = ["If", "For", "While", "Try", "With"]
    if not isinstance(node, dict) or node.get('node_type') not in CONTROL_FLOW_TYPES:
        return False
    def get_nesting_depth(n, root):
        # If __parent__ is present, use it
        depth = 1
        parent = n.get('__parent__')
        while parent:
            if parent.get('node_type') in CONTROL_FLOW_TYPES:
                depth += 1
            parent = parent.get('__parent__')
        if n.get('__parent__'):
            return depth
        # Otherwise, traverse from root
        def find_path(cur, target, path):
            if cur is target:
                return path
            if isinstance(cur, dict):
                for k, v in cur.items():
                    if isinstance(v, dict):
                        res = find_path(v, target, path + [cur])
                        if res:
                            return res
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, dict):
                                res = find_path(item, target, path + [cur])
                                if res:
                                    return res
            return None
        path = find_path(root, n, []) or []
        depth = 1
        for ancestor in path:
            if ancestor.get('node_type') in CONTROL_FLOW_TYPES:
                depth += 1
        return depth
    actual_depth = get_nesting_depth(node, ast_root) if ast_root else 1
    return actual_depth > max_depth
def is_out_of_range_datetime_constructor(node, ast_root=None):
    """
    Returns True if a Call node to datetime/date/time has out-of-range month or day arguments.
    Triggers for month < 1 or > 12, day < 1 or > 31.
    Handles both direct and attribute calls.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'Call':
        return False
    func = node.get('func', {})
    func_name = func.get('attr') or func.get('id')
    if func_name not in ("datetime", "date", "time"):
        return False
    args = node.get('args', [])
    # Month is args[1], day is args[2] (if present)
    if len(args) > 1 and isinstance(args[1], dict):
        month = args[1].get('value')
        if isinstance(month, int) and (month < 1 or month > 12):
            return True
    if len(args) > 2 and isinstance(args[2], dict):
        day = args[2].get('value')
        if isinstance(day, int) and (day < 1 or day > 31):
            return True
    return False
# Custom function to detect single-character character classes in regex strings
def has_single_character_class(node, ast_root=None):
    """
    Returns True if a regex string in a Call node contains a character class with only one character.
    """
    import re
    if not isinstance(node, dict) or node.get('node_type') != 'Call':
        return False
    args = node.get('args', [])
    if not args or not isinstance(args[0], dict):
        return False
    regex_str = None
    for key in ['s', 'value', 'constant', 'str', 'text']:
        if isinstance(args[0].get(key), str):
            regex_str = args[0][key]
            break
    if not isinstance(regex_str, str):
        return False
    for match in re.finditer(r'\[(.*?)\]', regex_str):
        char_class = match.group(1)
        if len(char_class) == 1:
            return True
    return False
# Custom function to detect duplicate characters in regex character classes (case-insensitive)
def has_duplicate_character_class(node, ast_root=None):
    """
    Returns True if a regex string in a Call node contains a character class with duplicate characters (case-insensitive).
    """
    import re
    print('[DEBUG][has_duplicate_character_class] Called for node:', node.get('node_type'), 'at line', node.get('lineno'))
    if not isinstance(node, dict) or node.get('node_type') != 'Call':
        print('[DEBUG][has_duplicate_character_class] Not a Call node')
        return False
    args = node.get('args', [])
    if not args or not isinstance(args[0], dict):
        print('[DEBUG][has_duplicate_character_class] No args or first arg not dict')
        return False
    regex_str = None
    # Try common keys for string value in AST node
    for key in ['s', 'value', 'constant', 'str', 'text']:
        if isinstance(args[0].get(key), str):
            regex_str = args[0][key]
            break
    print('[DEBUG][has_duplicate_character_class] Regex string:', regex_str)
    if not isinstance(regex_str, str):
        print('[DEBUG][has_duplicate_character_class] Regex string not str')
        return False
    for match in re.finditer(r'\[(.*?)\]', regex_str):
        char_class = match.group(1)
        print('[DEBUG][has_duplicate_character_class] Found character class:', char_class)
        seen = set()
        for c in char_class:
            c_lower = c.lower()
            if c_lower in seen:
                print('[DEBUG][has_duplicate_character_class] Duplicate found:', c)
                return True
            seen.add(c_lower)
    print('[DEBUG][has_duplicate_character_class] No duplicates found')
    return False
def is_typing_generic_import(node):
    pass

# Custom function to detect unconditional replacement of collection content in For nodes
def is_unconditional_collection_replacement(node, ast_root=None):
    """
    Returns True if a For node replaces collection content unconditionally (not inside an If).
    Example:
        for i in my_list:
            my_list[i] = 'replacement'  # Unconditional
    """
    # Only process For nodes
    if not isinstance(node, dict) or node.get('node_type') != 'For':
        return False
    # Check if the body contains an assignment to a collection element
    body = node.get('body', [])
    for stmt in body:
        if stmt.get('node_type') == 'Assign':
            targets = stmt.get('targets', [])
            # Look for subscript assignment: my_list[i] = ...
            for target in targets:
                if target.get('node_type') == 'Subscript':
                    # Unconditional if parent is not an If node
                    # Check if parent is an If node (by traversing up if ast_root is provided)
                    if ast_root:
                        # Traverse up to see if this For node is inside an If
                        def is_inside_if(n, parent=None):
                            if n is node:
                                return False
                            if n.get('node_type') == 'If' and node in n.get('body', []):
                                return True
                            for k in ['body', 'orelse', 'args', 'targets', 'value', 'test']:
                                v = n.get(k)
                                if isinstance(v, list):
                                    for child in v:
                                        if isinstance(child, dict):
                                            if is_inside_if(child, n):
                                                return True
                                elif isinstance(v, dict):
                                    if is_inside_if(v, n):
                                        return True
                            return False
                        if is_inside_if(ast_root):
                            return False
                    return True
    return False

    # Custom function to detect meaningless chained collection size comparisons
    def is_meaningless_collection_comparison(node, ast_root=None):
        """
        Returns True if a Compare node has chained comparison with a constant in the middle (e.g., len(x) > 5 > len(y)).
        """
        if not isinstance(node, dict) or node.get('node_type') != 'Compare':
            return False
        comparators = node.get('comparators', [])
        # Chained comparison: len(x) > 5 > len(y)
        if len(comparators) >= 2:
            # Check if the first comparator is a constant (int/float)
            first = comparators[0]
            if isinstance(first, (int, float)):
                return True
        return False
    if node.get('node_type') == 'ImportFrom' and node.get('module') == 'typing':
        forbidden = {'List', 'Dict', 'Set', 'Tuple', 'Union'}
        for name_obj in node.get('names', []):
            if isinstance(name_obj, dict) and name_obj.get('name') in forbidden:
                return True
    return False
# Custom function to detect unused scope-limited definitions
def is_unused_scopelimited_definition(node, ast_root=None):
    """
    Returns True if a variable assigned in a function (Assign node) is never used in that function.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'Assign':
        return False
    targets = node.get('targets', [])
    if not targets or not isinstance(targets[0], dict):
        return False
    var_name = targets[0].get('id')
    if not var_name:
        return False
    # Find the nearest FunctionDef parent, or use ast_root if provided
    func_root = None
    root = node
    while root.get('__parent__'):
        if root.get('__parent__', {}).get('node_type') == 'FunctionDef':
            func_root = root.get('__parent__')
            break
        root = root.get('__parent__')
    if not func_root and ast_root:
        func_root = ast_root
    used = False
    def search_usage(n):
        nonlocal used
        if isinstance(n, dict):
            if n.get('node_type') == 'Name' and n.get('id') == var_name:
                used = True
            for v in n.values():
                search_usage(v)
        elif isinstance(n, list):
            for item in n:
                search_usage(item)
    if func_root:
        search_usage(func_root)
    else:
        search_usage(node)
    return not used
# Custom function to detect unused private nested classes
def is_unused_private_nested_class(node, ast_root=None):
    """
    Returns True if a private nested class (name starts with '_') is never used in the codebase.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'ClassDef':
        return False
    class_name = node.get('name')
    if not class_name or not class_name.startswith('_'):
        return False

    # Custom function to detect list comprehensions used only to copy collections
def is_comprehension_only_copy(node, ast_root=None):
    """
    Returns True if a ListComp node is used only to copy another collection (e.g., [i for i in b]).
    """
    if not isinstance(node, dict) or node.get('node_type') != 'ListComp':
        return False
    elt = node.get('elt')
    generators = node.get('generators', [])
    if not generators or not isinstance(elt, dict):
        return False
    gen = generators[0]
    # Check if elt is a Name and matches the target of the generator
    if elt.get('node_type') == 'Name' and gen.get('target', {}).get('node_type') == 'Name':
        if elt.get('id') == gen.get('target', {}).get('id'):
            # Only one generator, no ifs, and iter is a Name (e.g., b)
            if len(generators) == 1 and not gen.get('ifs') and gen.get('iter', {}).get('node_type') == 'Name':
                return True
    return False

# Custom function to detect constructors around generator expressions
def is_constructor_around_generator_expression(node, ast_root=None):
    """
    Returns True if a Call node is a constructor (list, set, tuple) around a generator expression.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'Call':
        return False
    func = node.get('func', {})
    if func.get('node_type') == 'Name' and func.get('id') in {'list', 'set', 'tuple'}:
        args = node.get('args', [])
        if args and isinstance(args[0], dict) and args[0].get('node_type') == 'GeneratorExp':
            return True
    return False

# Custom function to detect nested If statements
def is_nested_conditional_expression(node, ast_root=None):
    """
    Returns True if an If node contains another If node in its body.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'If':
        return False
    body = node.get('body', [])
    for stmt in body:
        if isinstance(stmt, dict) and stmt.get('node_type') == 'If':
            return True
    return False

# Custom function for comparison to None as a constant
def is_comparison_to_none_constant(node, ast_root=None):
    """
    Returns True if a Compare node compares to None as a constant.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'Compare':
        return False
    comparators = node.get('comparators', [])
    for comp in comparators:
        if isinstance(comp, dict) and comp.get('node_type') == 'Constant' and comp.get('value') is None:
            return True
    return False
    # Check if this class is nested (parent is also a ClassDef)
    parent = node.get('__parent__')
    if not parent or parent.get('node_type') != 'ClassDef':
        return False
    # Search for usage of this nested class in the AST
    used = False
    def search_usage(n):
        nonlocal used
        if isinstance(n, dict):
            # Look for instantiation or reference: A._NestedClass or _NestedClass()
            if n.get('node_type') == 'Attribute' and n.get('attr') == class_name:
                used = True
            elif n.get('node_type') == 'Name' and n.get('id') == class_name:
                used = True
            for v in n.values():
                search_usage(v)
        elif isinstance(n, list):
            for item in n:
                search_usage(item)
    # Use ast_root if provided, else walk up to module root
    root = ast_root if ast_root else node
    while root.get('__parent__'):
        root = root.get('__parent__')
    search_usage(root)
    return not used
# Custom function to detect unused local variables
def is_unused_local_variable(node, ast_root=None):
    """
    Returns True if a local variable assigned in an Assign node is never used in the function body.
    """
    print('[DEBUG][is_unused_local_variable] Called for node:', node.get('node_type'), 'at line', node.get('lineno'))
    if not isinstance(node, dict) or node.get('node_type') != 'Assign':
        print('[DEBUG][is_unused_local_variable] Node is not Assign')
        return False
    targets = node.get('targets', [])
    if not targets or not isinstance(targets[0], dict):
        print('[DEBUG][is_unused_local_variable] No valid targets')
        return False
    var_name = targets[0].get('id')
    print('[DEBUG][is_unused_local_variable] Variable name:', var_name)
    if not var_name:
        print('[DEBUG][is_unused_local_variable] No variable name')
        return False
    # Find the nearest FunctionDef parent, or use ast_root if provided
    func_root = None
    root = node
    while root.get('__parent__'):
        if root.get('__parent__', {}).get('node_type') == 'FunctionDef':
            func_root = root.get('__parent__')
            break
        root = root.get('__parent__')
    if not func_root and ast_root:
        func_root = ast_root
    print('[DEBUG][is_unused_local_variable] Function root node_type:', func_root.get('node_type') if func_root else None)
    used = False
    def search_usage(n):
        nonlocal used
        if isinstance(n, dict):
            if n.get('node_type') == 'Name' and n.get('id') == var_name:
                print('[DEBUG][is_unused_local_variable] Usage found for:', var_name, 'at line', n.get('lineno'))
                used = True
            for v in n.values():
                search_usage(v)
        elif isinstance(n, list):
            for item in n:
                search_usage(item)
    if func_root:
        search_usage(func_root)
    else:
        print('[DEBUG][is_unused_local_variable] No function root found, searching from node')
        search_usage(node)
    print('[DEBUG][is_unused_local_variable] Used:', used)
    return not used
# Custom function to detect unused imports
def is_unused_import(node, ast_root=None):
    """
    Returns True if an import in an Import node is unused in the AST.
    """
    print('[DEBUG][is_unused_import] Called for node:', node.get('node_type'), 'at line', node.get('lineno'))
    if not isinstance(node, dict) or node.get('node_type') != 'Import':
        print('[DEBUG][is_unused_import] Node is not Import')
        return False
    imported_names = [alias.get('name') for alias in node.get('names', []) if isinstance(alias, dict)]
    print('[DEBUG][is_unused_import] Imported names:', imported_names)
    root = ast_root if ast_root is not None else node
    while root.get('__parent__'):
        root = root.get('__parent__')
    used_names = set()
    def collect_used_names(n):
        if isinstance(n, dict):
            if n.get('node_type') == 'Name':
                used_names.add(n.get('id'))
            elif n.get('node_type') == 'Attribute':
                # Add the base name of the attribute (e.g., math in math.sqrt)
                value = n.get('value')
                if isinstance(value, dict) and value.get('node_type') == 'Name':
                    used_names.add(value.get('id'))
            for v in n.values():
                collect_used_names(v)
        elif isinstance(n, list):
            for item in n:
                collect_used_names(item)
    collect_used_names(root)
    print('[DEBUG][is_unused_import] Used names in AST:', used_names)
    unused_found = False
    for name in imported_names:
        if name not in used_names:
            print('[DEBUG][is_unused_import] Unused import detected:', name)
            unused_found = True
    if unused_found:
        return True
    print('[DEBUG][is_unused_import] All imports are used')
    return False
# Shared custom function for bare raise statement context detection
def is_unread_private_attribute(node, ast_root=None):
    """
    Returns True if a private attribute (name starts with '_') assigned in a class is never read anywhere in the class.
    """
    print('[DEBUG][is_unread_private_attribute] Called for node:', node.get('node_type'), 'at line', node.get('lineno'))
    targets = node.get('targets', [])
    if not targets or not isinstance(targets[0], dict):
        print('[DEBUG][is_unread_private_attribute] No valid targets')
        return False
    target = targets[0]
    attr_name = None
    if target.get('node_type') == 'Attribute':
        attr_name = target.get('attr')
    elif target.get('node_type') == 'Name':
        attr_name = target.get('id')
    print('[DEBUG][is_unread_private_attribute] Attribute name:', attr_name)
    if not attr_name or not attr_name.startswith('_') or attr_name.startswith('__'):
        print('[DEBUG][is_unread_private_attribute] Not a private attribute')
        return False
    # Find the nearest ClassDef ancestor by walking up the parent chain
    current = node
    class_node = None
    while current:
        parent = current.get('__parent__')
        if parent:
            print('[DEBUG][is_unread_private_attribute] Traversing parent node_type:', parent.get('node_type'))
            if parent.get('node_type') == 'ClassDef':
                class_node = parent
                break
        current = parent
    print('[DEBUG][is_unread_private_attribute] Class node_type:', class_node.get('node_type') if class_node else None)
    if not class_node:
        print('[DEBUG][is_unread_private_attribute] No ClassDef ancestor found')
        return False
    used = False
    def search_usage(n):
        nonlocal used
        if n is node:
            print(f'[DEBUG][is_unread_private_attribute] Skipping assignment node itself at line {n.get("lineno")}')
            return  # Skip the assignment node itself
        if isinstance(n, dict):
            if n.get('node_type') == 'Attribute' and n.get('attr') == attr_name:
                print('[DEBUG][is_unread_private_attribute] Usage found for:', attr_name, 'at line', n.get('lineno'))
                used = True
            elif n.get('node_type') == 'Name' and n.get('id') == attr_name:
                print('[DEBUG][is_unread_private_attribute] Usage found for:', attr_name, 'at line', n.get('lineno'))
                used = True
            # Also skip nested Assign nodes for the same attribute
            if n.get('node_type') == 'Assign':
                targets = n.get('targets', [])
                target = targets[0] if targets and isinstance(targets[0], dict) else None
                target_name = None
                if target:
                    if target.get('node_type') == 'Attribute':
                        target_name = target.get('attr')
                    elif target.get('node_type') == 'Name':
                        target_name = target.get('id')
                if target_name == attr_name and n is not node:
                    print(f'[DEBUG][is_unread_private_attribute] Skipping nested assignment for {attr_name} at line {n.get("lineno")}')
                    return
            for v in n.values():
                search_usage(v)
        elif isinstance(n, list):
            for item in n:
                search_usage(item)
    search_usage(class_node)
    print('[DEBUG][is_unread_private_attribute] Used:', used)
    return not used
def is_unused_classprivate_method(node, ast_root=None):
    """
    Returns True if a private method (name starts with '_') in a class is never called in its class.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'FunctionDef':
        return False
    method_name = node.get('name')
    if not method_name or not method_name.startswith('_') or method_name.startswith('__'):
        return False
    # Find the parent class
    parent = node.get('__parent__')
    if not parent or parent.get('node_type') != 'ClassDef':
        return False
    # Search for usage of this method in the class
    used = False
    def search_usage(n):
        nonlocal used
        if isinstance(n, dict):
            # Look for method call: self._method() or _method()
            if n.get('node_type') == 'Call':
                func = n.get('func')
                if isinstance(func, dict):
                    # self._method()
                    if func.get('node_type') == 'Attribute' and func.get('attr') == method_name:
                        used = True
                    # _method()
                    elif func.get('node_type') == 'Name' and func.get('id') == method_name:
                        used = True
            for v in n.values():
                search_usage(v)
        elif isinstance(n, list):
            for item in n:
                search_usage(item)
    search_usage(parent)
    return not used
def check_bare_raise_context(node, context=None):
    """
    Returns True if a bare raise statement is found in the specified context ('finally' or 'except').
    """
    # Only process Raise nodes
    if not isinstance(node, dict) or node.get('node_type') != 'Raise':
        return False
    # Check if it's a bare raise (no exception specified)
    if node.get('exc') is not None:
        return False
    # Traverse parent chain to find context
    parent = node.get('__parent__', None)
    while parent:
        if context == 'finally' and parent.get('node_type') == 'Finally':
            return True
        if context == 'except' and parent.get('node_type') == 'ExceptHandler':
            return True
        parent = parent.get('__parent__', None)
    # For 'except' context, bare raise outside except block is a violation
    if context == 'except':
        return False
    return False
# Custom function for detecting hardcoded AWS region in boto3 client calls
def check_hardcoded_aws_region(node):
    """
    Returns True if a boto3.client call contains a hardcoded AWS region value.
    """
    if not isinstance(node, dict) or node.get('node_type') != 'Call':
        return False
    func = node.get('func', {})
    # Check for boto3.client call
    if func.get('node_type') == 'Attribute' and func.get('attr') == 'client':
        value = func.get('value', {})
        if value.get('node_type') == 'Name' and value.get('id') == 'boto3':
            # Check for region_name keyword argument
            for kw in node.get('keywords', []):
                if kw.get('arg') == 'region_name':
                    region_value = kw.get('value', {})
                    if region_value.get('node_type') == 'Constant':
                        region = str(region_value.get('value', ''))
                        # Match AWS region pattern
                        if re.match(r'^(us|eu|ap|sa|ca|me|af)-(north|south|east|west|central|northeast|southeast|southwest|northwest|central)-[0-9]+$', region):
                            return True
    return False
# Custom function for unnecessary equality checks
def is_unnecessary_equality_check(node):
    """
    Detects chained equality comparisons like: x == 1 or x == 2 or x == 3
    Returns True if such a pattern is found.
    """
    if not isinstance(node, dict):
        return False
    # Check for BoolOp (or) with multiple Compare nodes
    if node.get('node_type') == 'BoolOp' and node.get('op', {}).get('node_type') == 'Or':
        left_names = set()
        values = node.get('values', [])
        for value in values:
            if isinstance(value, dict) and value.get('node_type') == 'Compare':
                ops = value.get('ops', [])
                if ops and ops[0].get('node_type') == 'Eq':
                    left = value.get('left', {})
                    if left.get('node_type') == 'Name':
                        left_names.add(left.get('id'))
        if len(left_names) == 1 and len(values) > 1:
            print('[DEBUG][is_unnecessary_equality_check] Triggered on node:', node)
            return True
    return False

# Custom function: simple cognitive complexity heuristic
def cognitive_complexity_check_impl(node, ast_root=None):
    """
    Heuristic for cognitive complexity: return True for FunctionDef nodes
    whose top-level body contains more than 5 statements. This is a
    conservative approximation used by the metadata-driven rule.
    """
    # Expect the node as a dict produced by ast_to_dict_with_parent
    if not isinstance(node, dict) or node.get('node_type') != 'FunctionDef':
        return False
    print(f"[DEBUG][cognitive_complexity_check_impl] Called for node: {node.get('node_type')} at line {node.get('lineno')}")
    body = node.get('body', [])
    if not isinstance(body, list):
        return False
    # Count only top-level statements (ignore nested defs/classes)
    stmt_count = 0
    for stmt in body:
        if isinstance(stmt, dict):
            # Skip nested FunctionDef or ClassDef from counting
            if stmt.get('node_type') in ('FunctionDef', 'ClassDef'):
                continue
            stmt_count += 1
        else:
            # Non-dict entries (unlikely) still count
            stmt_count += 1
    # Threshold matches metadata heuristic (>5 statements)
    return stmt_count > 5
# Custom function: Detect Unicode grapheme clusters inside regex character classes
def check_unicode_grapheme_clusters_in_regex(node):
    """
    Returns True if a regex string contains a character class with Unicode grapheme cluster range (U+0300–U+036F).
    Example: pattern = r'[̀-ͯ]+'
    """
    # Only check assignment nodes
    if not isinstance(node, dict) or node.get('node_type') != 'Assign':
        return False
    value_node = node.get('value', {})
    if not isinstance(value_node, dict):
        return False
    # Look for Constant node with a string value
    if value_node.get('node_type') == 'Constant':
        pattern = value_node.get('value', '')
        # Match character class with Unicode grapheme cluster range
        # U+0300 = \u0300, U+036F = \u036F
        import re
        if isinstance(pattern, str) and re.search(r'\[.*?\u0300-\u036F.*?\]', pattern):
            return True
        # Also match literal combining marks: [̀-ͯ]
        if isinstance(pattern, str) and re.search(r'\[[̀-ͯ]+\]', pattern):
            return True
    return False
def check_unencrypted_rds_usage(node):
    """
    Custom logic for rule: using_unencrypted_rds_db_resources_is_securitysensitive
    Flags calls to boto3.client('rds').describe_db_instances()
    """
    # print('[DEBUG] Called check_unencrypted_rds_usage')
    # print('[DEBUG] Node type:', node.get('node_type'))
    # print('[DEBUG] Node structure:', node)
    if node.get('node_type') == 'Call':
        func = node.get('func', {})
    # print('[DEBUG] func:', func)
        # Check for describe_db_instances call
        if func.get('node_type') == 'Attribute' and func.get('attr') == 'describe_db_instances':
            value = func.get('value', {})
            # print('[DEBUG] value:', value)
            # Check for boto3.client('rds')
            if value.get('node_type') == 'Call':
                inner_func = value.get('func', {})
                # print('[DEBUG] inner_func:', inner_func)
                if inner_func.get('node_type') == 'Attribute' and inner_func.get('attr') == 'client':
                    args = value.get('args', [])
                    # print('[DEBUG] args:', args)
                    for arg in args:
                        # print('[DEBUG] arg:', arg)
                        if arg.get('node_type') == 'Constant' and arg.get('value') == 'rds':
                            # print('[DEBUG] MATCH FOUND!')
                            return {
                                'message': 'Unencrypted RDS resource found',
                                'line': node.get('lineno', 1)
                            }
    return False
def async_functions_should_use_async_features(node):
    # Only process async functions
    if node.get("node_type") != "AsyncFunctionDef":
        return False
    def contains_async_feature(n):
        if isinstance(n, dict):
            # Check for 'Await' or 'AsyncWith' node types
            if n.get("node_type") in ["Await", "AsyncWith"]:
                return True
            for v in n.values():
                if contains_async_feature(v):
                    return True
        elif isinstance(n, list):
            for item in n:
                if contains_async_feature(item):
                    return True
        return False
    return not contains_async_feature(node.get("body", []))
def async_forbidden_subprocess_call(node):
    # Recursively check for forbidden subprocess calls in async function body
    forbidden_subprocess_calls = ["run", "call", "Popen"]
    def contains_forbidden_call(n):
        if isinstance(n, dict):
            if n.get('node_type') == 'Call':
                func = n.get('func', {})
                if func.get('node_type') == 'Attribute':
                    if func.get('value', {}).get('id') == 'subprocess' and func.get('attr') in forbidden_subprocess_calls:
                        return True
            for v in n.values():
                if contains_forbidden_call(v):
                    return True
        elif isinstance(n, list):
            for item in n:
                if contains_forbidden_call(item):
                    return True
        return False
    return contains_forbidden_call(node.get('body', []))
# ...existing code...
def cancellation_scope_contains_checkpoint(node, ast_root=None):
    """
    Returns True if an AsyncWith node with a cancel_token context contains a checkpoint (either in items or as 'await checkpoint()' in the body).
    """
    if not isinstance(node, dict) or node.get('node_type') != 'AsyncWith':
        return False
    items = node.get('items', [])
    has_cancel_token = False
    has_checkpoint_item = False
    for item in items:
        context_expr = item.get('context_expr', {})
        if isinstance(context_expr, dict):
            if context_expr.get('id') == 'cancel_token':
                has_cancel_token = True
            if context_expr.get('id') == 'checkpoint':
                has_checkpoint_item = True
    if not has_cancel_token:
        return False
    if has_checkpoint_item:
        return False  # Compliant, no finding
    # Scan body for 'await checkpoint()'
    def body_has_checkpoint(n):
        if isinstance(n, dict):
            if n.get('node_type') == 'Expr':
                value = n.get('value', {})
                if value.get('node_type') == 'Await':
                    awaited = value.get('value', {})
                    # Check for checkpoint.wait() or checkpoint()
                    if awaited.get('node_type') == 'Call':
                        func = awaited.get('func', {})
                        if func.get('node_type') == 'Attribute' and func.get('value', {}).get('id') == 'checkpoint':
                            return True
                        if func.get('node_type') == 'Name' and func.get('id') == 'checkpoint':
                            return True
            for v in n.values():
                if body_has_checkpoint(v):
                    return True
        elif isinstance(n, list):
            for item in n:
                if body_has_checkpoint(item):
                    return True
        return False
    if body_has_checkpoint(node.get('body', [])):
        return False  # Compliant, no finding
    return True  # Noncompliant, checkpoint missing
import re
def check_admin_services_access_restricted_to_specific_ip_addresses(node):
    """
    Custom logic for rule: administration_services_access_should_be_restricted_to_specific_ip_addresses
    Checks for unrestricted admin service access (e.g., 0.0.0.0/0, *, any) in cidr_blocks.
    """
    def extract_cidr_blocks(obj):
        cidrs = []
        if isinstance(obj, dict):
            if obj.get('node_type') == 'Dict':
                keys = obj.get('keys', [])
                values = obj.get('values', [])
                for key, value in zip(keys, values):
                    if isinstance(key, dict) and key.get('value') == 'cidr_blocks':
                        if value.get('node_type') == 'List':
                            for elt in value.get('elts', []):
                                if elt.get('node_type') == 'Constant':
                                    cidrs.append(str(elt.get('value', '')))
            elif obj.get('node_type') == 'Assign':
                value = obj.get('value', {})
                cidrs.extend(extract_cidr_blocks(value))
            for key in ['value', 'values']:
                if key in obj:
                    value = obj[key]
                    if isinstance(value, (dict, list)):
                        cidrs.extend(extract_cidr_blocks(value))
        elif isinstance(obj, list):
            for item in obj:
                cidrs.extend(extract_cidr_blocks(item))
        return cidrs
    if node.get('node_type') not in ['Assign', 'Call']:
        return False
    cidr_blocks = extract_cidr_blocks(node)
    if not cidr_blocks:
        return False
    node_id = None
    if node.get('node_type') == 'Assign':
        targets = node.get('targets', [])
        if targets and isinstance(targets[0], dict):
            node_id = targets[0].get('id', '')
    if node_id and not re.search(r'(?i)(admin|administrator|manage|control|configure)', node_id):
        return False
    pattern = re.compile(r"(?i)(0\.0\.0\.0/0|\*|any)")
    return any(pattern.search(cidr) for cidr in cidr_blocks)
# ...existing code...
def check_subclass_parent_in_except(node):
    """
    Check for subclass and parent class in the same except statement.
    """
    if node.get('node_type') != 'ExceptHandler':
        return False
    exc_type = node.get('type', {})
    if isinstance(exc_type, dict) and exc_type.get('node_type') == 'Tuple':
        elts = exc_type.get('elts', [])
        exception_names = []
        for elt in elts:
            if isinstance(elt, dict) and elt.get('node_type') == 'Name':
                exception_names.append(elt.get('id', ''))
        # Build a map of class inheritance from the parent AST node
        # Traverse up to find the root module/class definitions
        parent = node.get('__parent__', None)
        while parent and parent.get('__parent__'):
            parent = parent.get('__parent__')
        class_bases = {}
        if parent and 'body' in parent:
            for item in parent['body']:
                if isinstance(item, dict) and item.get('node_type') == 'ClassDef':
                    class_name = item.get('name', '')
                    bases = [base.get('id', '') for base in item.get('bases', []) if isinstance(base, dict)]
                    class_bases[class_name] = bases
        # Check for subclass-parent pairs in the except tuple
        for i, name1 in enumerate(exception_names):
            for j, name2 in enumerate(exception_names):
                if i != j:
                    # name1 is subclass of name2
                    if name1 in class_bases and name2 in class_bases[name1]:
                        return True
                    # name2 is subclass of name1
                    if name2 in class_bases and name1 in class_bases[name2]:
                        return True
        # Fallback: if 'Exception' is present and another type, still trigger
        if 'Exception' in exception_names and len(exception_names) > 1:
            return True
    return False
# ...existing code...
def is_weak_password(password):
    """Check if a password is considered weak"""
    if not isinstance(password, str) or len(password) < 3:
        return False

def check_union_type_expressions_preferred(node):
    """
    Custom logic for rule: union_type_expressions_should_be_preferred_over_typingunion_in_type_hints
    Flags usage of typing.Union in type hints, recommends using X | Y syntax.
    """
    findings = []
    # Check function arguments
    if node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
        args = node.get('args', {}).get('args', [])
        for arg in args:
            annotation = arg.get('annotation', {})
            if annotation.get('node_type') == 'Subscript':
                value = annotation.get('value', {})
                if value.get('node_type') == 'Name' and value.get('id') == 'Union':
                    findings.append({
                        'message': "Use 'X | Y' union type expressions instead of 'typing.Union[X, Y]' in type hints.",
                        'line': arg.get('lineno', node.get('lineno', 1))
                    })
    # Check variable annotations
    if node.get('node_type') == 'AnnAssign':
        annotation = node.get('annotation', {})
        if annotation.get('node_type') == 'Subscript':
            value = annotation.get('value', {})
            if value.get('node_type') == 'Name' and value.get('id') == 'Union':
                findings.append({
                    'message': "Use 'X | Y' union type expressions instead of 'typing.Union[X, Y]' in type hints.",
                    'line': node.get('lineno', 1)
                })
    return findings if findings else False
    password_lower = password.lower()
    weak_passwords = [
        '123456', 'password', 'admin', 'root', 'user', 'guest', 'test',
        'admin123', 'password123', 'root123', 'user123', 'test123',
        'qwerty', 'abc123', '111111', '000000', 'letmein', 'welcome',
        'monkey', 'dragon', 'master', 'secret', 'login', 'pass',
        '12345678', '1234567890', 'password1', 'admin1', 'secret123'
    ]
    if password_lower in weak_passwords:
        return True
    if password.isdigit() and len(password) <= 8:
        return True
    if len(password) <= 6:
        return True
    if all(ord(password[i]) == ord(password[0]) + i for i in range(len(password))):
        return True
    return False
# ...existing code...
def check_database_password_security(node):
    """
    Check for insecure database passwords in connection calls.
    """
    if node.get('node_type') == 'Call':
        func = node.get('func', {})
        if isinstance(func, dict):
            # Check for database connection functions
            func_name = func.get('attr', '') or func.get('id', '')
            if any(db_word in func_name.lower() for db_word in ['connect', 'engine', 'session']):
                # Check password parameter
                keywords = node.get('keywords', [])
                for kw in keywords:
                    if isinstance(kw, dict):
                        arg_name = kw.get('arg', '').lower()
                        if arg_name in ['password', 'pwd', 'passwd']:
                            value = kw.get('value', {})
                            if isinstance(value, dict) and value.get('node_type') in ['Constant', 'Str']:
                                password = str(value.get('value', ''))
                                if is_weak_password(password):
                                    return True
    elif node.get('node_type') == 'Assign':
        # Check database URL assignments
        targets = node.get('targets', [])
        for target in targets:
            if isinstance(target, dict) and target.get('node_type') == 'Name':
                var_name = target.get('id', '').lower()
                if any(word in var_name for word in ['db_url', 'database_url', 'connection_string']):
                    value = node.get('value', {})
                    if isinstance(value, dict) and value.get('node_type') in ['Constant', 'Str']:
                        url = str(value.get('value', ''))
                        # Check for weak passwords in database URLs
                        if ':' in url and '@' in url:
                            try:
                                # Extract password from URL like postgresql://user:password@host/db
                                password_part = url.split('://')[1].split('@')[0]
                                if ':' in password_part:
                                    password = password_part.split(':')[1]
                                    if is_weak_password(password):
                                        return True
                            except:
                                pass
    return False
# ...existing code...
def check_test_skip_without_reason(node):
    """
    Check for pytest.mark.skip without a reason parameter.
    """
    if node.get('node_type') != 'FunctionDef':
        return False
    decorators = node.get('decorator_list', [])
    for decorator in decorators:
        if isinstance(decorator, dict):
            if decorator.get('node_type') == 'Attribute':
                # Handle @pytest.mark.skip
                attr = decorator.get('attr', '')
                if attr == 'skip':
                    value = decorator.get('value', {})
                    if isinstance(value, dict):
                        if value.get('node_type') == 'Attribute':
                            sub_attr = value.get('attr', '')
                            sub_value = value.get('value', {})
                            if (sub_attr == 'mark' and isinstance(sub_value, dict) and 
                                sub_value.get('node_type') == 'Name' and 
                                sub_value.get('id') == 'pytest'):
                                return True
            elif decorator.get('node_type') == 'Call':
                # Handle @pytest.mark.skip() - check if reason is provided
                func = decorator.get('func', {})
                if isinstance(func, dict):
                    if func.get('node_type') == 'Attribute' and func.get('attr') == 'skip':
                        # Check if there are keyword arguments with 'reason'
                        keywords = decorator.get('keywords', [])
                        for kw in keywords:
                            if isinstance(kw, dict) and kw.get('arg') == 'reason':
                                return False  # Reason is provided
                        return True  # No reason provided
    return False
# Auto-generated function for metadata creation
# Importing check_test_skip_without_reason from logic_implementationsv2
from prework.logic_implementationsv2 import check_test_skip_without_reason
def check_field_class_name_conflict(node):
    """
    Check if a field name duplicates its containing class name.
    """
    if node.get('node_type') != 'ClassDef':
        return False
    class_name = node.get('name', '')
    if not class_name:
        return False
    # Check class body for field assignments and instance attribute assignments
    body = node.get('body', [])
    for stmt in body:
        if isinstance(stmt, dict):
            # Class-level assignments
            if stmt.get('node_type') == 'Assign':
                targets = stmt.get('targets', [])
                for target in targets:
                    if isinstance(target, dict) and target.get('node_type') == 'Name':
                        field_name = target.get('id', '')
                        if field_name.lower() == class_name.lower():
                            return True
            # Instance attribute assignments inside methods
            if stmt.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
                method_body = stmt.get('body', [])
                for inner_stmt in method_body:
                    if isinstance(inner_stmt, dict) and inner_stmt.get('node_type') == 'Assign':
                        targets = inner_stmt.get('targets', [])
                        for target in targets:
                            if (isinstance(target, dict) and target.get('node_type') == 'Attribute' and
                                target.get('value', {}).get('node_type') == 'Name' and
                                target.get('value', {}).get('id') == 'self'):
                                attr_name = target.get('attr', '')
                                if attr_name.lower() == class_name.lower():
                                    return True
    return False
# Auto-generated function for metadata creation
# Detects regex patterns containing two or more consecutive spaces
import ast
import re

def field_should_not_duplicate_class_name(node):
    """Detects when a field name duplicates its containing class name."""
    if node.get('node_type') != 'ClassDef':
        return False
        
    class_name = node.get('name', '')
    if not class_name:
        return False
        
    # Check assignments in the class body
    for stmt in node.get('body', []):
        if isinstance(stmt, dict):
            # Class-level assignments
            if stmt.get('node_type') == 'Assign':
                for target in stmt.get('targets', []):
                    if isinstance(target, dict):
                        if target.get('node_type') == 'Name' and target.get('id').lower() == class_name.lower():
                            return True
                        elif target.get('node_type') == 'Attribute' and target.get('attr').lower() == class_name.lower():
                            return True
            # Instance attribute assignments inside methods
            if stmt.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
                method_body = stmt.get('body', [])
                for inner_stmt in method_body:
                    if isinstance(inner_stmt, dict) and inner_stmt.get('node_type') == 'Assign':
                        for target in inner_stmt.get('targets', []):
                            if (isinstance(target, dict) and target.get('node_type') == 'Attribute' and
                                target.get('value', {}).get('node_type') == 'Name' and
                                target.get('value', {}).get('id') == 'self' and
                                target.get('attr').lower() == class_name.lower()):
                                return True
                            
    return False

def regular_expressions_should_not_contain_multiple_spaces(node):
    """Detects regex patterns containing two or more consecutive spaces."""
    if isinstance(node, ast.Call):
        for arg in node.args:
            if isinstance(arg, ast.Str):
                pattern = arg.s
                if re.search(r" {2,}", pattern):
                    return True
    return False

# Detects if/elif/else chains with repeated conditions

def related_ifelse_if_statements_should_not_have_the_same_condition(node):
    """Detects if/elif/else chains with repeated conditions."""
    if isinstance(node, ast.If):
        conditions = set()
        current = node
        while isinstance(current, ast.If):
            cond_src = ast.dump(current.test)
            if cond_src in conditions:
                return True
            conditions.add(cond_src)
            if current.orelse and isinstance(current.orelse[0], ast.If):
                current = current.orelse[0]
            else:
                break
    return False

# Detects regex patterns where a reluctant quantifier (e.g., *?, +?, ??) is followed by an expression that can match the empty string

def reluctant_quantifiers_in_regular_expressions_should_be_followed_by_an_expression_that_cant_match_the_empty_string(node):
    """Detects regex patterns where a reluctant quantifier (e.g., *?, +?, ??) is followed by an expression that can match the empty string."""
    if isinstance(node, ast.Call):
        for arg in node.args:
            if isinstance(arg, ast.Str):
                pattern = arg.s
                # Find reluctant quantifiers
                for match in re.finditer(r'(\*\?|\+\?|\?\?)', pattern):
                    idx = match.end()
                    # Check if the next part can match empty string (e.g., .*, (?:), [])
                    next_part = pattern[idx:idx+4]
                    if re.match(r'(\.|\(\?:\)|\[\])', next_part):
                        return True
    return False
# Auto-generated function for metadata creation
def regular_expressions_should_be_syntactically_valid(node):
    """Detects regex strings containing contradictory lookahead assertions."""
    if isinstance(node, ast.Call):
        for arg in node.args:
            if isinstance(arg, ast.Str):
                regex = arg.s
                if '(?=' in regex and '(?!' in regex:
                    return True
    return False

# Auto-generated function for metadata creation
def regular_expressions_should_not_be_too_complicated(node):
    """Detects regex strings containing contradictory lookahead assertions."""
    if isinstance(node, ast.Call):
        for arg in node.args:
            if isinstance(arg, ast.Str):
                regex = arg.s
                if '(?=' in regex and '(?!' in regex:
                    return True
    return False

# Auto-generated function for metadata creation
def regular_expressions_should_not_contain_empty_groups(node):
    """Detects regex strings containing contradictory lookahead assertions."""
    if isinstance(node, ast.Call):
        for arg in node.args:
            if isinstance(arg, ast.Str):
                regex = arg.s
                if '(?=' in regex and '(?!' in regex:
                    return True
    return False
# Auto-generated function for metadata creation
def passing_a_reversed_iterable_to_set_sorted_or_reversed_should_be_avoided(node):
    """Detects if the expression value is a generator expression."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.GeneratorExp):
        return True
    return False

# Auto-generated function for metadata creation
def password_hashing_functions_should_use_an_unpredictable_salt(node):
    """Detects if the expression value is a generator expression."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.GeneratorExp):
        return True
    return False

# Auto-generated function for metadata creation
def passwords_should_not_be_stored_in_plaintext_or_with_a_fast_hashing_algorithm(node):
    """Detects if the expression value is a generator expression."""
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.GeneratorExp):
        return True
    return False
# Auto-generated function for metadata creation
def npnonzero_should_be_preferred_over_npwhere_when_only_the_condition_parameter_is_set(node):
    """Detects use of np.where with only the condition parameter set."""
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == 'where':
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'np':
                # Only one positional argument and no keywords
                if len(node.args) == 1 and not node.keywords:
                    return True
    return False

# Auto-generated function for metadata creation
def nulltrue_should_not_be_used_on_stringbased_fields_in_django_models(node):
    """Detects use of null=True on string-based fields in Django models."""
    string_fields = {'CharField', 'TextField', 'SlugField', 'EmailField', 'URLField'}
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in string_fields:
            for kw in node.keywords:
                if kw.arg == 'null' and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    return True
    return False

# Auto-generated function for metadata creation
def numpy_weekmask_should_have_a_valid_value(node):
    """Detects invalid weekmask values in numpy usage."""
    valid_weekmask = {'1111111', '0000000', '1010101', '0101010'}  # Example valid values
    if isinstance(node, ast.Call):
        for kw in node.keywords:
            if kw.arg == 'weekmask' and isinstance(kw.value, ast.Str):
                if kw.value.s not in valid_weekmask:
                    return True
    return False
# Auto-generated function for metadata creation
def noncapturing_groups_without_quantifier_should_not_be_used(node):
    """Detects old-style class or function definitions."""
    return isinstance(node, (ast.ClassDef, ast.FunctionDef))

# Auto-generated function for metadata creation
def nonempty_statements_should_change_control_flow_or_have_at_least_one_sideeffect(node):
    """Detects old-style class or function definitions."""
    return isinstance(node, (ast.ClassDef, ast.FunctionDef))

# Auto-generated function for metadata creation
def nonexistent_operators_like_should_not_be_used(node):
    """Detects old-style class or function definitions."""
    return isinstance(node, (ast.ClassDef, ast.FunctionDef))
# Auto-generated function for metadata creation
def hardcoded_passwords_are_securitysensitive(node):
    """Detects hardcoded passwords in assignments or function arguments."""
    password_keywords = {'password', 'passwd', 'pwd', 'pass'}
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and any(k in target.id.lower() for k in password_keywords):
                if isinstance(node.value, ast.Str):
                    return True
    if isinstance(node, ast.Call):
        for kw in getattr(node, 'keywords', []):
            if any(k in kw.arg.lower() for k in password_keywords) and isinstance(kw.value, ast.Str):
                return True
    return False

# Auto-generated function for metadata creation
def hardcoded_secrets_are_securitysensitive(node):
    """Detects hardcoded secrets in assignments or function arguments."""
    secret_keywords = {'secret', 'token', 'key', 'api_key', 'access_key', 'private_key'}
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and any(k in target.id.lower() for k in secret_keywords):
                if isinstance(node.value, ast.Str):
                    return True
    if isinstance(node, ast.Call):
        for kw in getattr(node, 'keywords', []):
            if any(k in kw.arg.lower() for k in secret_keywords) and isinstance(kw.value, ast.Str):
                return True
    return False

# Auto-generated function for metadata creation
def having_a_permissive_crossorigin_resource_sharing_policy_is_securitysensitive(node):
    """Detects permissive CORS policy (wildcard origins)."""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and 'cors' in target.id.lower():
                if isinstance(node.value, ast.Str) and node.value.s == '*':
                    return True
            if isinstance(target, ast.Name) and 'origin' in target.id.lower():
                if isinstance(node.value, ast.Str) and node.value.s == '*':
                    return True
    if isinstance(node, ast.Call):
        for kw in getattr(node, 'keywords', []):
            if kw.arg and ('origin' in kw.arg.lower() or 'cors' in kw.arg.lower()):
                if isinstance(kw.value, ast.Str) and kw.value.s == '*':
                    return True
    return False
# Auto-generated function for metadata creation
def exception_and_baseexception_should_not_be_raised(node):
    """Detects if a raise statement raises Exception or BaseException."""
    if isinstance(node, ast.Raise):
        exc = node.exc
        # exc can be ast.Name, ast.Call, ast.Attribute, etc.
        if isinstance(exc, ast.Name) and exc.id in {'Exception', 'BaseException'}:
            return True
        if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id in {'Exception', 'BaseException'}:
            return True
    return False
# Auto-generated function for metadata creation
def except_clauses_should_do_more_than_raise_the_same_issue(node):
    """Detects except clauses that only re-raise the exception."""
    if isinstance(node, ast.Try):
        for handler in node.handlers:
            # If the except block only contains a single raise statement
            if (len(handler.body) == 1 and isinstance(handler.body[0], ast.Raise)):
                return True
    return False
# Auto-generated function for metadata creation
def events_should_be_used_instead_of_sleep_in_asynchronous_loops(node):
    """Detects if an async function uses sleep in a loop instead of event synchronization."""
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.AsyncFor)):
                has_sleep = False
                has_event = False
                for loop_body_item in child.body:
                    # Check for sleep calls
                    if isinstance(loop_body_item, ast.Expr) and isinstance(loop_body_item.value, ast.Call):
                        func = loop_body_item.value.func
                        if (isinstance(func, ast.Attribute) and func.attr == 'sleep') or (isinstance(func, ast.Name) and func.id == 'sleep'):
                            has_sleep = True
                    # Check for event usage
                    if isinstance(loop_body_item, ast.Assign):
                        if isinstance(loop_body_item.value, ast.Call):
                            func = loop_body_item.value.func
                            if (isinstance(func, ast.Attribute) and 'Event' in func.attr) or (isinstance(func, ast.Name) and 'Event' in func.id):
                                has_event = True
                if has_sleep and not has_event:
                    return True
    return False
# Auto-generated function for metadata creation
def asyncio_tasks_should_be_saved_to_prevent_premature_garbage_collection(node):
    """Detects if an async function creates asyncio tasks without saving them to a variable."""
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            # Look for calls to asyncio.create_task, loop.create_task, or asyncio.ensure_future
            if isinstance(child, ast.Call):
                called = None
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == 'create_task' or child.func.attr == 'ensure_future':
                        called = child.func.attr
                elif isinstance(child.func, ast.Name):
                    if child.func.id == 'ensure_future':
                        called = child.func.id
                # If a task is created, check if it's assigned to a variable
                if called:
                    parent = getattr(child, 'parent', None)
                    if not (parent and isinstance(parent, ast.Assign) and child in parent.value.elts if hasattr(parent.value, 'elts') else parent.value == child):
                        return True
    return False
# Auto-generated function for metadata creation
def asynchronous_functions_should_not_accept_timeout_parameters(node):
    """Detects if an async function accepts a 'timeout' parameter."""
    if isinstance(node, ast.AsyncFunctionDef):
        for arg in node.args.args:
            if arg.arg == 'timeout':
                return True
        # Also check for keyword-only arguments
        for arg in getattr(node.args, 'kwonlyargs', []):
            if arg.arg == 'timeout':
                return True
    return False
# Auto-generated function for metadata creation
def async_with_should_be_used_for_asynchronous_resource_management(node):
    """Detects use of synchronous 'with' inside an async function (should use 'async with')."""
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.With):
                # Synchronous 'with' found in async function
                return True
    return False
# Auto-generated function for metadata creation
def is_async_function_with_sync_file_operations(node):
    """Detects if an async function contains synchronous file operations like open(), read(), write(), close()."""
    file_methods = {'read', 'write', 'close', 'flush', 'seek', 'tell', 'truncate'}
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            # Detect open()
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name) and child.func.id == 'open':
                    return True
                # Detect file method calls (e.g., f.read())
                if isinstance(child.func, ast.Attribute) and child.func.attr in file_methods:
                    return True
    return False

# Stub for Issue class (replace with actual implementation if available)
class Issue(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)


# Auto-generated function for metadata creation
def test_skip_reason(node):
    """Auto-generated STUB for a_reason_should_be_provided_when_skipping_a_test. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_mixed_http_methods(node):
    """Auto-generated STUB for allowing_both_safe_and_unsafe_http_methods_is_securitysensitive. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_unrestricted_outbound_communication(node):
    """Auto-generated STUB for allowing_unrestricted_outbound_communications_is_securitysensitive. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_async_function_with_input_call(node):
    """Detects if an async function contains an input() call."""
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Check if the function called is 'input'
                if (isinstance(child.func, ast.Name) and child.func.id == 'input'):
                    return True
    return False


# Auto-generated function for metadata creation
def check_async_function_for_sync_http_calls(node):
    """Detects if an async function contains synchronous HTTP client calls like requests.get/post, http.client.HTTPConnection, etc."""
    sync_http_calls = {
        ('requests', {'get', 'post', 'put', 'delete', 'head', 'options', 'patch'}),
        ('http.client', {'HTTPConnection', 'HTTPSConnection'})
    }
    if isinstance(node, ast.AsyncFunctionDef):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # requests.get/post/put/etc
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == 'requests' and child.func.attr in sync_http_calls[0][1]:
                        return True
                # http.client.HTTPConnection/HTTPSConnection
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id == 'http' and child.func.attr == 'client':
                        if child.args and isinstance(child.args[0], ast.Str) and child.args[0].s in sync_http_calls[1][1]:
                            return True
                # direct instantiation: http.client.HTTPConnection(...)
                if isinstance(child.func, ast.Name) and child.func.id in sync_http_calls[1][1]:
                    return True
    return False


# Auto-generated function for metadata creation
def is_os_call_in_async_function(node):
    """Auto-generated STUB for async_functions_should_not_contain_synchronous_os_calls. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation

def is_unreachable_code(node):
    if node.get('node_type') != 'FunctionDef':
        return False

    # Skip main functions or test functions as they may be called externally
    func_name = node.get('name')
    if func_name in ['main'] or func_name.startswith('test_'):
        return False

    # Walk up parent chain to find module node
    root = node
    while root.get('node_type') != 'Module' and root.get('__parent__') is not None:
        root = root.get('__parent__')
    if root.get('node_type') != 'Module':
        return False

    # Look for any assignments or calls using this function
    found_usage = False
    nodes_to_check = [root]  # Start with root node
    checked_nodes = set()  # Keep track of nodes we've seen to avoid loops

    while nodes_to_check and not found_usage:
        current = nodes_to_check.pop(0)
        if id(current) in checked_nodes:  # Skip if already checked
            continue
        checked_nodes.add(id(current))

        if isinstance(current, dict):
            if current.get('node_type') in ['Call', 'Name']:
                # Check direct calls
                if current.get('node_type') == 'Call':
                    func = current.get('func', {})
                    if isinstance(func, dict) and func.get('node_type') == 'Name' and func.get('id') == func_name:
                        found_usage = True
                        break
                # Check assignments and other references
                elif current.get('node_type') == 'Name' and current.get('id') == func_name:
                    # If it's referenced anywhere besides its own definition, count it as used
                    if current != node:
                        found_usage = True
                        break
            
            # Add children to check
            for value in current.values():
                if isinstance(value, list):
                    nodes_to_check.extend(item for item in value if isinstance(item, dict))
                elif isinstance(value, dict):
                    nodes_to_check.append(value)

    return not found_usage


# Auto-generated function for metadata creation
def all_except_blocks_should_be_able_to_catch_exceptions_check(node):
    # Only check function definitions
    if node.get('node_type') != 'FunctionDef':
        return False

    # Check for @contextmanager decorator
    decorators = node.get('decorator_list', [])
    for dec in decorators:
        # Handles both Name and Attribute nodes
        if dec.get('node_type') == 'Name' and dec.get('id') == 'contextmanager':
            return False
        if dec.get('node_type') == 'Attribute' and dec.get('attr') == 'contextmanager':
            return False

    # Check for try/except blocks in function body
    body = node.get('body', [])
    for stmt in body:
        if stmt.get('node_type') == 'Try':
            # If there is at least one except handler
            handlers = stmt.get('handlers', [])
            if any(h.get('node_type') == 'ExceptHandler' for h in handlers):
                return False

    # If neither contextmanager nor except block found, flag as violation
    return True


# Auto-generated function for metadata creation
def is_async_function(node):
    return node.type == 'FunctionDef' and node.name == 'lambda_handler' and node.body.value.value.async_value


# Auto-generated function for metadata creation
def cognitive_complexity_check(node):
    """Delegate stub to the implemented cognitive_complexity_check with ast_root=None."""
    try:
        return cognitive_complexity_check_impl(node, None)
    except Exception:
        # Fall back to older implementation if present
        try:
            return cognitive_complexity_check(node, None)
        except Exception:
            return False

def check_public_access_parameters(node):
    """Check if a function call contains public access parameters"""
    if node.get('node_type') != 'Call':
        return False

    # Check function keywords arguments
    for kw in node.get('keywords', []):
        # Look for access_control parameter
        if kw.get('arg') == 'access_control':
            value = kw.get('value', {})
            # Check for public access value
            if value.get('node_type') == 'Constant' and \
               value.get('value') == 'Public_Read':
                # print("[DEBUG] Found public access configuration:", value.get('value'))
                return True
    
    return False

def check_public_network_access(node):
    """Check for public network access in cloud resource configurations."""
    if node.get('node_type') != 'Call':
        return False

    # Get keywords arguments
    keywords = node.get('keywords', [])
    for kw in keywords:
        if kw.get('arg') == 'access_control':
            value = kw.get('value', {})
            if value.get('node_type') == 'Constant' and value.get('value') == 'Public_Read':
                return True
            
    return False

def allowing_public_s3_access_check(node):
    if node.get('node_type') != 'Call':
        return False
    
    # Check function name
    func = node.get('func', {})
    if func.get('node_type') == 'Attribute':
        method_name = func.get('attr')
        if method_name == 'put_bucket_acl':
            # Check ACL parameter
            keywords = node.get('keywords', [])
            for kw in keywords:
                if kw.get('arg') == 'ACL' and isinstance(kw.get('value'), dict):
                    value = kw.get('value', {}).get('value')
                    if value in ['public-read', 'public-read-write']:
                        return True
        elif method_name == 'put_bucket_policy':
            # Check Policy parameter for public access
            keywords = node.get('keywords', [])
            for kw in keywords:
                if kw.get('arg') == 'Policy' and isinstance(kw.get('value'), dict):
                    value = kw.get('value', {}).get('value')
                    if isinstance(value, str) and '*' in value and 'Principal' in value:
                        return True
    
    return False


# Auto-generated function for metadata creation
def cyclomatic_complexity_check(node):
    """Auto-generated STUB for cyclomatic_complexity_of_functions_should_not_be_too_high. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_dynamic_execution(node):
    """Auto-generated STUB for dynamically_executing_code_is_securitysensitive. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def check_encryption_secure_mode_padding(node):
    # TODO: implement detection logic
    return False


# Auto-generated function for metadata creation
def custom_check_except_clauses(node):
    """Auto-generated STUB for except_clauses_should_do_more_than_raise_the_same_issue. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def custom_check_function(node):
    # TODO: implement detection logic
    return False


# Auto-generated function for metadata creation

# Custom function to detect identical branches in conditionals
def check_identical_branches(node):
    """
    Returns True if two branches in an if/else conditional have identical implementations.
    """
    import ast
    if isinstance(node, ast.If):
        # Only check if there is an else branch
        if hasattr(node, 'orelse') and node.orelse:
            # Compare the AST dumps of both branches
            body_dump = [ast.dump(stmt) for stmt in node.body]
            orelse_dump = [ast.dump(stmt) for stmt in node.orelse]
            if body_dump == orelse_dump:
                return True
    return False


# Auto-generated function for metadata creation
def check_functions_return_statements(node):
    # Replace X with a sensible value, e.g., 0
    if isinstance(node, ast.FunctionDef) and len(getattr(node, 'body', [])) > 0:
        return any(isinstance(stmt, ast.Return) for stmt in node.body)
    return False


# Auto-generated function for metadata creation
def secret_detection(node):
    """Auto-generated STUB for hardcoded_secrets_are_securitysensitive. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_implicit_concatenation(node):
    # Check for implicit concatenation of bytes and strings
    for child in node.children:
        if isinstance(child, ast.Num):
            parent = getattr(node, 'parent', None)
            if parent and hasattr(parent, 'body') and isinstance(parent, ast.BinOp):
                if (isinstance(parent.left, ast.Str) or isinstance(parent.left, ast.Bytes) or
                    isinstance(parent.right, ast.Str) or isinstance(parent.right, ast.Bytes)):
                    return child.n in parent.body
    return False


# Auto-generated function for metadata creation
def check_issue_suppression_comment(node):
    if not node.get('value').startswith('# nocov erase') or not any(line.startswith(f'# nocov {key}') for key in ['start', 'ignore', 'end'] for line in node.get('value').split('\n')):
        return True


# Auto-generated function for metadata creation
def check_model_evaluation_or_training(node):
    """Auto-generated STUB for modeleval_or_modeltrain_should_be_called_after_loading_the_state_of_a_pytorch_model. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def python_parser_failure_check(node):
    """Auto-generated STUB for python_parser_failure. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def is_side_effect_in_tffunction(node):
    """Auto-generated STUB for python_side_effects_should_not_be_used_inside_a_tffunction. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def recursion_check(node):
    if isinstance(node, ast.FunctionDef) and getattr(node, 'name', None) == 'f':
        return any([
            any([isinstance(n, ast.FunctionDef) and getattr(n, 'name', None) == 'f' for n in getattr(node, 'body', [])])
        ])
    return False


def check_cloudwatch_namespace(node):
    """
    Custom logic for rule: aws_cloudwatch_metrics_namespace_should_not_begin_with_aws
    Checks if CloudWatch metric namespace starts with 'aws'
    """
    if node.get('node_type') != 'Call':
        return False

    # Check if this is a put_metric_data call
    func = node.get('func', {})
    if func.get('node_type') == 'Attribute' and func.get('attr') == 'put_metric_data':
        # Look for the Namespace parameter in keywords
        keywords = node.get('keywords', [])
        for kw in keywords:
            if kw.get('arg') == 'Namespace':
                value = kw.get('value', {})
                if value.get('node_type') == 'Constant':
                    namespace = value.get('value', '')
                    if isinstance(namespace, str) and namespace.startswith('aws'):
                        return {
                            'message': f"CloudWatch metric namespace '{namespace}' should not start with 'aws'",
                            'line': value.get('lineno', 1)
                        }
    return False


# Auto-generated function for metadata creation
def custom_check_repeated_empty_regex(node):
    """Auto-generated STUB for repeated_patterns_in_regular_expressions_should_not_match_the_empty_string. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False


# Auto-generated function for metadata creation
def check_server_hostnames_should_be_verified_during_ssltls_connections(node):
    # TODO: implement detection logic
    return False


# Auto-generated function for metadata creation
def custom_check_string_duplication(node):
    string_literals = set()
    seen = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.Str, ast.Bytes, ast.Constant)):
            value = getattr(child, 'nval', child.s)
            if value not in string_literals:
                string_literals.add(value)
                seen.add(id(child))
        if id(child) in seen:
            raise Issue(..., message='Duplicated string literal: {}'.format(value))


# Auto-generated function for metadata creation
def custom_check_type_aliases_without_type_statement(node):
    """Auto-generated STUB for type_aliases_should_be_declared_with_a_type_statement. Implement detection logic here."""
    # TODO: implement detection that returns True when vulnerability exists
    return False



# Auto-generated function for metadata creation
def is_unencrypted_efs_usage(node):
    if not any(isinstance(n, ast.Call) and n.func.id == 'create_filesystem' and 'encryption_by_default' not in n.keywords
           for n in ast.walk(node) if isinstance(n, (ast.Call, ast.Attribute))):
        return False
    return True


# Auto-generated function for metadata creation
def xml_signature_validation_check(node):
    # TODO: implement detection logic
    return False


# Auto-generated function for metadata creation
def custom_check_cancellation_exceptions_should_be_reraised_after_cleanup(node):
    # Only process Raise nodes
    if not isinstance(node, dict) or node.get('node_type') != 'Raise':
        return False
    # Check if exception being raised is CancelledError
    exc = node.get('exc')
    if isinstance(exc, dict) and exc.get('node_type') == 'Call' and exc.get('func', {}).get('id') == 'CancelledError':
        # Check if parent field is 'finalbody' (i.e., inside a finally block)
        parent_field = node.get('__parent_field__')
        if parent_field == 'finalbody':
            return True
    return False


# Auto-generated function for metadata creation
def check_hardcoded_passwords_are_securitysensitive(node):
    # TODO: implement detection logic
    return False


# Auto-generated function for metadata creation
def hardcoded_passwords_are_securitysensitive(node):
    """Detects hardcoded passwords in assignments or function arguments."""
    password_keywords = {'password', 'passwd', 'pwd', 'pass'}
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and any(k in target.id.lower() for k in password_keywords):
                if isinstance(node.value, ast.Str):
                    return True
    if isinstance(node, ast.Call):
        for kw in getattr(node, 'keywords', []):
            if any(k in kw.arg.lower() for k in password_keywords) and isinstance(kw.value, ast.Str):
                return True
    return False

# Auto-generated function for metadata creation
def weak_hashing_algorithm_check(node):
    weak_hashes = {'md5', 'sha1', 'whirlpool'}
    def walk(n):
        if isinstance(n, dict):
            if n.get('node_type') == 'Call':
                func = n.get('func', {})
                if func.get('node_type') == 'Attribute' and func.get('attr') in weak_hashes:
                    return True
            for v in n.values():
                if isinstance(v, (dict, list)):
                    if walk(v):
                        return True
        elif isinstance(n, list):
            for item in n:
                if walk(item):
                    return True
        return False
    return walk(node)

def check_iam_policy_least_privilege(node):
    """
    Custom logic for rule: aws_iam_policies_should_limit_the_scope_of_permissions_given
    Detects IAM policies with excessive permissions (wildcards in Action or Resource).
    """
    def is_excessive(actions, resources):
        if isinstance(actions, str):
            actions = [actions]
        if isinstance(resources, str):
            resources = [resources]
        for act in actions:
            if act == '*' or act.endswith(':*'):
                return True
        for res in resources:
            if res == '*' or res.endswith(':*') or res == 'arn:aws:s3:::*':
                return True
        return False

    # Look for dicts with 'Statement' key
    if node.get('node_type') == 'Dict' and 'keys' in node and 'values' in node:
        keys = node['keys']
        values = node['values']
        for k, v in zip(keys, values):
            if k.get('node_type') == 'Constant' and k.get('value') == 'Statement':
                # Statement value should be a list of dicts
                if v.get('node_type') == 'List':
                    for stmt in v.get('elts', []):
                        if stmt.get('node_type') == 'Dict' and 'keys' in stmt and 'values' in stmt:
                            stmt_keys = stmt['keys']
                            stmt_values = stmt['values']
                            action = None
                            resource = None
                            for sk, sv in zip(stmt_keys, stmt_values):
                                if sk.get('node_type') == 'Constant' and sk.get('value') == 'Action':
                                    if sv.get('node_type') == 'List':
                                        action = [elt.get('value') for elt in sv.get('elts', []) if elt.get('node_type') == 'Constant']
                                    elif sv.get('node_type') == 'Constant':
                                        action = [sv.get('value')]
                                if sk.get('node_type') == 'Constant' and sk.get('value') == 'Resource':
                                    if sv.get('node_type') == 'List':
                                        resource = [elt.get('value') for elt in sv.get('elts', []) if elt.get('node_type') == 'Constant']
                                    elif sv.get('node_type') == 'Constant':
                                        resource = [sv.get('value')]
                            if action and resource and is_excessive(action, resource):
                                return {
                                    'message': 'IAM policy has excessive permissions.',
                                    'line': node.get('lineno', 1)
                                }
    return False

def lambda_handler_compliance_check(node):
    """
    Checks AWS Lambda handler compliance for:
    1. Not being async
    2. Cleaning up temporary files
    3. Returning only JSON serializable values
    """
    findings = []
    # 1. Check for async Lambda handler
    if node.get('node_type') == 'AsyncFunctionDef' and node.get('name', '').startswith('lambda_handler'):
        findings.append({
            'message': 'Lambda handler should not be an async function.',
            'line': node.get('lineno', 1)
        })
    # 2. Check for cleanup of temporary files
    if node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef'] and node.get('name', '').startswith('lambda_handler'):
        body = node.get('body', [])
        for stmt in body:
            # Look for creation of temp files without delete=True
            if stmt.get('node_type') == 'Assign':
                value = stmt.get('value', {})
                if value.get('node_type') == 'Call' and value.get('func', {}).get('attr', '') == 'NamedTemporaryFile':
                    keywords = value.get('keywords', [])
                    for kw in keywords:
                        if kw.get('arg') == 'delete' and kw.get('value', {}).get('node_type') == 'Constant' and kw.get('value', {}).get('value') is False:
                            findings.append({
                                'message': 'Lambda function does not clean up temporary files in the tmp directory',
                                'line': stmt.get('lineno', 1)
                            })
            # Look for os.system("rm ... tmp*")
            if stmt.get('node_type') == 'Expr':
                value = stmt.get('value', {})
                if value.get('node_type') == 'Call' and value.get('func', {}).get('attr', '') == 'system':
                    args = value.get('args', [])
                    for arg in args:
                        if arg.get('node_type') == 'Constant' and 'rm' in str(arg.get('value', '')) and 'tmp' in str(arg.get('value', '')):
                            findings.append({
                                'message': 'Lambda function does not clean up temporary files in the tmp directory',
                                'line': stmt.get('lineno', 1)
                            })
    # 3. Check for JSON serializable return values
    if node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef'] and node.get('name', '').startswith('lambda_handler'):
        returns = node.get('returns', None)
        if returns and returns.get('node_type') == 'Name':
            if returns.get('id') in ['list', 'tuple', 'set']:
                findings.append({
                    'message': 'The handler should return JSON serializable values.',
                    'line': node.get('lineno', 1)
                })
    return findings if findings else False
