
import os
from pathlib import Path
import re

RULES_DIR = Path("python_rules")
PROMPTS_DIR = Path("prompts")
PROMPTS_DIR.mkdir(parents=True, exist_ok=True)


# Read rule IDs to regenerate from to_regen.txt
REGEN_LIST_FILE = Path("to_regen.txt")
regen_rule_ids = set()
if REGEN_LIST_FILE.exists():
    with REGEN_LIST_FILE.open("r", encoding="utf-8") as rf:
        for line in rf:
            fname = line.strip()
            if fname:
                # Remove folder and extension, and _raw if present
                base = os.path.basename(fname)
                rule_id = base.replace('_raw.txt', '').replace('.txt', '')
                regen_rule_ids.add(rule_id)
else:
    print(f"No to_regen.txt file found. Please create one with the list of prompt filenames to regenerate.")
    exit(1)

# Load all custom function definitions from logic_implementationsv2.py
LOGIC_FILE = Path("logic_implementationsv2.py")
custom_functions = {}
if LOGIC_FILE.exists():
    with LOGIC_FILE.open("r", encoding="utf-8") as lf:
        logic_code = lf.read()
        # Find all function definitions
        for match in re.finditer(r"def (check_[a-zA-Z0-9_]+)\(node[\w, ]*\):\n([\s\S]+?)(?=\ndef |\Z)", logic_code):
            func_name = match.group(1)
            func_code = f"def {func_name}(node):\n" + match.group(2)
            custom_functions[func_name] = func_code

# reusable prompt template. use {rule_id}, {sonar_url}, and optionally {function_code}
PROMPT_TEMPLATE = """You are an expert in Python static analysis and Sonar-style rule authoring.

Task:
Produce a single JSON object (no extra commentary) that is the metadata for the Sonar rule identified by:
- rule_id: "{rule_id}"
- Sonar page (source): {sonar_url}

Requirements (MANDATORY):
1) Follow exactly this top-level JSON structure (fill fields):
    {{
        "rule_id": "<string>",
        "title": "<string>",
        "type": "CODE_SMELL|BUG|VULNERABILITY",
        "status": "ready",
        "defaultSeverity": "<Major|Minor|Critical|Blocker>",
        "description": "<detailed>",
        "message": "<short message>",
        "remediation": {{ "func": "Constant/Issue", "constantCost": "<e.g. 5min>" }},
        "tags": [ ... ],
        "impact": "<string>",
        "recommendation": "<string>",
        "references": [ ... ],
        "examples": {{
            "noncompliant": [{{ "code": "<code>", "description": "<desc>" }}],
            "compliant": [{{ "code": "<code>", "description": "<desc>" }}]
        }},
        "devsecops": {{ "category":"", "security":"", "automation":"", "compliance":"" }},
        "why_is_this_an_issue": "<string>",
        "how_to_fix": "<string>",
        "security_mappings": {{ "CWE":"", "CERT":"", "OWASP":"" }},
        "logic": {{ /* see below */ }}
        {function_code}
    }}

Logic section rules (CRITICAL):
- Always try to express the rule purely in the "logic" section (node types, property_path(s), check_type, forbidden_values/required_values/regex etc).
- ONLY when it is impossible to define logic that *reliably triggers exactly when vulnerability exists* (critical/complex cases), produce a custom function.
- If you decide to produce a custom function, set:
        "logic": {{
            "check_type": "custom",
            "custom_function": "<function_name>"
        }}
    AND ALSO include a field "function_code" in the same JSON whose value is the full Python function source code (a single function definition) that accepts one AST-node-dict argument `node` and returns True when vulnerability is present.

Additional logic rules:
- Use only the following check types supported by our PythonGenericRule engine:
     - "custom"
     - "equals"
     - "not_contains"
     - "in"
     - "contains"
     - "min_value"
     - "required_present"
     - "regex"
     - "pattern"
     - "forbidden_empty"
     - "property_comparison"
     - (add others from the engine if needed)
- Only introduce a new check type if the rule cannot be reliably expressed with the above. If you create a new check type:
     - Clearly document the new check type in the JSON (field: "logic.new_check_type_doc": "<description>")
     - Output a separate JSON file named `new_check_types_{rule_id}.json` in the folder `python_new_check_types` containing:
         {{
             "rule_id": "{rule_id}",
             "new_check_type": "<name>",
             "description": "<detailed description of logic and intended usage>"
         }}

Strict output rules:
- Output must be *only* the JSON object (no explanatory text).
- If a custom function is required, include "function_code" (the python code) in the JSON so the caller can save it directly.
- property_path values must use the AST-dict keys your scanner uses (node_type, name, value, args, body, etc).
- Examples must be runnable Python snippets (short, 1-8 lines).

Sonar source:
- Use the Sonar rule page to extract the most accurate title, severity, description, examples and remediation.
- If the Sonar page has an official rule-id, include it in rule_id.

{extra_instruction}
"""

# optional extra instruction to ensure conservative custom function creation:
EXTRA_INSTRUCTION = ("Important: prefer a logic section. Create a custom function only if "
                     "you cannot create logic that will only trigger on real vulnerabilities. "
                     "If you create a custom function, make it minimal, well-documented, and safe.")

for f in RULES_DIR.iterdir():

    if f.is_file() and f.suffix in {".txt", ".md", ".rule", ".yaml", ".yml", ".json"}:
        rule_id = f.stem
        # Only generate prompt if rule_id is in regen_rule_ids
        if rule_id not in regen_rule_ids:
            continue
        sonar_url = f"https://rules.sonarsource.com/python/{rule_id}"
        # Try to find a custom function for this rule
        func_name = f"check_{rule_id}"
        function_code = ""
        if func_name in custom_functions:
            # Insert function_code field in the prompt
            function_code = f',\n    "function_code": """\n{custom_functions[func_name].replace('"', '\"')}\n"""'
        prompt_text = PROMPT_TEMPLATE.format(rule_id=rule_id, sonar_url=sonar_url, extra_instruction=EXTRA_INSTRUCTION, function_code=function_code)
        out = PROMPTS_DIR / f"{rule_id}.txt"
        print(f"Processing: {f} -> {out}")
        out.write_text(prompt_text, encoding="utf-8")

print(f"Prompts written to {PROMPTS_DIR.resolve()}")
