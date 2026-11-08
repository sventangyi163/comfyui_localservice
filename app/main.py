from fastapi import FastAPI
from app.config import get_settings

app = FastAPI(title="i2v-gateway")

@app.get("/healthz")
def healthz():
    s = get_settings()
    return {"ok": True, "comfy": s.comfy_base_url}
