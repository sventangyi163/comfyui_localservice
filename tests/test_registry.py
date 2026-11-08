from pathlib import Path
import json
import pytest
from app.registry import load_registry, RegistryError

REG = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "registry_test.yaml"
ROOT = Path(__file__).resolve().parents[1]

def test_load_and_get():
    reg = load_registry(REG)
    e = reg["ltx-2.3-local"]
    assert e.duration_range == [3, 8] and e.fps == 25
    assert e.resolutions["480p"] == 480
    assert e.inject["prompt"][0].node == "320.319"

def test_unknown_model():
    reg = load_registry(REG)
    with pytest.raises(RegistryError):
        reg.get_entry("nope")

def test_validate_duration():
    reg = load_registry(REG)
    assert reg.get_entry("ltx-2.3-local").validate(duration=5, resolution="720p") == (5, 720)
    with pytest.raises(RegistryError):
        reg.get_entry("ltx-2.3-local").validate(duration=99, resolution="720p")
    with pytest.raises(RegistryError):
        reg.get_entry("ltx-2.3-local").validate(duration=5, resolution="1080p")

def test_unknown_inject_param_rejected(tmp_path):
    p = tmp_path / "bad_registry.yaml"
    p.write_text(
        "- name: bad-model\n"
        "  template: workflows/bad.json\n"
        "  inject:\n"
        '    foo: [{node: "1", field: "x"}]\n',
        encoding="utf-8",
    )
    with pytest.raises(RegistryError, match="foo"):
        load_registry(p)

def test_real_registry_smoke():
    reg = load_registry(ROOT / "registry.yaml")
    assert len(reg.entries) == 2
    assert reg.get_entry("ltx-2.3-local").available is True
    assert reg.get_entry("minimax-h3-local").available is False
    # minimax prompt 注入点回填守卫：注入节点/字段必须真实存在于已提交模板
    wf = json.loads((ROOT / "workflows" / "minimax-h3-i2v.json").read_text(encoding="utf-8"))
    inj = reg.get_entry("minimax-h3-local").inject["prompt"]
    assert inj, "minimax-h3-local 的 prompt 注入点未回填"
    for p in inj:
        assert p.node in wf, f"注入节点 {p.node} 不在模板中"
        assert p.field in wf[p.node]["inputs"], f"{p.node} 无字段 {p.field}"
