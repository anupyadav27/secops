#!/usr/bin/env python3
"""
Test the assertions rule directly
"""
import ast
import json
from python_generic_rule import PythonGenericRule

# Load the rule metadata
with open('python_docs/assertions_should_not_fail_or_succeed_unconditionally_metadata.json', 'r') as f:
    metadata = json.load(f)

# Create the rule
rule = PythonGenericRule(metadata)

# Test code with assert statements
test_code = """
assert True
assert False
assert x == 5
"""

# Parse the code
tree = ast.parse(test_code)

def ast_to_dict(node):
    """Convert AST node to dictionary representation"""
    result = {
        'node_type': type(node).__name__,
        'lineno': getattr(node, 'lineno', None),
        'end_lineno': getattr(node, 'end_lineno', None),
        'col_offset': getattr(node, 'col_offset', None),
    }
    
    # Add node-specific attributes
    for field, value in ast.iter_fields(node):
        if isinstance(value, list):
            result[field] = [ast_to_dict(item) if isinstance(item, ast.AST) else item for item in value]
        elif isinstance(value, ast.AST):
            result[field] = ast_to_dict(value)
        else:
            result[field] = value
    
    return result

ast_dict = {
    'module': ast_to_dict(tree),
    'source_lines': test_code.split('\n'),
    'filename': 'test.py'
}

print("Testing rule applicability...")
is_applicable = rule.is_applicable(ast_dict)
print(f"Rule is applicable: {is_applicable}")

print("\nTesting rule execution...")
findings = rule.check(ast_dict, 'test.py')
print(f"Number of findings: {len(findings)}")

for i, finding in enumerate(findings):
    print(f"Finding {i+1}: {finding}")