import ast
import json

code = '''
# Should trigger - direct inheritance from Exception
class CustomException(Exception):
    """Custom exception class"""
    pass

# Should trigger - inheritance through another exception
class DatabaseException(Exception):
    pass

class QueryException(DatabaseException):
    pass

# Should NOT trigger - proper inheritance from BaseException
class ProperException(BaseException):
    pass

def raise_error():
    raise CustomException("Error")
'''

def node_to_dict(node):
    """Convert AST node to a dictionary representation."""
    if isinstance(node, ast.AST):
        # Create a dict with node type and attributes
        dict_node = {'node_type': node.__class__.__name__}
        # Add relevant attributes
        for key, value in ast.iter_fields(node):
            # Convert child nodes recursively
            if isinstance(value, (list, tuple)):
                dict_node[key] = [node_to_dict(x) if isinstance(x, (ast.AST, list, tuple)) else x for x in value]
            else:
                dict_node[key] = node_to_dict(value) if isinstance(value, (ast.AST, list, tuple)) else value
        return dict_node
    elif isinstance(node, (list, tuple)):
        return [node_to_dict(x) if isinstance(x, (ast.AST, list, tuple)) else x for x in node]
    return node

# Parse the code and convert to JSON for inspection
tree = ast.parse(code)
dict_tree = node_to_dict(tree)
print(json.dumps(dict_tree, indent=2))