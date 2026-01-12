# Python Code Scanner

A comprehensive static code analysis tool for Python that identifies security vulnerabilities, code smells, and potential issues using configurable rules based on industry standards and best practices.

## Overview

The Python Scanner is a rule-based static analysis tool that parses Python code into Abstract Syntax Trees (AST) and applies predefined rules to identify various code quality and security issues. It supports both data-driven rules (configured via JSON metadata) and legacy hard-coded rules.

## Features

- **77+ Built-in Rules**: Comprehensive set of rules covering security, reliability, maintainability, and performance
- **JSON-Configurable Rules**: Easy-to-modify rule definitions using JSON metadata
- **AST-Based Analysis**: Deep code analysis using Python's Abstract Syntax Tree
- **Multiple Output Formats**: JSON reports with detailed findings
- **Flexible Rule Engine**: Support for complex logical conditions (AND/OR operations)
- **Security Mapping**: Integration with industry standards (CWE, OWASP, CERT)

## Project Structure

```
python_scanner/
├── python_scanner_fixed.py     # Main scanner application
├── python_generic_rule.py      # Core rule engine and AST processing
├── check_type_handlers.py      # Rule condition handlers
├── python_docs/                # JSON rule metadata files
│   ├── *.json                  # Individual rule definitions
├── python_rules1/              # Legacy rule definitions (if any)
├── test/                       # Test scripts for validation
│   ├── cipher.py
│   ├── test_bare_raise_in_finally.py
│   └── ...
└── README.md                   # This file
```

## Installation & Setup

### Prerequisites

- Python 3.7 or higher
- Standard Python libraries (ast, json, os, sys, re)

### Quick Start

1. Clone or download the project files
2. Ensure all Python files are in the same directory
3. Run the scanner:

```bash
python python_scanner_fixed.py
```

## Usage

### Interactive Mode

Run the scanner interactively to select test files:

```bash
python python_scanner_fixed.py
```

The scanner will display available test scripts and prompt you to select one:

```
Available test scripts:
  1. cipher.py
  2. test_bare_raise_in_finally.py
  3. test_trigger_latest_rules.py
  4. test_trigger_regex_backref_rule.py
Select a test script to scan (number): 2
```

### Command Line Mode

You can also pipe input to automatically select a test file:

```bash
echo "2" | python python_scanner_fixed.py
```

## Workflow

### 1. Initialization
- Load rule metadata from JSON files in `python_docs/` directory
- Initialize rule instances with their configurations
- Set up the AST parser and rule engine

### 2. File Selection
- Scan the `test/` directory for available Python files
- Present options to user or accept input programmatically
- Load and parse the selected Python file

### 3. AST Generation
- Parse Python source code into Abstract Syntax Tree
- Convert AST nodes into dictionary format for rule processing
- Add metadata like line numbers and column offsets

### 4. Rule Application
- Filter applicable rules based on AST content
- Apply each rule's logic conditions sequentially
- Evaluate complex conditions using AND/OR operators
- Collect violations with detailed location information

### 5. Report Generation
- Compile all findings into structured format
- Include rule metadata, severity levels, and remediation advice
- Generate JSON report with detailed violation information
- Save report to disk with timestamp

## Rule Configuration

### JSON Rule Structure

Each rule is defined in a JSON file with the following structure:

```json
{
  "rule_id": "rule_identifier",
  "title": "Human-readable rule title",
  "type": "CODE_SMELL|BUG|VULNERABILITY|SECURITY_HOTSPOT",
  "defaultSeverity": "Info|Minor|Major|Critical|Blocker",
  "description": "Detailed description of the issue",
  "message": "Message to display when rule is violated",
  "logic": {
    "operator": "and|or",
    "conditions": [
      {
        "check_type": "node_type|property_exists|regex_match|contains",
        "property_path": "path.to.property",
        "value": "expected_value"
      }
    ]
  },
  "security_mappings": {
    "cwe": [{"id": "CWE-XX", "name": "Description"}],
    "owasp": [{"id": "A01:2021", "name": "Category"}]
  }
}
```

### Condition Types

- **node_type**: Matches specific AST node types (e.g., "Call", "FunctionDef")
- **property_exists**: Checks if a property exists in the node
- **regex_match**: Applies regular expression matching to property values
- **contains**: Checks if a property contains specific nested structures

### Example Rules

1. **Bare Raise in Finally Blocks**
   - Detects `raise` statements without arguments in `finally` blocks
   - Severity: Major
   - Security Impact: Can suppress important exceptions

2. **Undefined Variables**
   - Identifies usage of variables before definition
   - Severity: Blocker
   - Common cause of runtime errors

3. **Regex Anchor Grouping**
   - Ensures proper grouping in regular expressions with anchors
   - Severity: Major
   - Prevents unexpected matching behavior

## Output Format

### Console Output
```
Applied 59 out of 77 rules

Scan Summary for file: D:\python_scanner\test\test_bare_raise_in_finally.py
Vulnerabilities found: 70

Number of rules loaded: 77
```

### JSON Report
```json
[
  {
    "rule_id": "bare_raise_statements_should_not_be_used_in_finally_blocks",
    "message": "Bare 'raise' statements should not be used in 'finally' blocks",
    "node": "Raise.anonymous",
    "property_path": [],
    "value": null,
    "status": "violation",
    "line": 12,
    "column": 12,
    "severity": "Major"
  }
]
```

## Architecture

### Core Components

1. **python_scanner_fixed.py**
   - Main application entry point
   - File selection and user interface
   - Report generation and output formatting

2. **python_generic_rule.py**
   - Core rule engine implementation
   - AST processing and traversal
   - Condition evaluation logic
   - Base rule class definitions

3. **check_type_handlers.py**
   - Specific condition type handlers
   - Property path resolution
   - Value matching and comparison logic

### Rule Engine Flow

```
Python Source → AST Parser → Rule Filter → Condition Evaluation → Report Generation
                     ↓              ↓              ↓               ↓
                AST Dictionary → Applicable Rules → Violations → JSON Report
```

### Performance Optimizations

- **Recursive Traversal Protection**: Prevents infinite loops in circular AST references
- **Rule Applicability Filtering**: Only applies relevant rules to reduce processing time
- **Visited Node Tracking**: Avoids reprocessing the same AST nodes
- **Lazy Evaluation**: Conditions are evaluated only when necessary

## Troubleshooting

### Common Issues

1. **UTF-8 BOM Errors**
   - **Problem**: JSON files with Byte Order Mark causing decode errors
   - **Solution**: Files are automatically processed to remove BOM

2. **Recursion Depth Exceeded**
   - **Problem**: Circular references in AST causing infinite recursion
   - **Solution**: Built-in recursion protection using visited node tracking

3. **Missing Rule Files**
   - **Problem**: JSON metadata files not found
   - **Solution**: Verify `python_docs/` directory contains rule definitions

### Debug Mode

To enable verbose output for troubleshooting:

1. Modify `python_scanner_fixed.py` to add debug prints
2. Check rule loading success/failure messages
3. Verify AST generation for problematic files

## Extending the Scanner

### Adding New Rules

1. **Create JSON Metadata**
   - Define rule in `python_docs/new_rule_metadata.json`
   - Follow the standard JSON schema
   - Include appropriate security mappings

2. **Test the Rule**
   - Create test cases in `test/` directory
   - Verify rule triggers correctly
   - Check for false positives/negatives

3. **Custom Condition Types**
   - Extend `check_type_handlers.py` for new condition types
   - Implement handler functions following existing patterns
   - Update rule engine to recognize new types

### Example: Adding a Custom Rule

```json
{
  "rule_id": "no_hardcoded_secrets",
  "title": "Avoid hardcoded secrets in source code",
  "type": "VULNERABILITY",
  "defaultSeverity": "Critical",
  "description": "Hardcoded secrets in source code pose security risks",
  "message": "Remove hardcoded secret from source code",
  "logic": {
    "operator": "and",
    "conditions": [
      {
        "check_type": "node_type",
        "value": "Str"
      },
      {
        "check_type": "regex_match",
        "property_path": "s",
        "value": "^(password|secret|key|token).*[=:].*"
      }
    ]
  }
}
```

## Contributing

1. Fork the repository
2. Create feature branches for new rules or improvements
3. Test thoroughly with various Python code samples
4. Submit pull requests with detailed descriptions
5. Ensure all existing tests continue to pass

## License

This project is available for educational and research purposes. Please review the license terms before commercial use.

## Support

For issues, questions, or contributions:
- Review the troubleshooting section above
- Check existing rule definitions for examples
- Test with simple Python scripts first
- Verify JSON syntax for custom rules

---

**Version**: 1.0  
**Last Updated**: October 2, 2025  
**Python Compatibility**: 3.7+