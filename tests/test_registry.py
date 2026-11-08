from pathlib import Path
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

def test_real_registry_smoke():
    reg = load_registry(ROOT / "registry.yaml")
    assert len(reg.entries) == 2
    assert reg.get_entry("ltx-2.3-local").available is True
    assert reg.get_entry("minimax-h3-local").available is False
