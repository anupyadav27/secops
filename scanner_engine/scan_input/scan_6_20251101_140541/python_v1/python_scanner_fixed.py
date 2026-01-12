import sys
import os
import ast
import json
from python_generic_rule import PythonGenericRule
import inspect
import traceback

# Debugging flag: Set to True to enable debug prints, False to disable
DEBUG = True

# Step 1: Input Handling (scan test folder for .py files)
test_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
if not os.path.isdir(test_folder):
    print(f"Test folder '{test_folder}' not found.")
    sys.exit(1)
py_files = [f for f in os.listdir(test_folder) if f.endswith(".py")]
if not py_files:
    print(f"No .py files found in test folder '{test_folder}'.")
    sys.exit(1)
print("Available test scripts:")
for idx, fname in enumerate(py_files, 1):
    print(f"  {idx}. {fname}")
choice = input("Select a test script to scan (number): ").strip()
try:
    py_file = os.path.join(test_folder, py_files[int(choice)-1])
except Exception:
    print("Invalid selection.")
    sys.exit(1)

# Step 2: Parse Python file to AST structure
def parse_python_file(file_path):
    """Parse Python file into AST and convert to dictionary structure for rule processing"""
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        sys.exit(1)
    
    # Convert AST to a dictionary structure with parent references
    def ast_to_dict(node, parent=None):
        """Convert AST node to dictionary representation, with parent annotation."""
        result = {
            'node_type': type(node).__name__,
            'lineno': getattr(node, 'lineno', None),
            'col_offset': getattr(node, 'col_offset', None),
        }
        if parent is not None:
            result['parent'] = parent
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                result[field] = []
                for item in value:
                    if isinstance(item, ast.AST):
                        child = ast_to_dict(item, result)
                        result[field].append(child)
                    else:
                        result[field].append(item)
            elif isinstance(value, ast.AST):
                child = ast_to_dict(value, result)
                result[field] = child
            else:
                result[field] = value
        return result
    return {
        'module': ast_to_dict(tree),
        'source_lines': source_code.split('\n'),
        'filename': file_path
    }

# Step 3: Load rule metadata from JSON files  
def load_rule_metadata(folder="python_docs"):
    # Look for metadata folder in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder)
    if not os.path.isdir(folder_path):
        print(f"Metadata folder '{folder}' not found in {script_dir}.")
        # Fallback to python_docs if python_docs1 doesn't exist
        folder_path = os.path.join(script_dir, "python_docs")
        if not os.path.isdir(folder_path):
            print(f"Neither '{folder}' nor 'python_docs' folder found in {script_dir}.")
            sys.exit(1)
    rules_meta = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    rules_meta[data["rule_id"]] = data
                    if DEBUG:
                        print(f"[DEBUG] Loaded rule: {data['rule_id']}")
            except Exception as e:
                print(f"Error in file: {file_path}")
                raise  # This will show the error and stop at the bad file
    return rules_meta

# Step 4: Define base rule class
class BaseRule:
    def __init__(self, metadata):
        self.metadata = metadata
    def check(self, ast_tree, filename):
        raise NotImplementedError
    def visit(self, node, findings, filename):
        pass  # Optional: override in rules for visitor pattern

# Python AST visitor utility
def visit_ast_nodes(node, visit_fn, findings, filename, visited=None):
    """Visit all nodes in Python AST structure"""
    if visited is None:
        visited = set()
    
    if isinstance(node, dict):
        # Prevent infinite recursion by tracking visited objects
        node_id = id(node)
        if node_id in visited:
            return
        visited.add(node_id)
        
        # Handle our dictionary representation of AST
        visit_fn(node, findings, filename)
        
        # Process children, but skip parent references and other metadata
        for key, value in node.items():
            if key not in ['lineno', 'col_offset', 'node_type', 'parent']:
                if isinstance(value, dict):
                    visit_ast_nodes(value, visit_fn, findings, filename, visited)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            visit_ast_nodes(item, visit_fn, findings, filename, visited)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict):
                visit_ast_nodes(item, visit_fn, findings, filename, visited)

# Step 6: Rule loader (dynamic)
def load_rules(metadata_map):
    # Use only the PythonGenericRule class for all rules
    return [PythonGenericRule(meta) for meta in metadata_map.values()]

# Step 7: Scanner engine
def scan_file(py_file, rules):
    ast_tree = parse_python_file(py_file)
    # print("\n[DEBUG] Parsed AST for file:")
    # import pprint
    # pprint.pprint(ast_tree)
    if DEBUG:
        # Print Try and ExceptHandler nodes for inspection
        def print_try_except_nodes(node, depth=0):
            if isinstance(node, dict):
                if node.get('node_type') == 'Try':
                    print(f"[DEBUG] Found Try node at line {node.get('lineno')}, col {node.get('col_offset')}")
                    import pprint
                    pprint.pprint(node)
                if node.get('node_type') == 'ExceptHandler':
                    print(f"[DEBUG] Found ExceptHandler node at line {node.get('lineno')}, col {node.get('col_offset')}")
                    import pprint
                    pprint.pprint(node)
                for key, value in node.items():
                    if key not in ['lineno', 'col_offset', 'parent']:
                        print_try_except_nodes(value, depth+1)
            elif isinstance(node, list):
                for item in node:
                    print_try_except_nodes(item, depth+1)
        print_try_except_nodes(ast_tree['module'])
    all_findings = []
    applicable_rules = 0
    
    for rule in rules:
        # Check if rule is applicable before running it
        if not rule.is_applicable(ast_tree):
            continue
            
        applicable_rules += 1
        # Use the check method directly since PythonGenericRule doesn't have a visit method
        findings = rule.check(ast_tree, py_file)
        if DEBUG:
            print(f"[DEBUG] Rule applied: {getattr(rule, 'rule_id', getattr(rule, 'metadata', {}).get('rule_id', 'unknown'))}, findings: {len(findings)}")
            for finding in findings:
                print(f"[DEBUG] Finding: {finding}")
        all_findings.extend(findings)
    
    print(f"Applied {applicable_rules} out of {len(rules)} rules")
    return all_findings

def clean_for_json(obj):
    """Recursively clean an object to make it JSON serializable"""
    if isinstance(obj, dict):
        return {key: clean_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    else:
        return obj

# Step 8: Reporting
if __name__ == "__main__":
    metadata_map = load_rule_metadata()
    # Load all rules, but only apply those that are applicable
    rules = [PythonGenericRule(meta) for meta in metadata_map.values()]
    if DEBUG:
        print(f"[DEBUG] Loaded {len(rules)} total rules. Only applicable rules will be checked for findings.")
    results = scan_file(py_file, rules)
    # Clean up findings for JSON serialization
    cleaned_results = []
    for finding in results:
        if isinstance(finding, dict):
            if 'file' in finding:
                del finding['file']
        cleaned_finding = clean_for_json(finding)
        cleaned_results.append(cleaned_finding)
    results = cleaned_results
    print(f"\nScan Summary for file: {py_file}")
    print(f"Vulnerabilities found: {len(results)}")
    print(json.dumps(results, indent=2))
    # Save output to a detailed report file with summary
    base_name = os.path.splitext(os.path.basename(py_file))[0]
    report_file = os.path.join(test_folder, f"{base_name}_report.json")
    report_data = {
        "file_scanned": py_file,
        "vulnerabilities_found": len(results),
        "findings": results
    }
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"Detailed report saved to: {report_file}")
    print(f"Number of rules loaded: {len(rules)}")



'''
import sys
import os
import ast
import json
from python_generic_rule import PythonGenericRule
import inspect
import traceback

# Step 1: Input Handling (scan test folder for .py files)
test_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
if not os.path.isdir(test_folder):
    print(f"Test folder '{test_folder}' not found.")
    sys.exit(1)
py_files = [f for f in os.listdir(test_folder) if f.endswith(".py")]
if not py_files:
    print(f"No .py files found in test folder '{test_folder}'.")
    sys.exit(1)
print("Available test scripts:")
for idx, fname in enumerate(py_files, 1):
    print(f"  {idx}. {fname}")
choice = input("Select a test script to scan (number): ").strip()
try:
    py_file = os.path.join(test_folder, py_files[int(choice)-1])
except Exception:
    print("Invalid selection.")
    sys.exit(1)

def parse_python_file(file_path):
    """Parse Python file into AST and convert to dictionary structure for rule processing"""
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    try:
        tree = ast.parse(source_code, filename=file_path)
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        sys.exit(1)
    
    def ast_to_dict(node, parent=None):
        """Convert AST node to dictionary representation, with parent annotation."""
        result = {
            'node_type': type(node).__name__,
            'lineno': getattr(node, 'lineno', None),
            'col_offset': getattr(node, 'col_offset', None),
        }
        if parent is not None:
            result['parent'] = parent
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                result[field] = []
                for item in value:
                    if isinstance(item, ast.AST):
                        child = ast_to_dict(item, result)
                        result[field].append(child)
                    else:
                        result[field].append(item)
            elif isinstance(value, ast.AST):
                child = ast_to_dict(value, result)
                result[field] = child
                if isinstance(node, ast.Call) and field == 'func':
                    if isinstance(value, ast.Attribute):
                        result['func'] = {
                            'attr': value.attr,
                            'value': ast_to_dict(value.value, result)
                        }
                    if isinstance(node, ast.Call):
                        result['args'] = []
                        for arg in node.args:
                            if isinstance(arg, ast.Constant):
                                result['args'].append({
                                    'node_type': 'Constant',
                                    'value': arg.value,
                                    'parent': result
                                })
                            else:
                                result['args'].append(ast_to_dict(arg, result))
            else:
                result[field] = value
        return result
    
    return {
        'module': ast_to_dict(tree),
        'source_lines': source_code.split('\n'),
        'filename': file_path
    }

def load_rule_metadata(folder="python_docs"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder)
    if not os.path.isdir(folder_path):
        folder_path = os.path.join(script_dir, "python_docs")
        if not os.path.isdir(folder_path):
            print(f"Neither '{folder}' nor 'python_docs' folder found in {script_dir}.")
            sys.exit(1)
    rules_meta = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    rules_meta[data["rule_id"]] = data
            except Exception as e:
                print(f"Error in file: {file_path}")
                raise
    return rules_meta

def scan_file(py_file, rules):
    # Debug: Print the value of ['args', 0, 'value'] for every Call node
    def print_call_arg_values(node):
        if isinstance(node, dict) and node.get('node_type') == 'Call':
            args = node.get('args', [])
            if args and isinstance(args[0], dict):
                print(f"[DEBUG] Call node at line {node.get('lineno')}, col {node.get('col_offset')}: args[0]['value'] = {args[0].get('value')}")
        if isinstance(node, dict):
            for key, value in node.items():
                if key not in ['lineno', 'col_offset', 'parent']:
                    print_call_arg_values(value)
        elif isinstance(node, list):
            for item in node:
                print_call_arg_values(item)

    ast_tree = parse_python_file(py_file)
    code_tree = ast_tree.get('module', ast_tree)
    print_call_arg_values(code_tree)
    all_findings = []
    processed_nodes = set()  # Track processed nodes
    processed_findings = set()  # Track unique findings
    applicable_rules = 0

    def recursive_rule_check(node, rule, filename):
        findings = []
        # Create node identifier for deduplication
        if isinstance(node, dict):
            node_id = (
                node.get('node_type'),
                node.get('lineno'),
                node.get('col_offset'),
                rule.rule_id
            )
            if node_id in processed_nodes:
                return []
            processed_nodes.add(node_id)

            # Let the rule evaluate its logic conditions
            if rule.is_applicable(node):
                rule_findings = rule.check(node, filename)
                if rule_findings:
                    for finding in rule_findings:
                        finding_id = (
                            finding.get('rule_id'),
                            finding.get('line'),
                            finding.get('column')
                        )
                        if finding_id not in processed_findings:
                            processed_findings.add(finding_id)
                            findings.append(finding)
            # Process child nodes
            for key, value in node.items():
                if key not in ['lineno', 'col_offset']:
                    if isinstance(value, (dict, list)):
                        findings.extend(recursive_rule_check(value, rule, filename))
        elif isinstance(node, list):
            for item in node:
                findings.extend(recursive_rule_check(item, rule, filename))
        return findings

    # Apply all rules and count how many triggered
    for rule in rules:
        findings = recursive_rule_check(code_tree, rule, py_file)
        if findings:
            applicable_rules += 1
        all_findings.extend(findings)

    print(f"Applied {applicable_rules} out of {len(rules)} rules.")
    print(f"Total findings: {len(all_findings)}")
    return all_findings

if __name__ == "__main__":
    metadata_map = load_rule_metadata()
    rules = [PythonGenericRule(meta) for meta in metadata_map.values()]
    
    results = scan_file(py_file, rules)
    
    # Clean up findings for JSON serialization
    cleaned_results = []
    for finding in results:
        if isinstance(finding, dict):
            if 'file' in finding:
                del finding['file']
        cleaned_results.append(finding)
    
    # Save output to a detailed report file with summary
    base_name = os.path.splitext(os.path.basename(py_file))[0]
    report_file = os.path.join(test_folder, f"{base_name}_report.json")
    report_data = {
        "file_scanned": py_file,
        "vulnerabilities_found": len(cleaned_results),
        "findings": cleaned_results
    }
    
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nScan Summary for file: {py_file}")
    print(f"Vulnerabilities found: {len(cleaned_results)}")
    print(json.dumps(cleaned_results, indent=2))
    print(f"Detailed report saved to: {report_file}")
    print(f"Number of rules loaded: {len(rules)}")
    '''