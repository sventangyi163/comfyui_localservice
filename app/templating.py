from __future__ import annotations
import copy
from app.registry import ModelEntry


def dims_for(aspect_wh: tuple[int, int], short_side: int, multiple: int) -> tuple[int, int]:
    """按首帧长宽比与短边档位求宽高，两边一律严格向上对齐到 multiple 倍数。"""
    w0, h0 = aspect_wh
    if w0 >= h0:   # 横版或方图：短边=高
        h = short_side; w = round(w0 / h0 * short_side)
    else:
        w = short_side; h = round(h0 / w0 * short_side)
    up = lambda v: ((v + multiple - 1) // multiple) * multiple
    return up(w), up(h)


def frames_for(duration_s: int, fps: int) -> int:
    return duration_s * fps + 1


def build_graph(entry: ModelEntry, template: dict, image_name: str, prompt: str,
                width: int, height: int, length: int, fps: int | None = None,
                short_side: int | None = None, seconds: int | None = None) -> dict:
    g = copy.deepcopy(template)
    vals = {"image": image_name, "prompt": prompt, "width": width, "height": height,
            "length": length, "fps": fps, "short_side": short_side, "seconds": seconds}
    for param, points in entry.inject.items():
        v = vals.get(param)
        if v is None:
            continue
        for p in points:
            g[p.node]["inputs"][p.field] = v
    return g
