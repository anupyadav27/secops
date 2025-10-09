#!/usr/bin/env python3
"""
Debug script to check if the assertions rule is being loaded
"""
import os
import json

def load_rule_metadata(folder="python_docs"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.join(script_dir, folder)
    if not os.path.isdir(folder_path):
        print(f"Metadata folder '{folder}' not found in {script_dir}.")
        return {}
    
    rules_meta = {}
    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)
                    rules_meta[data["rule_id"]] = data
                    if "assertions_should_not_fail_or_succeed_unconditionally" in data["rule_id"]:
                        print(f"Found assertions rule in {filename}")
                        print(f"Logic: {json.dumps(data['logic'], indent=2)}")
            except Exception as e:
                print(f"[RULE LOAD ERROR] Skipped file: {file_path}\nReason: {e}\n")
    
    print(f"Total rules loaded: {len(rules_meta)}")
    if "assertions_should_not_fail_or_succeed_unconditionally" in rules_meta:
        print("Assertions rule successfully loaded!")
    else:
        print("Assertions rule NOT found in loaded rules!")
        print("Available rules:")
        for rule_id in sorted(rules_meta.keys()):
            if "assert" in rule_id.lower():
                print(f"  - {rule_id}")
    
    return rules_meta

if __name__ == "__main__":
    load_rule_metadata()