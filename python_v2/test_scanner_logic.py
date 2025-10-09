#!/usr/bin/env python3
"""
Quick test to run the assertions rule through the main scanner logic
"""
import sys
import os
import ast
import json
from python_generic_rule import PythonGenericRule

# Parse the test file (simplified version of what scanner does)
test_file = "test/test_assertions_should_not_fail_or_succeed_unconditionally_trigger.py"

def parse_python_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    tree = ast.parse(source_code, filename=file_path)
    
    def ast_to_dict(node):
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
    
    return {
        'module': ast_to_dict(tree),
        'source_lines': source_code.split('\\n'),
        'filename': file_path
    }

# Load rule metadata
def load_rule_metadata(folder="python_docs"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder)
    rules_meta = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    rules_meta[data["rule_id"]] = data
            except Exception as e:
                print(f"[RULE LOAD ERROR] Skipped file: {file_path}\\nReason: {e}\\n")
    return rules_meta

print("Step 1: Loading rules...")
rules_meta = load_rule_metadata()
print(f"Loaded {len(rules_meta)} rules")

print("Step 2: Creating rule objects...")
rules = []
for rule_id, metadata in rules_meta.items():
    try:
        rule = PythonGenericRule(metadata)
        rules.append(rule)
        if rule_id == "assertions_should_not_fail_or_succeed_unconditionally":
            print(f"  ✓ Found assertions rule: {rule_id}")
    except Exception as e:
        print(f"  ✗ Failed to create rule {rule_id}: {e}")

print(f"Created {len(rules)} rule objects")

print("Step 3: Parsing test file...")
ast_tree = parse_python_file(test_file)

print("Step 4: Finding applicable rules...")
applicable_rules = []
for rule in rules:
    try:
        if rule.is_applicable(ast_tree):
            applicable_rules.append(rule)
            if rule.rule_id == "assertions_should_not_fail_or_succeed_unconditionally":
                print(f"  ✓ Assertions rule is applicable")
    except Exception as e:
        if rule.rule_id == "assertions_should_not_fail_or_succeed_unconditionally":
            print(f"  ✗ Error checking applicability for assertions rule: {e}")

print(f"Found {len(applicable_rules)} applicable rules")

print("Step 5: Applying rules...")
all_findings = []
for rule in applicable_rules:
    if rule.rule_id == "assertions_should_not_fail_or_succeed_unconditionally":
        print(f"  Applying assertions rule...")
        try:
            findings = rule.check(ast_tree, test_file)
            print(f"  ✓ Assertions rule found {len(findings)} violations")
            all_findings.extend(findings)
        except Exception as e:
            print(f"  ✗ Error applying assertions rule: {e}")
            import traceback
            traceback.print_exc()

print(f"Step 6: Total findings: {len(all_findings)}")
assertions_findings = [f for f in all_findings if f.get('rule_id') == 'assertions_should_not_fail_or_succeed_unconditionally']
print(f"Assertions rule findings: {len(assertions_findings)}")