from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    comfy_base_url: str = "http://127.0.0.1:8188"
    host: str = "127.0.0.1"
    port: int = 8300
    workflows_dir: Path = ROOT / "workflows"
    registry_path: Path = ROOT / "registry.yaml"
    data_dir: Path = ROOT / "data"
    files_dir: Path = ROOT / "files"
    cache_dir: Path = ROOT / "cache"
    default_timeout_s: int = 1800
    model_dirs: list = field(default_factory=lambda: [
        Path(r"E:\comfy-desktop\ComfyUI-Shared\models\checkpoints"),
        Path(r"E:\comfy-desktop\ComfyUI-Installs\ComfyUI\ComfyUI\models\checkpoints"),
    ])

def get_settings() -> Settings:
    return Settings()
