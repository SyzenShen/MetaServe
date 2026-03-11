import os
import sys
import csv
import json
from datetime import datetime

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJ)

def get_methods():
    from file_upload.metadata_extractor import MetadataExtractor
    extractor = MetadataExtractor()
    content_assisted = sorted(list(extractor.extractors.keys()))
    return content_assisted

def main():
    content_assisted = get_methods()
    all_types = set(content_assisted)
    ext_only = sorted(list(set(["other"]) | (set() - set())))
    rows = []
    for t in sorted(content_assisted):
        rows.append({"file_type": t, "method": "content-assisted"})
    rows.append({"file_type": "other", "method": "extension-based"})
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"filetype_methods_{ts}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file_type", "method"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(json.dumps({"csv": csv_path, "content_assisted": content_assisted}, ensure_ascii=False))

if __name__ == "__main__":
    main()

