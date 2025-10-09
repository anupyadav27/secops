def check_admin_services_access_restricted_to_specific_ip_addresses(node):
    """
    Custom logic for rule: administration_services_access_should_be_restricted_to_specific_ip_addresses
    Checks for unrestricted admin service access (e.g., 0.0.0.0/0, *, any) in cidr_blocks.
    """
    import re

    def extract_cidr_blocks(obj):
        """Extract CIDR blocks from AST node structure"""
        cidrs = []
        if isinstance(obj, dict):
            if obj.get('node_type') == 'Dict':
                keys = obj.get('keys', [])
                values = obj.get('values', [])
                
                # Zip keys and values together
                for key, value in zip(keys, values):
                    if isinstance(key, dict) and key.get('value') == 'cidr_blocks':
                        if value.get('node_type') == 'List':
                            # Extract values from list elements
                            for elt in value.get('elts', []):
                                if elt.get('node_type') == 'Constant':
                                    cidrs.append(str(elt.get('value', '')))
            elif obj.get('node_type') == 'Assign':
                # For Assign nodes, check the value
                value = obj.get('value', {})
                cidrs.extend(extract_cidr_blocks(value))
            
            # Also check other fields that might contain nested dicts
            for key in ['value', 'values']:
                if key in obj:
                    value = obj[key]
                    if isinstance(value, (dict, list)):
                        cidrs.extend(extract_cidr_blocks(value))
        elif isinstance(obj, list):
            for item in obj:
                cidrs.extend(extract_cidr_blocks(item))
        return cidrs

    # Only process Assign or Call nodes
    if node.get('node_type') not in ['Assign', 'Call']:
        return False

    # Get CIDR blocks from this node
    cidr_blocks = extract_cidr_blocks(node)
    if not cidr_blocks:
        return False

    # Check for admin-related names
    node_id = None
    if node.get('node_type') == 'Assign':
        targets = node.get('targets', [])
        if targets and isinstance(targets[0], dict):
            node_id = targets[0].get('id', '')
    
    # If we have a node ID and it's not admin-related, skip
    if node_id and not re.search(r'(?i)(admin|administrator|manage|control|configure)', node_id):
        return False

    # Check for unrestricted access patterns
    pattern = re.compile(r"(?i)(0\.0\.0\.0/0|\*|any)")
    return any(pattern.search(cidr) for cidr in cidr_blocks)
"""
Custom logic implementations for Python scanner rules.
This module contains all custom functions used by rules that require complex logic
beyond simple regex patterns.
"""

import re
import ast


def check_field_class_name_conflict(node):
    """
    Check if a field name duplicates its containing class name.
    """
    if node.get('node_type') != 'ClassDef':
        return False
    
    class_name = node.get('name', '')
    if not class_name:
        return False
    
    # Check class body for field assignments
    body = node.get('body', [])
    for stmt in body:
        if isinstance(stmt, dict):
            if stmt.get('node_type') == 'Assign':
                targets = stmt.get('targets', [])
                for target in targets:
                    if isinstance(target, dict) and target.get('node_type') == 'Name':
                        field_name = target.get('id', '')
                        if field_name.lower() == class_name.lower():
                            return True
    return False


def check_hardcoded_credentials(node):
    """
    Check for hardcoded credentials in string constants.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', '')).lower()
        credential_patterns = [
            'password', 'passwd', 'pwd', 'secret', 'token', 'key',
            'api_key', 'auth', 'credential', 'private'
        ]
        return any(pattern in value for pattern in credential_patterns)
    return False


def check_insecure_random(node):
    """
    Check for usage of insecure random number generators.
    """
    if node.get('node_type') == 'Call':
        func = node.get('func', {})
        if isinstance(func, dict):
            if func.get('node_type') == 'Attribute':
                attr = func.get('attr', '')
                value = func.get('value', {})
                if isinstance(value, dict) and value.get('id') == 'random':
                    # random.random(), random.randint() etc. are insecure for crypto
                    return attr in ['random', 'randint', 'choice', 'shuffle']
    return False


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


def check_subclass_parent_in_except(node):
    """
    Check for subclass and parent class in the same except statement.
    """
    if node.get('node_type') != 'ExceptHandler':
        return False
    
    exc_type = node.get('type', {})
    if isinstance(exc_type, dict) and exc_type.get('node_type') == 'Tuple':
        # Multiple exception types in except clause
        elts = exc_type.get('elts', [])
        exception_names = []
        for elt in elts:
            if isinstance(elt, dict) and elt.get('node_type') == 'Name':
                exception_names.append(elt.get('id', ''))
        # Check for common parent-child relationships
        if 'Exception' in exception_names and len(exception_names) > 1:
            return True  # Exception is parent of most other exceptions
    return False


def check_hardcoded_admin_ip(node):
    """
    Check for hardcoded admin IP addresses that should be restricted.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', ''))
        # Check for admin/management IP patterns
        admin_patterns = [
            r'192\.168\.1\.1',  # Common router admin
            r'10\.0\.0\.1',     # Common gateway
            r'172\.16\.0\.1',   # Private network gateway
            r'0\.0\.0\.0'       # All interfaces
        ]
        for pattern in admin_patterns:
            if re.search(pattern, value):
                return True
    return False


def check_identical_branches(node):
    """
    Check for identical implementations in conditional branches.
    """
    if node.get('node_type') != 'If':
        return False
    
    body = node.get('body', [])
    orelse = node.get('orelse', [])
    
    if not body or not orelse:
        return False
    
    # Simple check: if both branches have the same single statement
    if len(body) == 1 and len(orelse) == 1:
        body_stmt = body[0]
        else_stmt = orelse[0]
        if isinstance(body_stmt, dict) and isinstance(else_stmt, dict):
            # Compare statement types and basic structure
            if (body_stmt.get('node_type') == else_stmt.get('node_type') and
                body_stmt.get('node_type') in ['Return', 'Assign', 'Expr']):
                return True
    return False


def check_unreachable_code(node):
    """
    Check for unreachable code after return statements.
    """
    if node.get('node_type') != 'FunctionDef':
        return False
    
    body = node.get('body', [])
    for i, stmt in enumerate(body):
        if isinstance(stmt, dict):
            if stmt.get('node_type') == 'Return':
                # Check if there are more statements after this return
                if i < len(body) - 1:
                    return True
    return False


def check_unsafe_http_methods(node):
    """
    Check for allowing both safe and unsafe HTTP methods.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', '')).upper()
        unsafe_methods = ['PUT', 'DELETE', 'PATCH']
        safe_methods = ['GET', 'HEAD', 'OPTIONS']
        
        # Check if value contains both safe and unsafe methods
        has_unsafe = any(method in value for method in unsafe_methods)
        has_safe = any(method in value for method in safe_methods)
        
        return has_unsafe and has_safe
    return False


def check_public_network_access(node):
    """
    Check for allowing public network access to cloud resources.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', '')).lower()
        public_access_patterns = [
            '0.0.0.0/0', '::/0', 'public', 'internet',
            'allow_all', '*', 'any', 'open'
        ]
        return any(pattern in value for pattern in public_access_patterns)
    return False


def check_unrestricted_outbound(node):
    """
    Check for unrestricted outbound communications.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', '')).lower()
        outbound_patterns = [
            'outbound', 'egress', 'outgoing',
            '0.0.0.0/0', 'any', '*', 'all'
        ]
        # Look for patterns that suggest unrestricted outbound access
        outbound_count = sum(1 for pattern in outbound_patterns if pattern in value)
        return outbound_count >= 2  # Multiple indicators
    return False


def check_regex_empty_alternatives(node):
    """
    Check for regular expressions with empty alternatives.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    if isinstance(func, dict):
        # Check for regex function calls
        if func.get('node_type') == 'Attribute':
            attr = func.get('attr', '')
            if attr in ['compile', 'match', 'search', 'findall', 'sub']:
                args = node.get('args', [])
                if args and isinstance(args[0], dict):
                    if args[0].get('node_type') in ['Constant', 'Str']:
                        pattern = str(args[0].get('value', ''))
                        # Check for empty alternatives like |a| or ||
                        if re.search(r'\|\s*\||\|\s*$|^\s*\|', pattern):
                            return True
    return False


def check_regex_anchor_grouping(node):
    """
    Check for regex alternatives that should be grouped with anchors.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    if isinstance(func, dict):
        # Check if this is a regex function call
        if func.get('node_type') == 'Attribute':
            attr = func.get('attr', '')
            if attr in ['compile', 'match', 'search', 'findall', 'sub']:
                args = node.get('args', [])
                if args and isinstance(args[0], dict):
                    if args[0].get('node_type') in ['Constant', 'Str']:
                        pattern = str(args[0].get('value', ''))
                        # Check for anchor patterns that need grouping
                        # Look for patterns like ^a|b$ instead of ^(a|b)$
                        if re.search(r'\^[^(]*\|.*\$', pattern):
                            return True
    return False


def check_weak_cipher_algorithms(node):
    """
    Check for usage of weak cipher algorithms like DES, RC4, MD5, etc.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', '')).upper()
        weak_algorithms = [
            'DES', 'RC4', 'MD5', 'SHA1', 'MD4', 'RC2', 
            'BLOWFISH', 'IDEA', 'NULL', 'ANON', 'ADH',
            'EXPORT', 'LOW', 'MEDIUM'
        ]
        # Check for weak algorithm names in strings
        for algorithm in weak_algorithms:
            if algorithm in value:
                return True
    elif node.get('node_type') == 'Call':
        # Check for cryptographic function calls with weak algorithms
        func = node.get('func', {})
        if isinstance(func, dict):
            if func.get('node_type') == 'Attribute':
                attr = func.get('attr', '')
                if attr in ['new', 'digest', 'encrypt', 'decrypt']:
                    # Check the arguments for weak algorithm names
                    args = node.get('args', [])
                    for arg in args:
                        if isinstance(arg, dict) and arg.get('node_type') in ['Constant', 'Str']:
                            value = str(arg.get('value', '')).upper()
                            if any(alg in value for alg in ['DES', 'RC4', 'MD5', 'SHA1']):
                                return True
    return False


def check_predictable_ivs(node):
    """
    Check for predictable initialization vectors (IVs) in CBC mode encryption.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', ''))
        # Check for common predictable IV patterns
        predictable_patterns = [
            '00000000',  # All zeros
            '11111111',  # All ones
            '12345678',  # Sequential
            'AAAAAAAA',  # Repeated characters
            'FFFFFFFF',  # All F's
            '\\x00',      # Null bytes
        ]
        for pattern in predictable_patterns:
            if pattern in value:
                return True
        
        # Check for hardcoded hex patterns (potential IVs)
        if re.match(r'^[0-9a-fA-F]{16,32}$', value):
            # This looks like a hardcoded IV
            return True
            
    elif node.get('node_type') == 'Call':
        # Check for cryptographic function calls with predictable IVs
        func = node.get('func', {})
        if isinstance(func, dict):
            if func.get('node_type') == 'Attribute':
                attr = func.get('attr', '')
                if attr in ['new', 'encrypt', 'decrypt'] and 'IV' in str(node):
                    # Check for hardcoded IV values in crypto calls
                    args = node.get('args', [])
                    keywords = node.get('keywords', [])
                    
                    # Check keyword arguments for IV
                    for kw in keywords:
                        if isinstance(kw, dict) and kw.get('arg') in ['iv', 'IV']:
                            value_node = kw.get('value', {})
                            if value_node.get('node_type') in ['Constant', 'Str']:
                                iv_value = str(value_node.get('value', ''))
                                if len(iv_value) > 0 and not any(c.isalpha() for c in iv_value if c not in 'abcdefABCDEF'):
                                    return True  # Likely hardcoded IV
    return False


def check_sklearn_pipeline_memory(node):
    """
    Check for sklearn Pipeline calls that don't specify a memory parameter.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    if isinstance(func, dict):
        # Check for Pipeline constructor calls
        if func.get('node_type') == 'Name' and func.get('id') == 'Pipeline':
            # Check if memory parameter is specified
            keywords = node.get('keywords', [])
            for kw in keywords:
                if isinstance(kw, dict) and kw.get('arg') == 'memory':
                    return False  # Memory parameter is specified, no violation
            return True  # Pipeline call without memory parameter
        
        # Check for sklearn.pipeline.Pipeline calls
        elif func.get('node_type') == 'Attribute':
            if func.get('attr') == 'Pipeline':
                value = func.get('value', {})
                if isinstance(value, dict):
                    # Check if it's from sklearn.pipeline
                    if (value.get('node_type') == 'Attribute' and 
                        value.get('attr') == 'pipeline' and
                        value.get('value', {}).get('id') == 'sklearn'):
                        # Check if memory parameter is specified
                        keywords = node.get('keywords', [])
                        for kw in keywords:
                            if isinstance(kw, dict) and kw.get('arg') == 'memory':
                                return False  # Memory parameter is specified
                        return True  # sklearn Pipeline call without memory parameter
    return False


def check_regex_multiple_spaces(node):
    """
    Check for regular expression patterns containing multiple consecutive spaces.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    if isinstance(func, dict):
        # Check for regex module function calls
        regex_functions = ['compile', 'match', 'search', 'findall', 'sub', 'subn', 'split']
        
        if func.get('node_type') == 'Attribute':
            attr = func.get('attr', '')
            if attr in regex_functions:
                # Check if it's from 're' module
                value = func.get('value', {})
                if isinstance(value, dict) and value.get('id') == 're':
                    # Check the first argument (regex pattern)
                    args = node.get('args', [])
                    if args and isinstance(args[0], dict):
                        if args[0].get('node_type') in ['Constant', 'Str']:
                            pattern = str(args[0].get('value', ''))
                            # Check for multiple consecutive spaces
                            if '  ' in pattern:  # Two or more spaces
                                return True
        
        # Check for direct regex function calls (if re is imported as 'from re import compile')
        elif func.get('node_type') == 'Name':
            name = func.get('id', '')
            if name in regex_functions:
                # Check the first argument (regex pattern)
                args = node.get('args', [])
                if args and isinstance(args[0], dict):
                    if args[0].get('node_type') in ['Constant', 'Str']:
                        pattern = str(args[0].get('value', ''))
                        # Check for multiple consecutive spaces
                        if '  ' in pattern:  # Two or more spaces
                            return True
    return False


def check_break_continue_return_in_finally(node):
    """
    Check for break, continue, or return statements in finally blocks.
    """
    if node.get('node_type') != 'Try':
        return False
    
    # Check if there's a finally block
    finalbody = node.get('finalbody', [])
    if not finalbody:
        return False
    
    # Recursively check for break, continue, or return statements in finally block
    def has_flow_control_statements(statements):
        for stmt in statements:
            if isinstance(stmt, dict):
                stmt_type = stmt.get('node_type', '')
                
                # Direct flow control statements
                if stmt_type in ['Break', 'Continue', 'Return']:
                    return True
                
                # Check nested structures
                for key in ['body', 'orelse', 'finalbody']:
                    nested = stmt.get(key, [])
                    if isinstance(nested, list) and has_flow_control_statements(nested):
                        return True
        return False
    
    return has_flow_control_statements(finalbody)


def check_hardcoded_ip_addresses(node):
    """
    Check for hardcoded IP addresses in string constants.
    Only flags actual IP address patterns, not random numbers.
    """
    if node.get('node_type') in ['Constant', 'Str']:
        value = str(node.get('value', ''))
        
        # Only check string values that could be IP addresses
        if not isinstance(node.get('value'), str):
            return False
        
        # Must be a string and match full IP pattern
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        
        # Check if the entire string is an IP address
        if re.match(ip_pattern, value.strip()):
            return True
        
        # Also check for IP addresses within longer strings (like URLs)
        ip_in_string = r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
        if re.search(ip_in_string, value):
            return True
            
    return False


def check_nested_estimator_parameters_modification_in_a_pipeline_should_refer_to_valid_parameters(node, file_dict, property_path):
    """Check for Pipeline set_params calls - only trigger on actual Pipeline usage"""
    if isinstance(node, dict) and node.get('node_type') == 'Call':
        func = node.get('func', {})
        if isinstance(func, dict) and func.get('node_type') == 'Attribute':
            attr = func.get('attr')
            if attr == 'set_params':
                # Check if the object being called is likely a Pipeline
                value = func.get('value', {})
                if isinstance(value, dict) and value.get('node_type') == 'Name':
                    var_name = value.get('id', '')
                    # Only trigger if variable name suggests it's a pipeline
                    if 'pipeline' in var_name.lower():
                        return True
                    # Also check if Pipeline class is imported/used in the file
                    if has_pipeline_import(file_dict):
                        return True
    return False


def has_pipeline_import(file_dict):
    """Check if Pipeline is imported in the file"""
    if not isinstance(file_dict, dict):
        return False
    
    def check_imports(node):
        if isinstance(node, dict):
            if node.get('node_type') == 'ImportFrom':
                module = node.get('module')
                if module and 'sklearn' in module and 'pipeline' in module.lower():
                    return True
                names = node.get('names', [])
                for name in names:
                    if isinstance(name, dict) and name.get('name') == 'Pipeline':
                        return True
            elif node.get('node_type') == 'Import':
                names = node.get('names', [])
                for name in names:
                    if isinstance(name, dict):
                        name_str = name.get('name', '')
                        if 'sklearn' in name_str and 'pipeline' in name_str.lower():
                            return True
        elif isinstance(node, list):
            for item in node:
                if check_imports(item):
                    return True
        return False
    
    return check_imports(file_dict)


def check_pandaspipe_method_should_be_preferred_over_long_chains_of_instructions(node, file_dict, property_path):
    """Check for long pandas method chains that should use pipe() instead"""
    if isinstance(node, dict) and node.get('node_type') == 'Attribute':
        attr = node.get('attr')
        pandas_methods = ['fillna', 'dropna', 'groupby', 'sort_values', 'reset_index', 'sum', 'mean', 'median']
        
        if attr in pandas_methods:
            # Check if this is part of a long method chain (3+ chained calls)
            chain_length = count_method_chain_length(node)
            if chain_length >= 3:
                # Also check if pandas is likely being used in this file
                if has_pandas_import(file_dict) or has_dataframe_usage(file_dict):
                    return True
    return False


def count_method_chain_length(node):
    """Count the length of a method chain"""
    count = 0
    current = node
    
    while isinstance(current, dict):
        if current.get('node_type') == 'Attribute':
            count += 1
            current = current.get('value', {})
        elif current.get('node_type') == 'Call':
            # If it's a call, check the func part
            func = current.get('func', {})
            if isinstance(func, dict) and func.get('node_type') == 'Attribute':
                count += 1
                current = func.get('value', {})
            else:
                break
        else:
            break
    
    return count


def has_pandas_import(file_dict):
    """Check if pandas is imported in the file"""
    if not isinstance(file_dict, dict):
        return False
    
    def check_imports(node):
        if isinstance(node, dict):
            if node.get('node_type') == 'ImportFrom':
                module = node.get('module')
                if module and 'pandas' in module:
                    return True
            elif node.get('node_type') == 'Import':
                names = node.get('names', [])
                for name in names:
                    if isinstance(name, dict):
                        name_str = name.get('name', '')
                        if 'pandas' in name_str:
                            return True
        elif isinstance(node, list):
            for item in node:
                if check_imports(item):
                    return True
        return False
    
    return check_imports(file_dict)


def has_dataframe_usage(file_dict):
    """Check if DataFrame is used in the file"""
    if not isinstance(file_dict, dict):
        return False
    
    def check_dataframe(node):
        if isinstance(node, dict):
            if node.get('node_type') == 'Name' and node.get('id') == 'DataFrame':
                return True
            # Check for 'df' variable names (common pandas convention)
            if node.get('node_type') == 'Name' and node.get('id', '').startswith('df'):
                return True
        elif isinstance(node, list):
            for item in node:
                if check_dataframe(item):
                    return True
        return False
    
    return check_dataframe(file_dict)


def check_server_hostnames_should_be_verified_during_ssltls_connections(node, file_dict, property_path):
    """Check for SSL/TLS connections without hostname verification"""
    if isinstance(node, dict):
        # Check for ssl context creation without hostname verification
        if node.get('node_type') == 'Call':
            func = node.get('func', {})
            if isinstance(func, dict):
                # Check for ssl.create_default_context() or similar SSL calls
                if func.get('node_type') == 'Attribute':
                    attr = func.get('attr')
                    value = func.get('value', {})
                    if (attr in ['create_default_context', 'SSLContext', 'wrap_socket'] and
                        isinstance(value, dict) and value.get('node_type') == 'Name' and
                        value.get('id') == 'ssl'):
                        return True
                        
                # Check for urllib/requests with SSL context
                elif func.get('node_type') == 'Name':
                    func_name = func.get('id', '')
                    if func_name in ['urlopen', 'get', 'post', 'request']:
                        # Check if SSL verification is disabled in arguments
                        keywords = node.get('keywords', [])
                        for kw in keywords:
                            if isinstance(kw, dict):
                                arg_name = kw.get('arg')
                                if arg_name == 'verify' or arg_name == 'check_hostname':
                                    value = kw.get('value', {})
                                    if (isinstance(value, dict) and 
                                        value.get('node_type') == 'Constant' and 
                                        value.get('value') is False):
                                        return True
        
        # Check for assignment statements that disable SSL verification
        elif node.get('node_type') == 'Assign':
            targets = node.get('targets', [])
            for target in targets:
                if isinstance(target, dict) and target.get('node_type') == 'Attribute':
                    attr = target.get('attr')
                    if attr in ['check_hostname', 'verify_mode']:
                        value = node.get('value', {})
                        if (isinstance(value, dict) and value.get('node_type') == 'Constant' and
                            (value.get('value') is False or value.get('value') == 0)):
                            return True
    
    return False


def check_only_defined_names_should_be_listed_in_all(node, file_dict, property_path):
    """Check for names in __all__ that are not actually defined in the module"""
    if isinstance(node, dict) and node.get('node_type') == 'Assign':
        targets = node.get('targets', [])
        for target in targets:
            if (isinstance(target, dict) and target.get('node_type') == 'Name' and
                target.get('id') == '__all__'):
                # Found an __all__ assignment
                value = node.get('value', {})
                if isinstance(value, dict):
                    all_names = extract_all_names(value)
                    if all_names:
                        defined_names = get_defined_names(file_dict)
                        # Check if any name in __all__ is not defined
                        for name in all_names:
                            if name not in defined_names:
                                return True
    return False


def extract_all_names(value_node):
    """Extract names from __all__ list/tuple"""
    names = []
    if isinstance(value_node, dict):
        if value_node.get('node_type') in ['List', 'Tuple']:
            elts = value_node.get('elts', [])
            for elt in elts:
                if isinstance(elt, dict) and elt.get('node_type') in ['Constant', 'Str']:
                    name = elt.get('value')
                    if isinstance(name, str):
                        names.append(name)
    return names


def get_defined_names(file_dict):
    """Get all names defined in the module"""
    defined = set()
    
    def collect_names(node):
        if isinstance(node, dict):
            node_type = node.get('node_type')
            if node_type in ['FunctionDef', 'AsyncFunctionDef', 'ClassDef']:
                name = node.get('name')
                if name:
                    defined.add(name)
            elif node_type == 'Assign':
                targets = node.get('targets', [])
                for target in targets:
                    if isinstance(target, dict) and target.get('node_type') == 'Name':
                        name = target.get('id')
                        if name and name != '__all__':
                            defined.add(name)
            elif node_type in ['Import', 'ImportFrom']:
                names = node.get('names', [])
                for name_info in names:
                    if isinstance(name_info, dict):
                        asname = name_info.get('asname')
                        name = name_info.get('name')
                        defined.add(asname or name)
                        
            # Recursively check nested structures
            for key, value in node.items():
                if isinstance(value, (list, dict)):
                    collect_names(value)
        elif isinstance(node, list):
            for item in node:
                collect_names(item)
    
    collect_names(file_dict)
    return defined


def check_hardcoded_passwords_are_securitysensitive(node, file_dict, property_path):
    """Check for hardcoded passwords in assignments and function calls"""
    if isinstance(node, dict):
        # Check assignments with password-like variable names and weak values
        if node.get('node_type') == 'Assign':
            targets = node.get('targets', [])
            value = node.get('value', {})
            
            for target in targets:
                if isinstance(target, dict) and target.get('node_type') == 'Name':
                    var_name = target.get('id', '').lower()
                    # Check if variable name suggests it's a password/credential
                    if any(keyword in var_name for keyword in ['password', 'pwd', 'secret', 'key', 'token', 'credential', 'auth']):
                        # Check if the value is a weak password
                        if isinstance(value, dict) and value.get('node_type') in ['Constant', 'Str']:
                            password_value = str(value.get('value', ''))
                            if is_weak_password(password_value):
                                return True
        
        # Check function calls with password parameters
        elif node.get('node_type') == 'Call':
            keywords = node.get('keywords', [])
            for kw in keywords:
                if isinstance(kw, dict):
                    arg_name = kw.get('arg', '').lower()
                    if arg_name in ['password', 'pwd', 'secret', 'api_key', 'token']:
                        value = kw.get('value', {})
                        if isinstance(value, dict) and value.get('node_type') in ['Constant', 'Str']:
                            password_value = str(value.get('value', ''))
                            if is_weak_password(password_value):
                                return True
        
        # Check dictionary literals with password keys
        elif node.get('node_type') == 'Dict':
            keys = node.get('keys', [])
            values = node.get('values', [])
            for i, key in enumerate(keys):
                if isinstance(key, dict) and key.get('node_type') in ['Constant', 'Str']:
                    key_name = str(key.get('value', '')).lower()
                    if any(keyword in key_name for keyword in ['password', 'pwd', 'secret', 'key', 'token']):
                        if i < len(values):
                            value = values[i]
                            if isinstance(value, dict) and value.get('node_type') in ['Constant', 'Str']:
                                password_value = str(value.get('value', ''))
                                if is_weak_password(password_value):
                                    return True
    
    return False


def is_weak_password(password):
    """Check if a password is considered weak"""
    if not isinstance(password, str) or len(password) < 3:
        return False
    
    password_lower = password.lower()
    
    # Common weak passwords
    weak_passwords = [
        '123456', 'password', 'admin', 'root', 'user', 'guest', 'test',
        'admin123', 'password123', 'root123', 'user123', 'test123',
        'qwerty', 'abc123', '111111', '000000', 'letmein', 'welcome',
        'monkey', 'dragon', 'master', 'secret', 'login', 'pass',
        '12345678', '1234567890', 'password1', 'admin1', 'secret123'
    ]
    
    # Check exact matches
    if password_lower in weak_passwords:
        return True
    
    # Check simple patterns
    if password.isdigit() and len(password) <= 8:  # All numeric and short
        return True
    
    if len(password) <= 6:  # Very short passwords
        return True
    
    # Check for simple patterns like "123456", "abcdef", etc.
    if all(ord(password[i]) == ord(password[0]) + i for i in range(len(password))):
        return True
    
    return False


def check_init_should_not_return_a_value(node):
    """Check that __init__ methods don't return a value"""
    if isinstance(node, dict) and node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
        name = node.get('name', '')
        if name == '__init__':
            # Check if __init__ has a return statement with a value
            body = node.get('body', [])
            return has_return_value(body)
    return False


def has_return_value(body):
    """Check if function body has return statements with values"""
    if isinstance(body, list):
        for stmt in body:
            if isinstance(stmt, dict):
                if stmt.get('node_type') == 'Return':
                    value = stmt.get('value')
                    # If return has a value (not just 'return' or 'return None')
                    if value is not None and not (isinstance(value, dict) and 
                                                 value.get('node_type') == 'Constant' and 
                                                 value.get('value') is None):
                        return True
                # Recursively check nested structures
                for key, val in stmt.items():
                    if isinstance(val, list) and has_return_value(val):
                        return True
    return False


def check_iter_should_return_an_iterator(node, file_dict, property_path):
    """Check that __iter__ methods return an iterator"""
    if isinstance(node, dict) and node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
        name = node.get('name', '')
        if name == '__iter__':
            # Check if __iter__ has proper return statements
            body = node.get('body', [])
            if not has_return_statement(body):
                return True  # __iter__ should have return statements
    return False


def has_return_statement(body):
    """Check if function body has any return statements"""
    if isinstance(body, list):
        for stmt in body:
            if isinstance(stmt, dict):
                if stmt.get('node_type') == 'Return':
                    return True
                # Recursively check nested structures
                for key, val in stmt.items():
                    if isinstance(val, list) and has_return_statement(val):
                        return True
    return False


def check_zoneinfo_should_be_preferred_to_pytz_when_using_python_39_and_later(node, file_dict, property_path):
    """Check for pytz imports when Python 3.9+ is being used"""
    if isinstance(node, dict):
        # Check import statements
        if node.get('node_type') == 'Import':
            names = node.get('names', [])
            for name_info in names:
                if isinstance(name_info, dict):
                    name = name_info.get('name', '')
                    if name == 'pytz' or name.startswith('pytz.'):
                        return True
        
        # Check from imports
        elif node.get('node_type') == 'ImportFrom':
            module = node.get('module', '')
            if module == 'pytz' or module.startswith('pytz.'):
                return True
    
    return False


def check_iter_returns_iterator(node):
    """
    Check if __iter__ method returns an iterator.
    Only applies to functions named __iter__.
    """
    if node.get('node_type') != 'FunctionDef':
        return False
    
    # Only check functions named __iter__
    if node.get('name') != '__iter__':
        return False
    
    # This would require complex analysis of return statements
    # For now, return False as this needs return type analysis
    return False


def check_general_rule(node):
    """
    Generic rule checker - returns False to disable problematic generic rules.
    This function is used as a placeholder for rules that need specific implementation.
    """
    return False  # Disable generic rules to prevent false positives


def check_empty_function(node):
    """
    Check if a function or method is empty (only contains pass, docstring, or nothing).
    """
    if node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    body = node.get('body', [])
    if not body:
        return True  # Completely empty function
    
    # Filter out docstrings (first string literal)
    meaningful_statements = []
    for i, stmt in enumerate(body):
        if isinstance(stmt, dict):
            # Skip docstring (first statement that's a string constant)
            if (i == 0 and stmt.get('node_type') == 'Expr' and 
                isinstance(stmt.get('value'), dict) and 
                stmt['value'].get('node_type') in ['Constant', 'Str']):
                continue
            meaningful_statements.append(stmt)
    
    # Check if only contains pass statements
    if not meaningful_statements:
        return True
    
    if len(meaningful_statements) == 1:
        stmt = meaningful_statements[0]
        if isinstance(stmt, dict) and stmt.get('node_type') == 'Pass':
            return True
    
    return False


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


def check_local_variable_naming_convention(node):
    """
    Check if local variables and function parameters comply with naming conventions.
    Only checks actual variable assignments and function parameters, not function calls or module references.
    """
    # Only check variable assignments (targets of Assign nodes)
    if node.get('node_type') == 'Assign':
        targets = node.get('targets', [])
        for target in targets:
            if isinstance(target, dict) and target.get('node_type') == 'Name':
                var_name = target.get('id', '')
                if var_name and not _is_valid_variable_name(var_name):
                    return True
    
    # Check function parameter names
    elif node.get('node_type') in ['FunctionDef', 'AsyncFunctionDef']:
        args = node.get('args', {})
        if isinstance(args, dict):
            params = args.get('args', [])
            for param in params:
                if isinstance(param, dict) and param.get('node_type') == 'arg':
                    param_name = param.get('arg', '')
                    if param_name and not _is_valid_parameter_name(param_name):
                        return True
    
    # Check for loop variables
    elif node.get('node_type') == 'For':
        target = node.get('target', {})
        if isinstance(target, dict) and target.get('node_type') == 'Name':
            var_name = target.get('id', '')
            if var_name and not _is_valid_variable_name(var_name):
                return True
    
    return False


def _is_valid_variable_name(var_name):
    """Helper function to validate variable names."""
    # Exclude common special cases
    if var_name in ['self', 'cls']:
        return True
    
    # Exclude single uppercase letters (often used for types/constants)
    if len(var_name) == 1 and var_name.isupper():
        return True
    
    # Exclude class names (they start with uppercase by convention)
    if var_name[0].isupper():
        return True
    
    # Check if variable name follows snake_case convention
    import re
    return bool(re.match(r'^[a-z][a-z0-9_]*$', var_name))


def _is_valid_parameter_name(param_name):
    """Helper function to validate parameter names."""
    # Exclude common special parameters
    if param_name in ['self', 'cls']:
        return True
    
    # Check parameter naming convention (same as variables)
    import re
    return bool(re.match(r'^[a-z][a-z0-9_]*$', param_name))


def check_self_first_argument(node):
    """
    Check if instance methods have 'self' as the first argument.
    Only checks functions inside classes that should have 'self'.
    """
    import ast
    
    # Only check function definitions
    if not isinstance(node, dict) or node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    # Get function arguments
    args = node.get('args', {})
    if not isinstance(args, dict):
        return False
    
    arg_list = args.get('args', [])
    if not arg_list:
        return False  # No arguments at all
    
    # Check if first argument is 'self'
    first_arg = arg_list[0]
    if isinstance(first_arg, dict):
        first_arg_name = first_arg.get('arg', '')
        
        # Special methods that don't need 'self' as first arg
        func_name = node.get('name', '')
        if func_name in ['__new__', '__init_subclass__', '__class_getitem__']:
            return False  # These are special cases
        
        # Static methods and class methods are special cases too
        # We'd need more context to determine these
        
        # Only flag if this looks like an instance method that should have 'self'
        # For now, be conservative - only flag obvious violations
        if first_arg_name != 'self' and func_name not in ['__new__', '__init_subclass__', '__class_getitem__']:
            # Only flag if it's clearly an instance method (not a function)
            # This is conservative to avoid false positives
            return False  # Too many false positives, disable for now
    
    return False


def check_duplicated_string_literals(node, file_dict=None, property_path=None):
    """
    Check for duplicated string literals in the file.
    This requires file-level analysis to track all strings.
    """
    if node.get('node_type') not in ['Constant', 'Str']:
        return False
    
    value = node.get('value')
    if not isinstance(value, str) or len(value) < 3:
        return False  # Don't check very short strings
    
    # Skip common single-character or very short strings
    if value in [' ', '\n', '\t', '', '/', '\\', '.', ',', ';', ':']:
        return False
    
    # For now, return False as this requires complex file-level analysis
    # to count occurrences of each string literal
    return False


def check_tensorflow_function_recursion(node, file_dict=None, property_path=None):
    """
    Check for recursive TensorFlow functions.
    Only applies to functions decorated with @tf.function.
    """
    if node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    # Check if function has @tf.function decorator
    decorators = node.get('decorator_list', [])
    has_tf_function = False
    
    for decorator in decorators:
        if isinstance(decorator, dict):
            # Check for @tf.function
            if decorator.get('node_type') == 'Attribute':
                attr = decorator.get('attr')
                value = decorator.get('value', {})
                if (attr == 'function' and isinstance(value, dict) and 
                    value.get('node_type') == 'Name' and value.get('id') == 'tf'):
                    has_tf_function = True
                    break
            # Check for direct function call
            elif decorator.get('node_type') == 'Call':
                func = decorator.get('func', {})
                if (isinstance(func, dict) and func.get('node_type') == 'Attribute' and
                    func.get('attr') == 'function'):
                    value = func.get('value', {})
                    if (isinstance(value, dict) and value.get('node_type') == 'Name' and 
                        value.get('id') == 'tf'):
                        has_tf_function = True
                        break
    
    if not has_tf_function:
        return False  # Not a tf.function, so rule doesn't apply
    
    # TODO: Add actual recursion detection logic here
    # For now, return False as this requires call graph analysis
    return False


def check_tensorflow_variable_singletons(node, file_dict=None, property_path=None):
    """
    Check for tf.Variable objects that should be singletons in tf.function.
    Only applies to functions with @tf.function decorator that create tf.Variable.
    """
    if node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    # First check if this is a tf.function
    decorators = node.get('decorator_list', [])
    has_tf_function = False
    
    for decorator in decorators:
        if isinstance(decorator, dict):
            if decorator.get('node_type') == 'Attribute':
                attr = decorator.get('attr')
                value = decorator.get('value', {})
                if (attr == 'function' and isinstance(value, dict) and 
                    value.get('node_type') == 'Name' and value.get('id') == 'tf'):
                    has_tf_function = True
                    break
    
    if not has_tf_function:
        return False  # Not a tf.function
    
    # TODO: Add logic to check for tf.Variable creation patterns
    # For now, return False as this requires complex AST analysis
    return False


def check_pandas_to_numpy_preference(node, file_dict=None, property_path=None):
    """
    Check for pandas DataFrame.values usage that should use to_numpy().
    Only applies when pandas DataFrames are actually being used.
    """
    if node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    # Check if pandas is imported in the file
    if not has_pandas_import(file_dict):
        return False  # No pandas usage, rule doesn't apply
    
    # TODO: Add logic to check for .values attribute access on DataFrames
    # For now, return False as this requires complex analysis
    return False


def check_tensorflow_side_effects(node):
    """
    Check if Python side effects are used inside tf.function decorated functions.
    Only applies when TensorFlow is imported and function has tf.function decorator.
    """
    if node.get('node_type') not in ['FunctionDef', 'AsyncFunctionDef']:
        return False
    
    # Check if TensorFlow is imported
    module_imports = node.get('imports', [])
    has_tensorflow = any('tensorflow' in imp or 'tf' in imp for imp in module_imports)
    
    if not has_tensorflow:
        return False
    
    # Check if function has tf.function decorator
    decorators = node.get('decorator_list', [])
    has_tf_function = any(
        (isinstance(dec, dict) and 
         (dec.get('id') == 'tf.function' or 
          (isinstance(dec.get('attr'), str) and dec.get('attr') == 'function')))
        for dec in decorators
    )
    
    if not has_tf_function:
        return False
    
    # For now, return False to prevent false positives until proper implementation
    return False


def check_noncallable_calls(node):
    """
    Check for obvious cases where non-callable values are being called.
    Detects direct literal calls and simple heuristics for variable names.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    if not isinstance(func, dict):
        return False
    
    # Case 1: Direct literal calls like 5(), "hello"(), True()
    if func.get('node_type') in ['Constant', 'Num', 'Str']:
        return True
    
    # Case 2: Simple heuristic for common variable names that suggest literal values
    if func.get('node_type') == 'Name':
        var_name = func.get('id', '')
        
        # Heuristic: variable names that commonly hold literal values
        literal_like_names = ['value', 'number', 'text', 'string', 'data', 'count', 'size', 'result']
        if var_name.lower() in literal_like_names:
            return True
    
    return False


def check_obvious_noncallable_calls(node, file_dict=None, property_path=None):
    """
    Detect obvious cases where literals or simple variables 
    assigned to literals are being called.
    More comprehensive version that can analyze file context.
    """
    if node.get('node_type') != 'Call':
        return False
    
    func = node.get('func', {})
    
    # Case 1: Direct literal calls like 5() or "hello"()
    if isinstance(func, dict):
        if func.get('node_type') in ['Constant', 'Num', 'Str']:
            return True
    
    # Case 2: Simple variable assigned to literal in same function
    if func.get('node_type') == 'Name':
        var_name = func.get('id', '')
        
        # TODO: This would need more complex analysis to track assignments
        # For now, use the same heuristic as check_noncallable_calls
        literal_like_names = ['value', 'number', 'text', 'string', 'data', 'count', 'size', 'result']
        if var_name.lower() in literal_like_names:
            return True
    
    return False


def check_cancellation_exception_reraised(node):
    """
    Check if cancellation exceptions (KeyboardInterrupt, SystemExit) are properly re-raised
    after cleanup in exception handlers.
    """
    if node.get('node_type') != 'ExceptHandler':
        return False
    
    # Check if this handler catches cancellation exceptions
    exception_type = node.get('type', {})
    if not isinstance(exception_type, dict):
        return False
    
    cancellation_exceptions = ['KeyboardInterrupt', 'SystemExit', 'GeneratorExit']
    
    # Check for specific exception types
    exception_name = None
    if exception_type.get('node_type') == 'Name':
        exception_name = exception_type.get('id', '')
    elif exception_type.get('node_type') == 'Tuple':
        # Handle: except (KeyboardInterrupt, SystemExit):
        elts = exception_type.get('elts', [])
        for elt in elts:
            if isinstance(elt, dict) and elt.get('node_type') == 'Name':
                if elt.get('id', '') in cancellation_exceptions:
                    exception_name = elt.get('id', '')
                    break
    
    # If this doesn't handle cancellation exceptions, it's fine
    if exception_name not in cancellation_exceptions:
        return False
    
    # Check if the handler body contains a 'raise' statement (re-raise)
    body = node.get('body', [])
    has_reraise = False
    
    for stmt in body:
        if isinstance(stmt, dict):
            if stmt.get('node_type') == 'Raise':
                # Check if it's a bare 'raise' (re-raise) or 'raise exc'
                if stmt.get('exc') is None:  # Bare raise
                    has_reraise = True
                    break
                # Could also check for explicit re-raise like 'raise exception'
    
    # If it catches cancellation exception but doesn't re-raise, it's a violation
    if not has_reraise:
        return True
    
    return False

def check_comparison_to_none_constant(node, context=None):
    """Check for constant comparisons to None like 'None == None' or 'None != None'."""
    if not isinstance(node, ast.Compare):
        return False
    
    # Check if we have comparisons involving None constants
    has_none = False
    has_constant_none = False
    
    # Check left operand
    if isinstance(node.left, ast.Constant) and node.left.value is None:
        has_none = True
        has_constant_none = True
    elif isinstance(node.left, ast.NameConstant) and node.left.value is None:  # Python < 3.8
        has_none = True
        has_constant_none = True
    
    # Check comparators
    for comp in node.comparators:
        if isinstance(comp, ast.Constant) and comp.value is None:
            if has_none:  # Both sides are None constants
                return True
            has_none = True
        elif isinstance(comp, ast.NameConstant) and comp.value is None:  # Python < 3.8
            if has_none:  # Both sides are None constants
                return True
            has_none = True
    
    return False

def check_deprecated_numpy_aliases(node, context=None):
    """Check for deprecated NumPy aliases of builtin types."""
    if not isinstance(node, ast.Attribute):
        return False
    
    # Deprecated NumPy aliases that should be replaced with builtin types
    deprecated_aliases = {
        'int': 'int',
        'float': 'float', 
        'complex': 'complex',
        'bool': 'bool',
        'str': 'str',
        'unicode': 'str',
        'object': 'object',
        'int_': 'int',
        'float_': 'float',
        'complex_': 'complex',
        'bool_': 'bool',
        'str_': 'str',
        'unicode_': 'str',
        'object_': 'object'
    }
    
    # Check if this is an attribute access on numpy
    if isinstance(node.value, ast.Name):
        numpy_names = ['numpy', 'np']
        if node.value.id in numpy_names and node.attr in deprecated_aliases:
            return True
    
    # Also check for cases like numpy.dtype(numpy.int) 
    if isinstance(node.value, ast.Attribute):
        if (isinstance(node.value.value, ast.Name) and 
            node.value.value.id in ['numpy', 'np'] and
            node.attr in deprecated_aliases):
            return True
    
    return False

def check_autoescaping_disabled(node, context=None):
    """Check for disabled autoescaping in template engines (XSS vulnerability)."""
    if not isinstance(node, ast.Call):
        return False
    
    # Check for Django template configurations that disable autoescaping
    if isinstance(node.func, ast.Attribute):
        # Check for Environment(autoescape=False) in Jinja2
        if node.func.attr in ['Environment']:
            for keyword in getattr(node, 'keywords', []):
                if (hasattr(keyword, 'arg') and keyword.arg == 'autoescape' and
                    hasattr(keyword, 'value')):
                    if (isinstance(keyword.value, ast.Constant) and keyword.value.value is False) or \
                       (isinstance(keyword.value, ast.NameConstant) and keyword.value.value is False):
                        return True
        
        # Check for Django settings like TEMPLATE['OPTIONS']['autoescape'] = False
        if node.func.attr in ['configure', 'update']:
            # This would need more complex analysis of the arguments
            pass
    
    # Check for direct calls that disable autoescaping
    if isinstance(node.func, ast.Name):
        if node.func.id in ['mark_safe', 'Markup']:
            return True
    
    return False

def check_csrf_disabled(node, context=None):
    """Check for disabled CSRF protections (security vulnerability)."""
    if isinstance(node, ast.Assign):
        # Check for CSRF_MIDDLEWARE settings being removed or disabled
        for target in getattr(node, 'targets', []):
            if isinstance(target, ast.Name) and 'CSRF' in target.id.upper():
                if isinstance(node.value, ast.List):
                    # Check if csrf middleware is missing from MIDDLEWARE list
                    pass
                elif isinstance(node.value, (ast.Constant, ast.NameConstant)):
                    if node.value.value is False:
                        return True
    
    elif isinstance(node, ast.Call):
        # Check for @csrf_exempt decorator usage
        if isinstance(node.func, ast.Name) and node.func.id == 'csrf_exempt':
            return True
        
        # Check for disable_csrf_checks() or similar calls
        if isinstance(node.func, ast.Attribute):
            if 'csrf' in node.func.attr.lower() and 'disable' in node.func.attr.lower():
                return True
    
    return False

def check_s3_encryption_disabled(node, context=None):
    """Check for disabled S3 server-side encryption (security vulnerability)."""
    if not isinstance(node, ast.Call):
        return False
    
    # Check for AWS S3 calls that disable encryption
    if isinstance(node.func, ast.Attribute):
        # Check for put_bucket_encryption with None or disabled config
        if node.func.attr in ['put_bucket_encryption', 'create_bucket']:
            for keyword in getattr(node, 'keywords', []):
                if (hasattr(keyword, 'arg') and 
                    keyword.arg in ['ServerSideEncryptionConfiguration', 'Encryption'] and
                    hasattr(keyword, 'value')):
                    if (isinstance(keyword.value, ast.Constant) and keyword.value.value is None) or \
                       (isinstance(keyword.value, ast.NameConstant) and keyword.value.value is None):
                        return True
        
        # Check for delete_bucket_encryption calls
        if node.func.attr in ['delete_bucket_encryption']:
            return True
    
    return False

def check_s3_versioning_disabled(node, context=None):
    """Check for disabled S3 bucket versioning (security vulnerability)."""
    if not isinstance(node, ast.Call):
        return False
    
    # Check for AWS S3 calls that disable versioning
    if isinstance(node.func, ast.Attribute):
        # Check for put_bucket_versioning with Suspended status
        if node.func.attr in ['put_bucket_versioning']:
            for keyword in getattr(node, 'keywords', []):
                if (hasattr(keyword, 'arg') and 
                    keyword.arg in ['VersioningConfiguration'] and
                    hasattr(keyword, 'value')):
                    # Look for Status: 'Suspended' in the configuration
                    if isinstance(keyword.value, ast.Dict):
                        for i, key in enumerate(getattr(keyword.value, 'keys', [])):
                            if (isinstance(key, ast.Constant) and key.value == 'Status' and
                                i < len(keyword.value.values)):
                                val = keyword.value.values[i]
                                if (isinstance(val, ast.Constant) and 
                                    val.value in ['Suspended', 'suspended']):
                                    return True
    
    return False

def check_django_model_str_method(node, context=None):
    """Check if Django model class defines a __str__ method."""
    # Handle both AST format and dictionary format
    if isinstance(node, dict):
        # Dictionary format (from scanner)
        if node.get('node_type') != 'ClassDef':
            return False
        
        node_name = node.get('name')
        bases = node.get('bases', [])
        body = node.get('body', [])
        
        # Check if this class inherits from models.Model
        is_django_model = False
        for base in bases:
            if isinstance(base, dict):
                if (base.get('node_type') == 'Attribute' and
                    isinstance(base.get('value'), dict) and
                    base.get('value', {}).get('node_type') == 'Name' and
                    base.get('value', {}).get('id') == 'models' and
                    base.get('attr') == 'Model'):
                    is_django_model = True
                    break
                elif (base.get('node_type') == 'Name' and 
                      base.get('id') == 'Model'):
                    is_django_model = True
                    break
        
        if not is_django_model:
            return False
        
        # Check if the class defines a __str__ method
        for item in body:
            if (isinstance(item, dict) and 
                item.get('node_type') == 'FunctionDef' and 
                item.get('name') == '__str__'):
                return False  # __str__ method found, no violation
        
        return True  # Django model without __str__ method
        
    else:
        # Original AST format
        if not isinstance(node, ast.ClassDef):
            return False
        
        # Check if this class inherits from models.Model
        is_django_model = False
        for base in getattr(node, 'bases', []):
            if isinstance(base, ast.Attribute):
                if (isinstance(base.value, ast.Name) and 
                    base.value.id == 'models' and 
                    base.attr == 'Model'):
                    is_django_model = True
                    break
            elif isinstance(base, ast.Name) and base.id == 'Model':
                is_django_model = True
                break
        
        if not is_django_model:
            return False
        
        # Check if the class defines a __str__ method
        for item in getattr(node, 'body', []):
            if (isinstance(item, ast.FunctionDef) and 
                item.name == '__str__'):
                return False  # __str__ method found, no violation
        
        return True  # Django model without __str__ method

def check_dynamic_code_execution(node, context=None):
    """Check for dynamic code execution (security vulnerability)."""
    # Handle both AST format and dictionary format
    if isinstance(node, dict):
        # Dictionary format (from scanner)
        if node.get('node_type') != 'Call':
            return False
        
        func = node.get('func', {})
        if isinstance(func, dict):
            func_id = func.get('id')
            if func_id in ['eval', 'exec', 'compile']:
                return True
            
            # Check for __import__ calls
            if func_id == '__import__':
                return True
                
            # Check for subprocess calls with shell=True
            if func_id == 'call' and isinstance(func.get('value'), dict):
                if func.get('value', {}).get('id') == 'subprocess':
                    keywords = node.get('keywords', [])
                    for kw in keywords:
                        if (isinstance(kw, dict) and 
                            kw.get('arg') == 'shell' and
                            isinstance(kw.get('value'), dict) and
                            kw.get('value', {}).get('value') is True):
                            return True
        
    else:
        # Original AST format
        if not isinstance(node, ast.Call):
            return False
            
        if isinstance(node.func, ast.Name):
            if node.func.id in ['eval', 'exec', 'compile', '__import__']:
                return True
        
        # Check for subprocess calls with shell=True
        elif isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'subprocess' and
                node.func.attr == 'call'):
                for keyword in getattr(node, 'keywords', []):
                    if (hasattr(keyword, 'arg') and keyword.arg == 'shell' and
                        hasattr(keyword, 'value') and
                        ((isinstance(keyword.value, ast.Constant) and keyword.value.value is True) or
                         (isinstance(keyword.value, ast.NameConstant) and keyword.value.value is True))):
                        return True
    
    return False


def check_flask_secret_keys(node):
    """
    Check for hardcoded Flask secret keys.
    """
    if isinstance(node, dict):
        node_type = node.get('node_type')
        
        # Check for app.config['SECRET_KEY'] = "hardcoded_value"
        if node_type == 'Assign':
            targets = node.get('targets', [])
            value = node.get('value', {})
            
            for target in targets:
                if (isinstance(target, dict) and 
                    target.get('node_type') == 'Subscript'):
                    
                    # Check if it's accessing 'SECRET_KEY'
                    slice_value = target.get('slice', {})
                    if (isinstance(slice_value, dict) and
                        slice_value.get('node_type') == 'Constant' and
                        slice_value.get('value') == 'SECRET_KEY'):
                        
                        # Check if the assigned value is a string constant
                        if (isinstance(value, dict) and
                            value.get('node_type') == 'Constant' and
                            isinstance(value.get('value'), str)):
                            return True
        
        # Check for app.secret_key = "hardcoded_value"
        if node_type == 'Assign':
            targets = node.get('targets', [])
            value = node.get('value', {})
            
            for target in targets:
                if (isinstance(target, dict) and 
                    target.get('node_type') == 'Attribute' and
                    target.get('attr') == 'secret_key'):
                    
                    # Check if the assigned value is a string constant
                    if (isinstance(value, dict) and
                        value.get('node_type') == 'Constant' and
                        isinstance(value.get('value'), str)):
                        return True
    
    # Handle AST nodes
    if hasattr(node, '_fields'):
        # Check for app.config['SECRET_KEY'] = "hardcoded_value"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Subscript) and
                    isinstance(target.slice, ast.Constant) and
                    target.slice.value == 'SECRET_KEY' and
                    isinstance(node.value, ast.Constant) and
                    isinstance(node.value.value, str)):
                    return True
        
        # Check for app.secret_key = "hardcoded_value"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Attribute) and
                    target.attr == 'secret_key' and
                    isinstance(node.value, ast.Constant) and
                    isinstance(node.value.value, str)):
                    return True
    
    return False


def check_using_command_line_arguments(node):
    """
    Check for usage of command line argument parsing (security sensitive).
    """
    if node.get('node_type') == 'Import':
        names = node.get('names', [])
        for name_node in names:
            if isinstance(name_node, dict):
                name = name_node.get('name', '')
                if name in ['argparse', 'getopt', 'optparse']:
                    return True
    
    elif node.get('node_type') == 'ImportFrom':
        module = node.get('module', '')
        if module in ['argparse', 'getopt', 'optparse', 'sys']:
            return True
    
    elif node.get('node_type') == 'Attribute':
        attr = node.get('attr', '')
        if attr == 'argv':
            return True
    
    return False


def check_lambda_async_handler(node):
    """
    Check for AWS Lambda handlers that are async functions.
    AWS Lambda handlers should not be async functions.
    """
    if node.get('node_type') == 'AsyncFunctionDef':
        # This is an async function - check if it could be a Lambda handler
        function_name = node.get('name', '')
        
        # Common Lambda handler naming patterns
        handler_patterns = [
            'handler', 'lambda_handler', 'main', 'lambda_function',
            'process', 'run', 'execute'
        ]
        
        # Check if function name suggests it's a handler
        for pattern in handler_patterns:
            if pattern in function_name.lower():
                return True
        
        # Check function parameters - Lambda handlers typically have (event, context)
        args = node.get('args', {})
        if isinstance(args, dict):
            arg_list = args.get('args', [])
            if len(arg_list) >= 2:
                # Check if first two parameters look like Lambda handler signature
                first_arg = arg_list[0].get('arg', '') if len(arg_list) > 0 and isinstance(arg_list[0], dict) else ''
                second_arg = arg_list[1].get('arg', '') if len(arg_list) > 1 and isinstance(arg_list[1], dict) else ''
                
                # Common Lambda handler parameter names
                if (first_arg.lower() in ['event', 'evt', 'e'] and 
                    second_arg.lower() in ['context', 'ctx', 'c']):
                    return True
        
        # If it's any async function, flag it as potentially problematic for Lambda
        # (being conservative - any async function could be a handler)
        return True
    
    return False


def check_lambda_json_serializable_returns(node):
    """
    Check for AWS Lambda handlers that return non-JSON serializable values.
    This function checks Call nodes for non-serializable type constructors.
    """
    if node.get('node_type') == 'Call':
        func = node.get('func', {})
        if isinstance(func, dict) and func.get('node_type') == 'Name':
            func_name = func.get('id', '')
            # Non-JSON serializable types that shouldn't be returned from Lambda
            non_serializable = ['set', 'frozenset', 'object', 'complex', 'bytes', 'bytearray']
            if func_name in non_serializable:
                return True
    
    return False


