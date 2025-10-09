import os

def rename_files_with_metadata(directory):
    for filename in os.listdir(directory):
        if filename.endswith('.json') and not filename.endswith('_metadata.json'):
            base, ext = os.path.splitext(filename)
            new_filename = f"{base}_metadata{ext}"
            src = os.path.join(directory, filename)
            dst = os.path.join(directory, new_filename)
            os.rename(src, dst)
            print(f"Renamed: {filename} -> {new_filename}")

if __name__ == "__main__":
    docs_folder = r'd:/task10/python_docs/'
    rename_files_with_metadata(docs_folder)
