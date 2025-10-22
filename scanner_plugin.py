import importlib
import os

# Register supported languages and their scanner modules
SCANNERS = {
    "python": {
        "detect": lambda content, ext: ext == ".py" or "def " in content or "import " in content,
        "module": "python_v2.python_scanner"
    },
    "terraform": {
        "detect": lambda content, ext: ext == ".tf" or "resource " in content or "provider " in content,
        "module": "terraform_v2.scanner_common"
    }
}

def detect_language(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read(2048)
    for lang, meta in SCANNERS.items():
        if meta["detect"](content, ext):
            return lang
    return None

def get_scanner(lang):
    if lang not in SCANNERS:
        raise ValueError(f"Unsupported language: {lang}")
    mod = importlib.import_module(SCANNERS[lang]["module"])
    if hasattr(mod, "run_scan"):
        return mod.run_scan
    raise ImportError(f"Scanner module for {lang} does not have run_scan")
