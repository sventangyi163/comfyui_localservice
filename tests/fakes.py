class FakeComfy:
    """submit 时登记 pid；finish_ok() 完成"最近一次提交"。down=True 模拟不可达。"""
    def __init__(self):
        self.down = False
        self._done: dict[str, dict | None] = {}
        self._last_pid: str = ""

    async def upload_image(self, data: bytes, name: str) -> str:
        if self.down: raise ConnectionError("comfy down")
        return "uploaded_" + name

    async def queue_prompt(self, graph: dict) -> str:
        if self.down: raise ConnectionError("comfy down")
        pid = f"pid-{len(self._done) + 1}"
        self._done[pid] = None
        self._last_pid = pid
        return pid

    async def history(self, prompt_id: str):
        if self.down: raise ConnectionError("comfy down")
        return self._done.get(prompt_id)

    async def fetch_output(self, filename: str, subfolder: str = "", ftype: str = "output") -> bytes:
        if self.down: raise ConnectionError("comfy down")
        return b"\x00\x00\x00\x1cftypmp42fakevideo"

    def finish_ok(self):
        self._done[self._last_pid] = {
            "status": {"completed": True, "messages": []},
            "outputs": {"1": {"videos": [
                {"filename": "a.mp4", "subfolder": "", "type": "output"}]}}}
