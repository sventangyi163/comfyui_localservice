# i2v-gateway

把本机 ComfyUI 包装成 **Ark 同构图生视频 API 服务**（127.0.0.1:8300 → ComfyUI :8188），供 AI互动短剧等外部应用把本地 ComfyUI 当作一个可切换的 i2v "大模型"使用。

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
start.bat          # 内置 NO_PROXY，规避系统代理拦截 localhost
# 或：.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8300
```

前置：ComfyUI 桌面版（或无头服务）在 :8188 运行中；v1 模型为 LTX-2.3（注册表 `registry.yaml`）。

## API（Ark 同构）

- `POST /contents/generations/tasks` — 提交（model / 首帧图 data URL / 提示词 / duration / resolution；画幅跟随首帧）
- `GET /contents/generations/tasks/{id}` — 轮询 status + video_url
- `GET /files/{id}.mp4` — 下载视频
- `GET /models` — 可用模型列表

## 文档

需求与设计、实施计划、验证记录：`doc/v1/`（01 需求与设计 / 02 实施计划 / 03 验证记录）。
