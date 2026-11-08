import json
import pytest
from pathlib import Path
from scripts.ui_to_api import convert

TPL_DIR = Path(r"E:\comfy-desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Lib\site-packages"
               r"\comfyui_workflow_templates_json\templates")
ROOT = Path(__file__).resolve().parents[1]
OBJ = ROOT / "cache" / "object_info.json"

WORKFLOWS = ROOT / "workflows"


def test_convert_ltx23_structure():
    tpl = TPL_DIR / "video_ltx2_3_i2v.json"
    if not tpl.is_file() or not OBJ.is_file():
        pytest.skip("需要本机 ComfyUI 模板与 object_info 缓存")
    ui = json.loads(tpl.read_text(encoding="utf-8"))
    oi = json.loads(OBJ.read_text(encoding="utf-8"))
    g = convert(ui, oi)
    assert g["269"]["class_type"] == "LoadImage"
    assert g["75"]["class_type"] == "SaveVideo"
    assert g["320.316"]["class_type"] == "CheckpointLoaderSimple"
    assert g["320.316"]["inputs"]["ckpt_name"] == "ltx-2.3-22b-dev-fp8.safetensors"
    assert g["320.319"]["class_type"] == "PrimitiveStringMultiline"
    assert g["320.290"]["class_type"] == "ResizeImageMaskNode"
    assert len(g) > 40
    src = g["75"]["inputs"]["video"]
    assert isinstance(src, list) and src[0].startswith("320.")
    # 连接完整性由真机 /prompt 校验闭环兜底


def _assert_wellformed(g: dict):
    """提交工件的结构不变量：连接必须是 [已有节点id, int slot]。"""
    for key, node in g.items():
        assert isinstance(node["class_type"], str) and node["class_type"]
        for field, v in node["inputs"].items():
            if isinstance(v, list):
                assert len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int), \
                    f"{key}.{field} 非法连接 {v!r}"
                assert v[0] in g, f"{key}.{field} 引用不存在的节点 {v[0]!r}"


def test_committed_ltx_workflow():
    g = json.loads((WORKFLOWS / "ltx-2.3-i2v.json").read_text(encoding="utf-8"))
    assert len(g) == 51
    assert any(k.startswith("320.") for k in g)
    _assert_wellformed(g)


def test_committed_minimax_workflow():
    g = json.loads((WORKFLOWS / "minimax-h3-i2v.json").read_text(encoding="utf-8"))
    assert len(g) == 26
    assert any(k.startswith("105.") for k in g)
    assert g["114"]["class_type"] == "LoadImage"
    _assert_wellformed(g)
