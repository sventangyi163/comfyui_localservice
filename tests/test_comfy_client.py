import httpx, pytest
from app.comfy_client import ComfyClient, parse_history, ComfySubmitError

HIST_DONE = {"status": {"completed": True, "messages": []},
             "outputs": {"75": {"videos": [{"filename": "a.mp4", "subfolder": "", "type": "output"}]}}}
HIST_ERR = {"status": {"completed": True, "messages": [
    ["execution_error", {"node_type": "KSampler", "exception_message": "OOM"}]]}, "outputs": {}}

def test_parse_history_done():
    st, vids, err = parse_history(HIST_DONE)
    assert st == "succeeded" and vids[0]["filename"] == "a.mp4" and err == ""

def test_parse_history_error():
    st, vids, err = parse_history(HIST_ERR)
    assert st == "failed" and "OOM" in err

@pytest.mark.asyncio
async def test_upload_and_queue():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/upload/image":
            return httpx.Response(200, json={"name": "t.png", "subfolder": "", "type": "input"})
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "pid-1"})
        return httpx.Response(404)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        c = ComfyClient("http://x", http)
        name = await c.upload_image(b"png", "t.png")
        assert name == "t.png"
        pid = await c.queue_prompt({"1": {"class_type": "X", "inputs": {}}})
        assert pid == "pid-1"

@pytest.mark.asyncio
async def test_queue_reject():
    def handler(request):
        return httpx.Response(400, json={"error": {"message": "bad"}, "node_errors": {"5": "x"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        c = ComfyClient("http://x", http)
        with pytest.raises(ComfySubmitError):
            await c.queue_prompt({})
