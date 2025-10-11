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

if __name__ == "__main__":
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
        # print(f"Syntax error in {file_path}: {e}")
        sys.exit(1)
    # Convert AST to a dictionary structure similar to Terraform
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

# Step 3: Load rule metadata from JSON files  
def load_rule_metadata(folder="python_docs"):
    # Look for metadata folder in the same directory as the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder)
    if not os.path.isdir(folder_path):
        # print(f"Metadata folder '{folder}' not found in {script_dir}.")
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
                # print(f"[RULE LOAD ERROR] Skipped file: {file_path}\nReason: {e}\n")
                # continue loading other files
                continue
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
def visit_ast_nodes(node, visit_fn, findings, filename, parent=None):
    """Visit all nodes in Python AST structure, annotating with parent."""
    if isinstance(node, dict):
        node['__parent__'] = parent
        visit_fn(node, findings, filename)
        for key, value in node.items():
            if key not in ['lineno', 'col_offset', 'node_type', '__parent__']:
                visit_ast_nodes(value, visit_fn, findings, filename, node)
    elif isinstance(node, list):
        for item in node:
            visit_ast_nodes(item, visit_fn, findings, filename, parent)

# Step 6: Rule loader (dynamic)
def load_rules(metadata_map):
    # Use only the PythonGenericRule class for all rules
    return [PythonGenericRule(meta) for meta in metadata_map.values()]

# Step 7: Scanner engine
def scan_file(py_file, rules):
    # print(f"\n[DEBUG] Scanning file {py_file}")
    ast_tree = parse_python_file(py_file)
    # DEBUG: Print AST structure for troubleshooting
    import pprint
    # print("[DEBUG] AST structure for file:")
    # pprint.pprint(ast_tree['module'], width=120, compact=True)
    all_findings = []
    applicable_rules = 0
    
    # First pass - determine which rules are applicable
    applicable_rule_list = []
    for rule in rules:
        #print(f"\n[DEBUG] Checking applicability of rule {rule.rule_id}")
        try:
            if rule.is_applicable(ast_tree):
                applicable_rules += 1
                applicable_rule_list.append(rule)
                # print(f"[DEBUG] Rule {rule.rule_id} is applicable")
            else:
                # print(f"Rule {rule.metadata.get('rule_id')} not applicable")
                pass
        except Exception as e:
            # print(f"Error checking applicability for rule {rule.metadata.get('rule_id')}: {e}")
            continue
    
    # Second pass - apply applicable rules
    for rule in applicable_rule_list:
        try:
            findings = []
            custom_function_name = None
            if isinstance(rule.logic.get('checks'), list):
                for check in rule.logic.get('checks', []):
                    if check.get('type') == 'custom_function':
                        custom_function_name = check.get('function')
                        break

            custom_function = rule._get_custom_function(custom_function_name)
            if custom_function:
                node_types = rule.logic.get('node_types', [])
                def check_node(node, findings, filename):
                    if isinstance(node, dict):
                        # If node_types is specified, only check those node types
                        if node_types:
                            if node.get('node_type') not in node_types:
                                return
                        try:
                            # print(f"[DEBUG][scanner] Checking node: {node.get('node_type')}, line: {node.get('lineno')}")
                            if custom_function(node):
                                finding = {
                                    "rule_id": rule.rule_id,
                                    "message": rule.message,
                                    "file": filename,
                                    "line": node.get('lineno', 0),
                                    "status": "violation"
                                }
                                findings.append(finding)
                        except Exception as e:
                            # print(f"[DEBUG] Error in custom function for {rule.rule_id} on node: {e}")
                            pass
                visit_ast_nodes(ast_tree.get('module', {}), check_node, findings, py_file)
            else:
                if hasattr(rule, 'visit') and callable(getattr(rule, 'visit')):
                    visit_ast_nodes(ast_tree, rule.visit, findings, py_file)
                else:
                    try:
                        findings_from_check = rule.check(ast_tree, py_file)
                        # print(f"[DEBUG] Rule {rule.rule_id} check() returned {len(findings_from_check)} findings.")
                        if rule.rule_id == "assertions_should_not_fail_or_succeed_unconditionally":
                            # print(f"[DEBUG] Assertions rule findings: {json.dumps(findings_from_check, indent=2)}")
                            pass
                        findings.extend(findings_from_check)
                    except RecursionError as re:
                        # print(f"[RECURSION ERROR] Rule {rule.rule_id} raised RecursionError: {re}")
                        # Optionally print a small snippet of the AST or property_path here
                        continue
                    except Exception as e:
                        # print(f"[ERROR] Rule {rule.rule_id} raised exception: {e}")
                        continue
            if findings:
                # print(f"[DEBUG] Adding {len(findings)} findings for rule {rule.rule_id} to all_findings.")
                all_findings.extend(findings)
        except Exception as e:
            # print(f"[DEBUG] Error applying rule {rule.metadata.get('rule_id')}: {e}")
            continue
    
    # print(f"Applied {applicable_rules} out of {len(rules)} rules")
    return all_findings

def clean_for_json(obj, depth=0, max_depth=10):
    """Recursively clean an object to make it JSON serializable, with depth limit"""
    if depth > max_depth:
        return f"<Max depth {max_depth} reached>"
    if isinstance(obj, dict):
        # Remove __parent__ if present
        obj = {k: v for k, v in obj.items() if k != '__parent__'}
        return {key: clean_for_json(value, depth+1, max_depth) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [clean_for_json(item, depth+1, max_depth) for item in obj]
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='replace')
    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    else:
        return obj

# Step 8: Reporting
if __name__ == "__main__":
    metadata_map = load_rule_metadata()
    # print(f"\nNumber of rule metadata files loaded: {len(metadata_map)}")
    rules = load_rules(metadata_map)
    results = scan_file(py_file, rules)
    
    # Clean up findings for JSON serialization
    cleaned_results = []
    for finding in results:
        if isinstance(finding, dict):
            # Remove fields that may contain cyclic references
            for key in ['file', 'node', '__parent__']:
                if key in finding:
                    del finding[key]
        cleaned_finding = clean_for_json(finding, max_depth=10)
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
