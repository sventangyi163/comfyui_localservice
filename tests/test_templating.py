from app.registry import ModelEntry, InjectPoint
from app.templating import dims_for, frames_for, build_graph

TPL = {  # 迷你模板：3 节点，模拟注入
  "269": {"class_type": "LoadImage", "inputs": {"image": "old.png"}},
  "320.319": {"class_type": "PrimitiveStringMultiline", "inputs": {"text": "hi"}},
  "320.295": {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": 768, "height": 512, "length": 97, "batch_size": 1}},
}

def entry():
    return ModelEntry(name="x", template="t.json", fps=25, dims_multiple=32, inject={
        "image": [InjectPoint("269", "image")],
        "prompt": [InjectPoint("320.319", "text")],
        "width": [InjectPoint("320.295", "width")],
        "height": [InjectPoint("320.319", "height")],   # 故意指向不同节点验证多点注入
        "length": [InjectPoint("320.295", "length")],
    })

def test_dims_16_9_and_9_16():
    assert dims_for((1920, 1080), 736, 32) == (1312, 736)   # 720p 档（对齐后 736）
    assert dims_for((1080, 1920), 736, 32) == (736, 1312)
    assert dims_for((1000, 1000), 544, 32) == (544, 544)

def test_dims_aligns_unaligned_input():
    assert dims_for((1000, 1000), 540, 32) == (544, 544)    # 无论传入值，一律向上对齐
    assert dims_for((1920, 1080), 480, 32) == (864, 480)

def test_frames():
    assert frames_for(5, 25) == 126   # duration*fps+1

def test_build_graph_no_mutation_and_injection():
    g = build_graph(entry(), dict(TPL), image_name="abc.png", prompt="夜景",
                    width=720, height=1280, length=126)
    assert g["269"]["inputs"]["image"] == "abc.png"
    assert g["320.319"]["inputs"]["text"] == "夜景"
    assert g["320.295"]["inputs"]["width"] == 720
    assert g["320.319"]["inputs"]["height"] == 1280
    assert g["320.295"]["inputs"]["length"] == 126
    assert TPL["269"]["inputs"]["image"] == "old.png"          # 原模板不被改
