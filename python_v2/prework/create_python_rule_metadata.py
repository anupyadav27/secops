import os
import json

# Metadata template with placeholders
metadata_template = {
    "rule_id": "{rule_id}",
    "title": "{title}",
    "type": "{type}",
    "status": "{status}",
    "defaultSeverity": "{defaultSeverity}",
    "description": "<DETAILED_RULE_DESCRIPTION>",
    "message": "<ISSUE_MESSAGE>",
    "remediation": {
        "func": "Constant/Issue",
        "constantCost": "5min"
    },
    "tags": [],
    "impact": "<IMPACT_OF_ISSUE>",
    "recommendation": "<RECOMMENDATION_TO_FIX>",
    "references": [],
    "examples": {
        "noncompliant": [
            {
                "code": "<NONCOMPLIANT_CODE_EXAMPLE>",
                "description": "<WHY_THIS_IS_NONCOMPLIANT>"
            }
        ],
        "compliant": [
            {
                "code": "<COMPLIANT_CODE_EXAMPLE>",
                "description": "<WHY_THIS_IS_COMPLIANT>"
            }
        ]
    },
    "devsecops": {
        "category": "<CATEGORY>",
        "security": "<SECURITY_IMPACT>",
        "automation": "<AUTOMATION_IMPACT>",
        "compliance": "<COMPLIANCE_IMPACT>"
    },
    "why_is_this_an_issue": "<WHY_IS_THIS_AN_ISSUE>",
    "how_to_fix": "<HOW_TO_FIX_THIS_ISSUE>",
    "security_mappings": {
        "CWE": "<CWE_ID_OR_DESCRIPTION>",
        "CERT": "<CERT_GUIDANCE_REFERENCE>",
        "OWASP": "<OWASP_CATEGORY_OR_REFERENCE>"
    },
    "logic": {}  # Will be filled from each rule file
}

rules_folder = r'd:/task10/python_rules/'
docs_folder = r'd:/task10/python_docs/'

for filename in os.listdir(rules_folder):
    if filename.endswith('.json'):
        rule_path = os.path.join(rules_folder, filename)
        with open(rule_path, 'r', encoding='utf-8') as f:
            try:
                rule_data = json.load(f)
            except Exception as e:
                print(f'[ERROR] {filename}: {e}')
                continue
        # Fill template fields from rule file
        meta = metadata_template.copy()
        for key in ["rule_id", "title", "type", "status", "defaultSeverity", "tags"]:
            if key in rule_data:
                meta[key] = rule_data[key]
        # Fill logic section if present
        if 'logic' in rule_data:
            meta['logic'] = rule_data['logic']
        else:
            meta['logic'] = {}
        # References and tags if present
        if 'references' in rule_data:
            meta['references'] = rule_data['references']
        if 'tags' in rule_data:
            meta['tags'] = rule_data['tags']
        # Save metadata file
        meta_filename = os.path.splitext(filename)[0] + '_metadata.json'
        meta_path = os.path.join(docs_folder, meta_filename)
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(f'[CREATED] {meta_filename}')
print('\nDone creating metadata files.')
