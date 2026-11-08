"""抓取 ComfyUI /object_info 到 cache/object_info.json（转换器命名映射用）。"""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8188/object_info"
    data = json.load(urllib.request.urlopen(url, timeout=60))
    out = ROOT / "cache" / "object_info.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data), encoding="utf-8")
    print(f"saved {len(data)} node classes -> {out}")

if __name__ == "__main__":
    main()
