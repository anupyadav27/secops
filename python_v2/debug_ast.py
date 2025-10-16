import ast
import json

def traverse_ast(node):
    if isinstance(node, ast.AST):
        node_type = type(node).__name__
        node_dict = {'node_type': node_type}
        for field, value in ast.iter_fields(node):
            node_dict[field] = traverse_ast(value)
        return node_dict
    elif isinstance(node, list):
        return [traverse_ast(item) for item in node]
    else:
        return node

with open('D:/scanner/python_v2/test/test_return_and_yield_rule.py', 'r') as f:
    code = f.read()
    
tree = ast.parse(code)
print(json.dumps(traverse_ast(tree), indent=2))