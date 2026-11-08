"""端到端冒烟：造首帧图 → 提交 → 轮询 → 下载 → ffprobe 断言。用法:
python scripts/smoke_local.py <model> <duration> <resolution> <aspect: 9:16|16:9>
"""
import base64, io, json, sys, time, urllib.request
from PIL import Image

BASE = "http://127.0.0.1:8300"

def make_first_frame(aspect: str) -> str:
    w, h = (720, 1280) if aspect == "9:16" else (1280, 720)
    img = Image.new("RGB", (w, h), (80, 120, 200))
    buf = io.BytesIO(); img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def main():
    model, dur, res, aspect = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    body = json.dumps({"model": model, "content": [
        {"type": "image_url", "image_url": {"url": make_first_frame(aspect)}},
        {"type": "text", "text": "slow cinematic dolly forward, subtle light drift, ambient"}],
        "duration": dur, "resolution": res}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        f"{BASE}/contents/generations/tasks", data=body,
        headers={"Content-Type": "application/json"}), timeout=120)
    tid = json.loads(r.read())["id"]
    print("task:", tid, flush=True)
    t0 = time.time()
    while True:
        j = json.loads(urllib.request.urlopen(f"{BASE}/contents/generations/tasks/{tid}",
                                              timeout=60).read())
        print(f"[{time.time()-t0:6.0f}s] {j['status']} err={j.get('error')}", flush=True)
        if j["status"] in ("succeeded", "failed"):
            break
        time.sleep(20)
    if j["status"] != "succeeded":
        print("FAILED:", j.get('error')); sys.exit(1)
    out = f"smoke_{tid}.mp4"
    urllib.request.urlretrieve(j["content"]["video_url"], out)
    print("saved:", out, "elapsed:", round(time.time() - t0), "s")

if __name__ == "__main__":
    main()
