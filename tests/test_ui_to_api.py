import json
from pathlib import Path
from scripts.ui_to_api import convert

TPL_DIR = Path(r"E:\comfy-desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Lib\site-packages"
               r"\comfyui_workflow_templates_json\templates")
ROOT = Path(__file__).resolve().parents[1]
OBJ = ROOT / "cache" / "object_info.json"

def test_convert_ltx23_structure():
    ui = json.loads((TPL_DIR / "video_ltx2_3_i2v.json").read_text(encoding="utf-8"))
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
