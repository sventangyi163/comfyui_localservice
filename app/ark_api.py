from __future__ import annotations
import base64, datetime, io, json, time
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from PIL import Image

from app.comfy_client import ComfySubmitError, parse_history
from app.config import ROOT
from app.registry import load_registry, RegistryError
from app.templating import build_graph, dims_for, frames_for

router = APIRouter()

class _ContentItem(BaseModel):
    type: str
    text: str | None = None
    image_url: dict | None = None

class ArkSubmitBody(BaseModel):
    model: str
    content: list[_ContentItem]
    duration: int = 5
    resolution: str = "720p"

def _new_task_id() -> str:
    return datetime.datetime.now().strftime("t_%Y%m%d_%H%M%S_") + \
        base64.b32encode(int(time.time() * 1000).to_bytes(6, "big")).decode()[:4].lower()

def _registry(request: Request):
    return load_registry(request.app.state.registry_path)

def _template_path(entry) -> Path:
    """registry.template 记录的是仓库相对路径（如 workflows/ltx-2.3-i2v.json）。"""
    return ROOT / entry.template

@router.post("/contents/generations/tasks")
async def submit(body: ArkSubmitBody, request: Request):
    app = request.app
    try:
        entry = _registry(request).get_entry(body.model)
        duration, short_side = entry.validate(body.duration, body.resolution)
    except RegistryError as e:
        raise HTTPException(400, detail=str(e))
    img_url = next((i.image_url.get("url", "") for i in body.content
                    if i.type == "image_url" and i.image_url), "")
    prompt = next((i.text for i in body.content if i.type == "text" and i.text), "")
    if not img_url or not prompt:
        raise HTTPException(400, detail="content 需含首帧图 data URL 与提示词文本")
    try:
        b64 = img_url.split(",", 1)[1]
        raw = base64.b64decode(b64)
        w, h = Image.open(io.BytesIO(raw)).size
    except Exception:
        raise HTTPException(400, detail="首帧图解码失败（需 data:image/...;base64）")
    template = _template_path(entry)
    if not template.exists():
        raise HTTPException(500, detail=f"模板缺失: {entry.template}")
    tpl_json = json.loads(template.read_text(encoding="utf-8"))
    gw, gh = dims_for((w, h), short_side, entry.dims_multiple)
    tid = _new_task_id()
    comfy = app.state.comfy
    try:
        name = await comfy.upload_image(raw, tid + "_first.png")
    except Exception as e:
        raise HTTPException(503, detail=f"ComfyUI 不可达: {e}")
    try:
        graph = build_graph(entry, tpl_json, image_name=name, prompt=prompt,
                            width=gw, height=gh,
                            length=frames_for(duration, entry.fps), fps=entry.fps,
                            short_side=short_side, seconds=duration)   # ⚠ 修正案：补传两参数
    except Exception as e:
        raise HTTPException(500, detail=f"模板注入失败（registry inject 与模板不匹配?）: {e}")
    try:
        pid = await comfy.queue_prompt(graph)
    except ComfySubmitError as e:
        raise HTTPException(400, detail=f"ComfyUI 拒绝: {e}")
    except Exception as e:
        raise HTTPException(503, detail=f"ComfyUI 不可达: {e}")
    app.state.store.create(tid, pid, body.model,
                           {"duration": duration, "resolution": body.resolution,
                            "width": gw, "height": gh, "prompt": prompt[:200]})
    return {"id": tid, "model": body.model}

@router.get("/contents/generations/tasks/{task_id}")
async def poll(task_id: str, request: Request):
    app = request.app
    row = app.state.store.get(task_id)
    if row is None:
        raise HTTPException(404)
    entry = None
    try:
        entry = _registry(request).get_entry(row["model"])
    except RegistryError:
        pass    # 模型被移除：仍可轮询/超时，用默认超时
    timeout_s = entry.timeout_s if entry else app.state.settings.default_timeout_s
    if row["status"] in ("queued", "running") and time.time() - row["created_at"] > timeout_s:
        app.state.store.set_status(task_id, "failed", error="timeout")
    elif row["status"] in ("queued", "running"):
        try:
            hist = await app.state.comfy.history(row["prompt_id"])
            st, vids, err = parse_history(hist)
            if st == "succeeded":
                f = vids[0]
                data = await app.state.comfy.fetch_output(f["filename"], f.get("subfolder", ""),
                                                          f.get("type", "output"))
                dest = Path(app.state.files_dir, f"{task_id}.mp4")
                dest.write_bytes(data)
                app.state.store.set_status(task_id, "succeeded", video_file=str(dest))
            elif st == "failed":
                app.state.store.set_status(task_id, "failed", error=err)
            elif st == "running" and row["status"] != "running":
                app.state.store.set_status(task_id, "running")
        except Exception:
            pass    # 瞬时不可达：返回缓存状态
    row = app.state.store.get(task_id)
    resp = {"id": row["id"], "model": row["model"], "status": row["status"],
            "progress": None, "created_at": row["created_at"],
            "content": {}, "error": {"message": row["error"]} if row["error"] else None}
    if row["status"] == "succeeded":
        resp["content"] = {"video_url": f"{app.state.public_base}/files/{row['id']}.mp4"}
    return resp

@router.get("/files/{fname}")
async def files(fname: str, request: Request):
    row = request.app.state.store.get(fname.rsplit(".", 1)[0])
    if row is None or row["status"] != "succeeded":
        raise HTTPException(404)
    p = Path(request.app.state.files_dir, fname)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4")

@router.get("/models")
async def models(request: Request):
    reg = _registry(request)
    ms = [{"name": e.name, "kind": "i2v",
           "available": e.available and _template_path(e).exists(),   # ⚠ 修正案：模板存在性实时校验
           "duration_range": e.duration_range,
           "resolutions": list(e.resolutions), "aspects": e.aspects}
          for e in reg.entries.values()]
    return {"models": ms}
