from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    comfy_base_url: str = "http://127.0.0.1:8188"
    host: str = "127.0.0.1"
    port: int = 8300
    registry_path: Path = ROOT / "registry.yaml"
    data_dir: Path = ROOT / "data"
    files_dir: Path = ROOT / "files"
    default_timeout_s: int = 1800

def get_settings() -> Settings:
    return Settings()
