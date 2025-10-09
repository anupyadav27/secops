#!/usr/bin/env python3
"""
Auto-populate logic sections in Python rule metadata files.

This script analyzes rule IDs and generates appropriate logic sections
based on common patterns and naming conventions.
"""

import os
import json
import re
from typing import Dict, List, Any

class LogicGenerator:
    """Generate logic sections for Python rules based on rule patterns."""
    
    def __init__(self):
        self.patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize rule patterns for automatic logic generation."""
        return {
            # Security patterns
            "hardcoded_password": {
                "keywords": ["password", "pwd", "secret", "key", "token", "hardcoded"],
                "logic": {
                    "node_type": ["Assign"],
                    "property_path": ["targets.*.id"],
                    "check_type": "regex",
                    "regex": ".*(password|pwd|secret|key|token).*"
                }
            },
            "hardcoded_ip": {
                "keywords": ["ip", "address", "hardcoded"],
                "logic": {
                    "node_type": ["Constant", "Str"],
                    "property_path": ["value"],
                    "check_type": "regex",
                    "regex": "\\b(?:[0-9]{1,3}\\.){3}[0-9]{1,3}\\b"
                }
            },
            "cleartext_protocol": {
                "keywords": ["cleartext", "protocol", "http", "ftp", "telnet"],
                "logic": {
                    "node_type": ["Constant", "Str"],
                    "property_path": ["value"],
                    "check_type": "contains",
                    "forbidden_values": ["http://", "ftp://", "telnet://"]
                }
            },
            
            # Type hint patterns
            "any_type_hint": {
                "keywords": ["any", "type", "hint"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef", "AnnAssign"],
                    "property_path": ["args.args.*.annotation.id", "returns.id", "annotation.id"],
                    "check_type": "contains",
                    "forbidden_values": ["Any"]
                }
            },
            "union_type": {
                "keywords": ["union", "type", "expression"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef", "AnnAssign"],
                    "property_path": ["args.args.*.annotation.id", "returns.id", "annotation.id"],
                    "check_type": "contains",
                    "forbidden_values": ["Union"]
                }
            },
            
            # Function/method patterns
            "empty_function": {
                "keywords": ["empty", "function", "method"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef"],
                    "property_path": ["body"],
                    "check_type": "custom",
                    "custom_function": "check_empty_function"
                }
            },
            "too_many_parameters": {
                "keywords": ["parameter", "many", "function", "method"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef"],
                    "property_path": ["args.args"],
                    "check_type": "min_value",
                    "required_values": [7]  # More than 6 parameters
                }
            },
            "return_type_hint": {
                "keywords": ["return", "type", "hint"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef"],
                    "property_path": ["returns"],
                    "check_type": "required_present"
                }
            },
            
            # Naming convention patterns
            "function_naming": {
                "keywords": ["function", "name", "convention"],
                "logic": {
                    "node_type": ["FunctionDef", "AsyncFunctionDef"],
                    "property_path": ["name"],
                    "check_type": "regex",
                    "regex": "^[a-z][a-z0-9_]*$"
                }
            },
            "class_naming": {
                "keywords": ["class", "name", "convention"],
                "logic": {
                    "node_type": ["ClassDef"],
                    "property_path": ["name"],
                    "check_type": "regex",
                    "regex": "^[A-Z][a-zA-Z0-9]*$"
                }
            },
            "variable_naming": {
                "keywords": ["variable", "name", "convention", "local"],
                "logic": {
                    "node_type": ["Assign"],
                    "property_path": ["targets.*.id"],
                    "check_type": "regex",
                    "regex": "^[a-z][a-z0-9_]*$"
                }
            },
            
            # Code quality patterns
            "constant_condition": {
                "keywords": ["constant", "condition"],
                "logic": {
                    "node_type": ["If", "While"],
                    "property_path": ["test.value"],
                    "check_type": "contains",
                    "forbidden_values": [True, False]
                }
            },
            "assertion_unconditional": {
                "keywords": ["assertion", "assert", "unconditional", "fail", "succeed"],
                "logic": {
                    "node_type": ["Assert"],
                    "property_path": ["test.value"],
                    "check_type": "contains",
                    "forbidden_values": [True, False]
                }
            },
            "duplicate_key": {
                "keywords": ["duplicate", "key", "dictionary"],
                "logic": {
                    "node_type": ["Dict"],
                    "property_path": ["keys"],
                    "check_type": "custom",
                    "custom_function": "check_duplicate_keys"
                }
            },
            
            # Import patterns
            "wildcard_import": {
                "keywords": ["wildcard", "import"],
                "logic": {
                    "node_type": ["ImportFrom"],
                    "property_path": ["names.*.name"],
                    "check_type": "contains",
                    "forbidden_values": ["*"]
                }
            },
            "unused_import": {
                "keywords": ["unused", "import"],
                "logic": {
                    "node_type": ["Import", "ImportFrom"],
                    "property_path": ["names.*.name"],
                    "check_type": "custom",
                    "custom_function": "check_unused_imports"
                }
            },
            
            # Exception handling patterns
            "bare_except": {
                "keywords": ["bare", "except", "exception"],
                "logic": {
                    "node_type": ["ExceptHandler"],
                    "property_path": ["type"],
                    "check_type": "forbidden_empty"
                }
            },
            "exception_inheritance": {
                "keywords": ["exception", "inherit", "baseexception"],
                "logic": {
                    "node_type": ["ClassDef"],
                    "property_path": ["bases.*.id"],
                    "check_type": "contains",
                    "required_values": ["Exception", "BaseException"]
                }
            },
            
            # Async patterns
            "async_input": {
                "keywords": ["async", "input"],
                "logic": {
                    "node_type": ["AsyncFunctionDef"],
                    "property_path": ["body.*.value.func.id"],
                    "check_type": "contains",
                    "forbidden_values": ["input"]
                }
            },
            "async_sleep": {
                "keywords": ["async", "sleep"],
                "logic": {
                    "node_type": ["AsyncFunctionDef"],
                    "property_path": ["body.*.value.func.attr"],
                    "check_type": "contains",
                    "forbidden_values": ["sleep"]
                }
            },
            
            # TODO/FIXME patterns
            "todo_comment": {
                "keywords": ["todo", "fixme", "comment"],
                "logic": {
                    "node_type": ["*"],
                    "property_path": ["*"],
                    "check_type": "custom",
                    "custom_function": "flag_todo_comments"
                }
            }
        }
    
    def analyze_rule_id(self, rule_id: str) -> Dict[str, Any]:
        """Analyze rule ID and generate appropriate logic."""
        rule_id_lower = rule_id.lower()
        
        # Score each pattern based on keyword matches
        pattern_scores = {}
        for pattern_name, pattern_data in self.patterns.items():
            score = 0
            keywords = pattern_data["keywords"]
            for keyword in keywords:
                if keyword in rule_id_lower:
                    score += 1
            if score > 0:
                pattern_scores[pattern_name] = score
        
        # Return the pattern with highest score
        if pattern_scores:
            best_pattern = max(pattern_scores.keys(), key=lambda k: pattern_scores[k])
            return self.patterns[best_pattern]["logic"].copy()
        
        # Default fallback logic
        return {
            "node_type": ["*"],
            "property_path": ["*"],
            "check_type": "custom",
            "custom_function": "check_general_rule"
        }
    
    def generate_logic_for_rule(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate logic section for a rule metadata."""
        rule_id = metadata.get("rule_id", "")
        
        # Check if logic already exists and is not empty
        existing_logic = metadata.get("logic", {})
        if existing_logic and len(existing_logic) > 0:
            return existing_logic
        
        # Generate new logic based on rule ID
        generated_logic = self.analyze_rule_id(rule_id)
        
        # Add rule-specific customizations
        generated_logic = self._customize_logic(rule_id, generated_logic, metadata)
        
        return generated_logic
    
    def _customize_logic(self, rule_id: str, logic: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule-specific customizations to generated logic."""
        rule_id_lower = rule_id.lower()
        
        # Security-specific customizations
        if "security" in metadata.get("type", "").lower():
            if "severity" not in logic:
                logic["severity"] = "high"
        
        # Framework-specific patterns
        if "django" in rule_id_lower:
            logic["framework"] = "django"
        elif "flask" in rule_id_lower:
            logic["framework"] = "flask"
        elif "numpy" in rule_id_lower or "pandas" in rule_id_lower:
            logic["framework"] = "data_science"
        elif "aws" in rule_id_lower or "boto" in rule_id_lower:
            logic["framework"] = "aws"
        
        # Adjust severity based on rule type
        rule_type = metadata.get("type", "").lower()
        if rule_type == "security_hotspot":
            logic["priority"] = "high"
        elif rule_type == "bug":
            logic["priority"] = "medium"
        elif rule_type == "code_smell":
            logic["priority"] = "low"
        
        return logic
    
    def process_metadata_file(self, file_path: str) -> bool:
        """Process a single metadata file and add logic section."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Generate logic section
            new_logic = self.generate_logic_for_rule(metadata)
            
            # Update metadata
            metadata["logic"] = new_logic
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Updated: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"✗ Error processing {file_path}: {e}")
            return False
    
    def process_directory(self, directory_path: str) -> Dict[str, int]:
        """Process all metadata files in a directory."""
        stats = {"processed": 0, "updated": 0, "errors": 0, "skipped": 0}
        
        if not os.path.isdir(directory_path):
            print(f"Directory not found: {directory_path}")
            return stats
        
        json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
        
        print(f"Found {len(json_files)} metadata files in {directory_path}")
        
        for filename in json_files:
            file_path = os.path.join(directory_path, filename)
            stats["processed"] += 1
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                # Check if logic already exists
                existing_logic = metadata.get("logic", {})
                if existing_logic and len(existing_logic) > 0:
                    print(f"- Skipped: {filename} (logic already exists)")
                    stats["skipped"] += 1
                    continue
                
                # Process the file
                if self.process_metadata_file(file_path):
                    stats["updated"] += 1
                else:
                    stats["errors"] += 1
                    
            except Exception as e:
                print(f"✗ Error with {filename}: {e}")
                stats["errors"] += 1
        
        return stats


def main():
    """Main function to run the logic generator."""
    import sys
    
    # Default directory
    default_dir = os.path.join(os.path.dirname(__file__), "python_docs")
    
    # Get directory from command line or use default
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = default_dir
    
    print(f"Auto-populating logic sections in: {directory}")
    print("=" * 60)
    
    generator = LogicGenerator()
    stats = generator.process_directory(directory)
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"Total files processed: {stats['processed']}")
    print(f"Files updated: {stats['updated']}")
    print(f"Files skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    
    if stats['updated'] > 0:
        print(f"\n✓ Successfully updated {stats['updated']} metadata files!")
        print("You can now run the Python scanner to test the rules.")
    else:
        print("\n! No files were updated. All files may already have logic sections.")


if __name__ == "__main__":
    main()