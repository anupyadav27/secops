import os
import json
import re

def to_snake_case(text):
    text = re.sub(r'["\'\-]', '', text)
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    text = text.replace(' ', '_').replace('-', '_')
    text = re.sub(r'_+', '_', text)
    return text.lower()

folder = r'd:/task10/python_rules/'
renamed = 0
skipped = 0
for filename in os.listdir(folder):
    if filename.endswith('.json'):
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
            new_name = to_snake_case(title) + '.json'
            new_path = os.path.join(folder, new_name)
            if new_name != filename:
                if not os.path.exists(new_path):
                    os.rename(path, new_path)
                    print(f'[RENAMED] {filename} -> {new_name}')
                    renamed += 1
                else:
                    print(f'[SKIPPED] {filename}: {new_name} already exists')
                    skipped += 1
            else:
                print(f'[SKIPPED] {filename}: Name already correct')
                skipped += 1
        else:
            print(f'[SKIPPED] {filename}: No title found')
            skipped += 1
print(f'\nDone. Renamed: {renamed}, Skipped: {skipped}')
