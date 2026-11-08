from __future__ import annotations
import uuid
import httpx

class ComfySubmitError(RuntimeError):
    def __init__(self, msg: str, node_errors: dict | None = None):
        super().__init__(msg)
        self.node_errors = node_errors or {}

def parse_history(entry: dict) -> tuple[str, list[dict], str]:
    """history 条目 → (状态, 视频文件列表, 错误摘要)。completed 且有产物=succeeded；
    execution_error=failed；否则 running。"""
    if not entry:
        return "running", [], ""
    status = entry.get("status") or {}
    msgs = status.get("messages") or []
    err = ""
    for m in msgs:
        if isinstance(m, list) and m and m[0] == "execution_error":
            d = m[1] if len(m) > 1 else {}
            err = f"{d.get('node_type', '?')}: {d.get('exception_message', '')}"
    if err:
        return "failed", [], err
    vids: list[dict] = []
    for node_out in (entry.get("outputs") or {}).values():
        for key in ("videos", "gifs", "images"):
            for f in (node_out.get(key) or []):
                fn = f.get("filename", "")
                if fn.endswith((".mp4", ".webm")):
                    vids.append(f)
    if status.get("completed") and vids:
        return "succeeded", vids, ""
    if status.get("completed"):
        return "failed", [], "completed 但无视频输出"
    return "running", [], ""

class ComfyClient:
    def __init__(self, base_url: str, http: httpx.AsyncClient | None = None):
        self.base_url = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())
        self._own = http is None
        self.http = http or httpx.AsyncClient(timeout=30)

    async def aclose(self):
        if self._own:
            await self.http.aclose()

    async def upload_image(self, data: bytes, name: str) -> str:
        r = await self.http.post(f"{self.base_url}/upload/image",
                                 files={"image": (name, data, "image/png")})
        r.raise_for_status()
        return r.json()["name"]

    async def queue_prompt(self, graph: dict) -> str:
        r = await self.http.post(f"{self.base_url}/prompt",
                                 json={"prompt": graph, "client_id": self.client_id})
        if r.status_code != 200:
            try:
                d = r.json()
                raise ComfySubmitError(str(d.get("error"))[:300], d.get("node_errors"))
            except ValueError:
                raise ComfySubmitError(f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()["prompt_id"]

    async def history(self, prompt_id: str) -> dict | None:
        r = await self.http.get(f"{self.base_url}/history/{prompt_id}")
        r.raise_for_status()
        return (r.json() or {}).get(prompt_id)

    async def fetch_output(self, filename: str, subfolder: str = "", ftype: str = "output") -> bytes:
        r = await self.http.get(f"{self.base_url}/view",
                                params={"filename": filename, "subfolder": subfolder, "type": ftype})
        r.raise_for_status()
        return r.content

    async def object_info(self) -> dict:
        r = await self.http.get(f"{self.base_url}/object_info")
        r.raise_for_status()
        return r.json()
