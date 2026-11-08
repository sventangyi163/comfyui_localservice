from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import yaml


class RegistryError(ValueError):
    pass


KNOWN_INJECT_PARAMS = {"image", "prompt", "width", "height", "length", "fps",
                       "short_side", "seconds"}


@dataclass
class InjectPoint:
    node: str
    field: str


@dataclass
class ModelEntry:
    name: str
    template: str
    available: bool = True
    duration_range: list = field(default_factory=lambda: [3, 8])
    fps: int = 25
    resolutions: dict = field(default_factory=lambda: {"720p": 720})
    dims_multiple: int = 32
    aspects: list = field(default_factory=lambda: ["9:16", "16:9", "1:1"])
    timeout_s: int = 1800
    inject: dict = field(default_factory=dict)  # param -> list[InjectPoint]

    def validate(self, duration: int, resolution: str) -> tuple[int, int]:
        lo, hi = self.duration_range
        if not (lo <= int(duration) <= hi):
            raise RegistryError(f"duration {duration} 超出 [{lo},{hi}]")
        if resolution not in self.resolutions:
            raise RegistryError(f"resolution 不支持: {resolution}，可选 {list(self.resolutions)}")
        return int(duration), self.resolutions[resolution]


@dataclass
class Registry:
    entries: dict

    def get_entry(self, name: str) -> ModelEntry:
        if name not in self.entries:
            raise RegistryError(f"未注册模型: {name}")
        return self.entries[name]

    def __getitem__(self, name: str) -> ModelEntry:
        return self.get_entry(name)


def load_registry(path: Path) -> Registry:
    entries: dict[str, ModelEntry] = {}
    for raw in yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []:
        inj = {}
        for k, v in (raw.get("inject") or {}).items():
            if k not in KNOWN_INJECT_PARAMS:
                raise RegistryError(f"未知 inject 参数: {k}（模型 {raw['name']}）")
            inj[k] = [InjectPoint(**p) for p in v]
        e = ModelEntry(name=raw["name"], template=raw["template"],
                       available=raw.get("available", True),
                       duration_range=raw.get("duration_range", [3, 8]),
                       fps=raw.get("fps", 25),
                       resolutions=raw.get("resolutions", {"720p": 720}),
                       dims_multiple=raw.get("dims_multiple", 32),
                       aspects=raw.get("aspects", ["9:16", "16:9", "1:1"]),
                       timeout_s=raw.get("timeout_s", 1800), inject=inj)
        entries[e.name] = e
    return Registry(entries)
