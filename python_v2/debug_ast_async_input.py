#!/usr/bin/env python3
"""
Debug script to understand AST structure for async functions with input calls
"""
import ast
import json

# Sample code with async function and input call
test_code = '''
async def example():
    x = input("Prompt: ")
    return x
'''

# Parse and examine the AST
tree = ast.parse(test_code)

def ast_to_dict(node):
    """Convert AST node to dictionary representation"""
    result = {
        'node_type': type(node).__name__,
        'lineno': getattr(node, 'lineno', None),
        'end_lineno': getattr(node, 'end_lineno', None),
        'col_offset': getattr(node, 'col_offset', None),
    }
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            result[field] = [ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
        elif isinstance(value, ast.AST):
            result[field] = ast_to_dict(value)
        else:
            result[field] = value
    return result

ast_dict = ast_to_dict(tree)
print("AST Structure:")
print(json.dumps(ast_dict, indent=2))
