from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.comfy_client import ComfyClient
from app.task_store import TaskStore
from app.ark_api import router as ark_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    if hasattr(app.state, "store"):    # 测试已注入（tests/test_api.py fixture）
        yield
        return
    s = get_settings()
    s.data_dir.mkdir(exist_ok=True); s.files_dir.mkdir(exist_ok=True)
    app.state.settings = s
    app.state.registry_path = s.registry_path
    app.state.workflows_dir = s.workflows_dir
    app.state.files_dir = s.files_dir
    app.state.public_base = f"http://{s.host}:{s.port}"
    app.state.store = TaskStore(s.data_dir / "tasks.db"); app.state.store.init()
    app.state.store.fail_pending("gateway restart")
    app.state.comfy = ComfyClient(s.comfy_base_url)
    try:
        await app.state.comfy.object_info()   # 启动时连通性检查（失败不阻断启动）
    except Exception:
        pass
    yield
    await app.state.comfy.aclose()

app = FastAPI(title="i2v-gateway", lifespan=lifespan)
app.include_router(ark_router)

@app.get("/healthz")
def healthz():
    s = get_settings()
    return {"ok": True, "comfy": s.comfy_base_url}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=get_settings().host, port=get_settings().port)
