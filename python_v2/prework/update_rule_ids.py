import os
import json
import re

def to_snake_case(text):
    # Remove quotes and special characters, replace spaces and dashes with underscores
    text = re.sub(r'["\'\-]', '', text)
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    text = text.replace(' ', '_').replace('-', '_')
    text = re.sub(r'_+', '_', text)
    return text.lower()

folder = r'd:/task10/python_rules/'
total = 0
updated = 0
skipped = 0
for filename in os.listdir(folder):
    if filename.endswith('.json'):
        total += 1
        path = os.path.join(folder, filename)
        with open(path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f'[ERROR] {filename}: {e}')
                skipped += 1
                continue
        title = data.get('title')
        if title:
            snake_case = to_snake_case(title)
            data['rule_id'] = snake_case
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f'[UPDATED] {filename} -> rule_id: {snake_case}')
            updated += 1
        else:
            print(f'[SKIPPED] {filename}: No title found')
            skipped += 1
print(f'\nDone. Processed: {total}, Updated: {updated}, Skipped: {skipped}')
