import os
import time
import json
import re
import requests
from pathlib import Path

# CONFIG
PROMPTS_DIR = Path("d:/task10/prompts")
OUT_DIR = Path("d:/task10/python_docs")
NEW_CHECK_TYPE_DIR = Path("d:/task10/python_new_check_types")
NEW_CHECK_TYPE_DIR.mkdir(parents=True, exist_ok=True)
LOGIC_FILE = Path("d:/task10/logic_implementations.py")
OUT_DIR.mkdir(parents=True, exist_ok=True)


# Fill your Mistral AI API key here directly
MISTRAL_API_KEY = "Nf39p6o0u9LMHltqclniNxkUByFgs388"  # <-- Set Mistral AI token directly
if not MISTRAL_API_KEY:
    raise SystemExit("Set MISTRAL_API_KEY in the code or environment before running.")

# Mistral AI free endpoint and headers
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# small helper to extract JSON object from a (possibly fenced) text
def extract_json_from_text(text):
    # 1) If fenced triple backticks present, prefer that block
    fenced = re.search(r"```(?:json|)*\s*(\{.*?\})\s*```", text, flags=re.S)
    if fenced:
        return fenced.group(1)
    # 2) find first balanced JSON object by searching first '{' and attempting parse
    start = text.find('{')
    if start == -1:
        return None
    for end in range(len(text), start, -1):
        candidate = text[start:end]
        try:
            obj = json.loads(candidate)
            return candidate
        except Exception:
            continue
    return None

# idempotent append to logic file (skip if function name exists)
def append_function_idempotent(function_code, function_name):
    LOGIC_FILE.touch(exist_ok=True)
    content = LOGIC_FILE.read_text(encoding="utf-8")
    if re.search(rf"def\s+{re.escape(function_name)}\s*\(", content):
        print(f"[skip] {function_name} already exists in {LOGIC_FILE}")
        return
    with LOGIC_FILE.open("a", encoding="utf-8") as f:
        f.write("\n\n# Auto-generated function for metadata creation\n")
        f.write(function_code.strip() + "\n")
    print(f"[wrote] {function_name} -> {LOGIC_FILE}")

def call_mistral(prompt, max_retries=3, backoff=2.0):
    payload = {
        "model": "mistral-tiny",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    # print("\n[DEBUG] Sending payload to Mistral AI endpoint:")
    # print(json.dumps(payload, indent=2, ensure_ascii=False))
    for attempt in range(max_retries):
        try:
            response = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=60)
            # print(f"[DEBUG] status_code: {response.status_code}")
            # print(f"[DEBUG] response: {response.text}")
            response.raise_for_status()
            data = response.json()
            # Mistral returns output in choices[0]['message']['content']
            if "choices" in data and data["choices"]:
                return data["choices"][0]["message"]["content"]
            else:
                return response.text
        except Exception as e:
            wait = backoff ** attempt
            print(f"[retry] attempt={attempt} error={e} waiting {wait}s")
            time.sleep(wait)
    raise SystemExit("Mistral AI API failed after retries")

# main loop
prompt_files = sorted(PROMPTS_DIR.glob("*.txt"))
total_files = len(prompt_files)
if total_files == 0:
    print("No prompt files found. Nothing was processed.")
else:
    batch_size = 3
    failed_prompts = []
    skipped_prompts = []
    for batch_start in range(0, total_files, batch_size):
        batch = prompt_files[batch_start:batch_start + batch_size]
        print(f"\nProcessing batch {batch_start//batch_size+1} ({len(batch)} prompts)")
        batch_results = []
        for prompt_path in batch:
            rule_id = prompt_path.stem
            print(f"\n--- Processing {rule_id} ---")
            prompt_text = prompt_path.read_text(encoding="utf-8")
            try:
                raw_resp = call_mistral(prompt_text)
            except Exception as e:
                print(f"[FAILED] {rule_id}: API error: {e}")
                batch_results.append({"file": rule_id, "status": "failed", "detail": f"API error: {e}"})
                failed_prompts.append(prompt_path)
                continue

            # Attempt to extract JSON
            json_text = extract_json_from_text(raw_resp)
            if not json_text:
                print(f"[FAILED] {rule_id}: Could not extract JSON. Raw output saved.")
                (OUT_DIR / f"{rule_id}_raw.txt").write_text(raw_resp, encoding="utf-8")
                batch_results.append({"file": rule_id, "status": "failed", "detail": "Could not extract JSON. Raw output saved."})
                failed_prompts.append(prompt_path)
                continue

            try:
                metadata = json.loads(json_text)
            except Exception as e:
                print(f"[FAILED] {rule_id}: JSON parsing failed: {e}. Raw output saved.")
                (OUT_DIR / f"{rule_id}_raw.txt").write_text(raw_resp, encoding="utf-8")
                batch_results.append({"file": rule_id, "status": "failed", "detail": f"JSON parsing failed: {e}. Raw output saved."})
                failed_prompts.append(prompt_path)
                continue

            # Save metadata JSON
            out_file = OUT_DIR / f"{rule_id}.json"
            out_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[SUCCESS] {rule_id}: Saved to {out_file}")
            batch_results.append({"file": rule_id, "status": "success", "detail": f"Saved to {out_file}"})

            # Check for new check type in metadata and save to separate folder if present
            logic = metadata.get("logic", {})
            if "new_check_type_doc" in logic and "check_type" in logic:
                new_check_type_doc = logic["new_check_type_doc"]
                new_check_type_name = logic["check_type"]
                new_check_type_json = {
                    "rule_id": rule_id,
                    "new_check_type": new_check_type_name,
                    "description": new_check_type_doc
                }
                new_file_path = NEW_CHECK_TYPE_DIR / f"new_check_types_{rule_id}.json"
                new_file_path.write_text(json.dumps(new_check_type_json, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"[NEW CHECK TYPE] {rule_id}: Saved new check type documentation to {new_file_path}")

            # If logic says custom, handle function code
            check_type = (logic.get("check_type") or "").lower()
            if check_type in ("custom", "generic_function"):
                func_name = logic.get("custom_function") or logic.get("function") or f"{rule_id}_check"
                func_code = metadata.get("function_code")
                if not func_code:
                    match = re.search(r"```(?:python)?\s*(def\s+%s\([^)]*\):[\s\S]+?)```" % re.escape(func_name), raw_resp, flags=re.I)
                    if match:
                        func_code = match.group(1)
                    else:
                        match2 = re.search(r"```(?:python)?\s*(def\s+[a-zA-Z0-9_]+\s*\([^)]+\):[\s\S]+?)```", raw_resp, flags=re.I)
                        if match2:
                            func_code = match2.group(1)
                if func_code:
                    append_function_idempotent(func_code, func_name)
                    metadata["logic"]["custom_function"] = func_name
                    out_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
                    print(f"[SUCCESS] {rule_id}: Custom function '{func_name}' saved.")
                    batch_results[-1]["detail"] += f"; Custom function '{func_name}' saved."
                else:
                    stub = f"def {func_name}(node):\n    \"\"\"Auto-generated STUB for {rule_id}. Implement detection logic here.\"\"\"\n    # TODO: implement detection that returns True when vulnerability exists\n    return False\n"
                    append_function_idempotent(stub, func_name)
                    print(f"[SKIPPED] {rule_id}: No function code returned. Stub created.")
                    batch_results[-1]["status"] = "skipped"
                    batch_results[-1]["detail"] += "; No function code returned. Stub created."
                    skipped_prompts.append(prompt_path)
        print(f"\nBatch {batch_start//batch_size+1} results:")
        for result in batch_results:
            print(f"  [{result['status'].upper()}] {result['file']}: {result['detail']}")

    # Retry only failed/skipped prompts that do NOT already have a corresponding output file
    if failed_prompts or skipped_prompts:
        print("\nRetrying only failed and skipped prompts that have not been created...")
        retry_prompts = list(set(failed_prompts + skipped_prompts))
        for prompt_path in retry_prompts:
            rule_id = prompt_path.stem
            out_file = OUT_DIR / f"{rule_id}.json"
            if out_file.exists():
                print(f"[SKIP RETRY] {rule_id}: Output already exists at {out_file}")
                continue
            print(f"\n--- RETRY Processing {rule_id} ---")
            prompt_text = prompt_path.read_text(encoding="utf-8")
            try:
                raw_resp = call_mistral(prompt_text)
            except Exception as e:
                print(f"[RETRY FAILED] {rule_id}: API error: {e}")
                continue

            json_text = extract_json_from_text(raw_resp)
            if not json_text:
                print(f"[RETRY FAILED] {rule_id}: Could not extract JSON. Raw output saved.")
                (OUT_DIR / f"{rule_id}_raw.txt").write_text(raw_resp, encoding="utf-8")
                continue

            try:
                metadata = json.loads(json_text)
            except Exception as e:
                print(f"[RETRY FAILED] {rule_id}: JSON parsing failed: {e}. Raw output saved.")
                (OUT_DIR / f"{rule_id}_raw.txt").write_text(raw_resp, encoding="utf-8")
                continue

            out_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[RETRY SUCCESS] {rule_id}: Saved to {out_file}")
