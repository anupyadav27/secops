#!/usr/bin/env python3
"""
Test what happens when the scanner processes our rule
"""
import ast
import json
import os
from python_generic_rule import PythonGenericRule

# Load the rule metadata
with open('python_docs/assertions_should_not_fail_or_succeed_unconditionally_metadata.json', 'r') as f:
    metadata = json.load(f)

# Create the rule
rule = PythonGenericRule(metadata)

# Parse the test file
test_file = 'test/test_assertions_should_not_fail_or_succeed_unconditionally_trigger.py'

def parse_python_file(file_path):
    """Parse Python file into AST and convert to dictionary structure for rule processing"""
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return None
    
    # Convert AST to a dictionary structure
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
    
    return {
        'module': ast_to_dict(tree),
        'source_lines': source_code.split('\n'),
        'filename': file_path
    }

print("Parsing test file...")
ast_tree = parse_python_file(test_file)

print("Testing rule applicability...")
is_applicable = rule.is_applicable(ast_tree)
print(f"Rule is applicable: {is_applicable}")

if is_applicable:
    print("\nApplying rule...")
    findings = rule.check(ast_tree, test_file)
    print(f"Number of findings: {len(findings)}")
    
    for i, finding in enumerate(findings):
        print(f"Finding {i+1}: Line {finding.get('line', 'unknown')}, Message: {finding.get('message', 'no message')}")
else:
    print("Rule is not applicable - checking why...")
    
    # Check if we have assert nodes
    def find_assert_nodes(node):
        assert_nodes = []
        if isinstance(node, dict):
            if node.get('node_type') == 'Assert':
                assert_nodes.append(node)
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    assert_nodes.extend(find_assert_nodes(value))
        elif isinstance(node, list):
            for item in node:
                assert_nodes.extend(find_assert_nodes(item))
        return assert_nodes
    
    assert_nodes = find_assert_nodes(ast_tree)
    print(f"Found {len(assert_nodes)} Assert nodes in the AST")
    for i, node in enumerate(assert_nodes[:3]):  # Show first 3
        print(f"Assert node {i+1}: Line {node.get('lineno')}, Test: {node.get('test', {}).get('node_type')}")