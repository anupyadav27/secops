import os
import json

def append_metadata_to_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            file_path = os.path.join(directory, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    print(f"[ERROR] {filename}: {e}")
                    continue
            # Append metadata at the end
            data['metadata'] = {
                'filename': filename,
                'rule_id': data.get('rule_id', ''),
                'title': data.get('title', ''),
                'status': data.get('status', ''),
                'defaultSeverity': data.get('defaultSeverity', ''),
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[UPDATED] {filename} with metadata")

if __name__ == "__main__":
    docs_folder = r'd:/task10/python_docs/'
    append_metadata_to_files(docs_folder)
