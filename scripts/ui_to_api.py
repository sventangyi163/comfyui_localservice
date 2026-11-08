"""UI 格式工作流 → API 格式 prompt graph。支持子图（definitions.subgraphs）展平：
子图节点 id 重写为 "<instance_id>.<inner_id>"，接口链接按 sg.inputs/outputs 的 linkIds 穿透重接。
widget 值按 object_info 的 required+optional 顺序对齐到 inputs 字段名（含 V3 动态组合递归展开）。
用法: python scripts/ui_to_api.py <ui.json> <out.json> <object_info.json>
"""
from __future__ import annotations
import json, sys
from pathlib import Path

SKIP_TYPES = {"MarkdownNote", "Note", "Reroute"}
_SCALARS = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}


def _opts(typ) -> dict:
    if isinstance(typ, list) and len(typ) > 1 and isinstance(typ[1], dict):
        return typ[1]
    return {}


def _t0(typ):
    return typ[0] if isinstance(typ, list) and typ else typ


def _is_widget_type(t0, opts: dict) -> bool:
    """该输入是否在 UI 上以 widget 呈现（会占据 widgets_values 一个位置）。"""
    if isinstance(t0, list):  # 旧式 combo
        return not opts.get("forceInput") and not opts.get("imageUpload")
    if isinstance(t0, str):
        if all(p.strip() in _SCALARS for p in t0.split(",")):
            return not opts.get("forceInput")
    return False


def _entries(spec: dict):
    """object_info 的 input 段按声明顺序展平为 (name, typ)。"""
    for group in ("required", "optional"):
        for name, typ in (spec.get(group) or {}).items():
            yield name, typ


def _align_widgets(cls: str, oi: dict, wv: list) -> dict:
    """widgets_values 按声明顺序对齐到字段名；COMFY_DYNAMICCOMBO_V3 按已选 key
    递归展开嵌套输入（嵌套字段名带 "<combo>.<field>" 前缀，与服务端
    get_finalized_class_inputs 的命名一致）。多余的 wv（控件 widget 等）丢弃。"""
    out: dict = {}
    it = iter(wv)

    def take():
        try:
            return next(it), True
        except StopIteration:
            return None, False

    def walk(entries, prefix: str):
        for name, typ in entries:
            t0, opts = _t0(typ), _opts(typ)
            full = prefix + name
            if t0 == "COMFY_DYNAMICCOMBO_V3":
                if opts.get("hidden"):
                    continue
                key, ok = take()
                if not ok:
                    return
                out[full] = key
                for opt in opts.get("options") or []:
                    if opt.get("key") == key:
                        walk(_entries(opt.get("inputs") or {}), full + ".")
                        break
            elif _is_widget_type(t0, opts):
                v, ok = take()
                if not ok:
                    return
                out[full] = v
                if opts.get("control_after_generate"):
                    _, ok = take()  # 控制 widget（fixed/randomize…）额外占一个 wv 槽
                    if not ok:
                        return

    walk(_entries(oi.get(cls, {}).get("input", {})), "")
    return out


def _is_widget_sg_input(sgin: dict) -> bool:
    """子图接口项是否 widget 型（占据实例 widgets_values 一个位置）。"""
    return all(p.strip() in _SCALARS for p in str(sgin.get("type", "")).split(","))


def _field_at(uinode: dict, slot: int, oi: dict) -> str | None:
    """UI 节点 inputs[slot] 的字段名（即 API 输入名，含动态组合前缀）。"""
    ins = uinode.get("inputs") or []
    if slot < len(ins):
        nm = ins[slot].get("name")
        if nm:
            return nm
    cls = uinode.get("type", "")
    conn = [nm for nm, typ in _entries(oi.get(cls, {}).get("input", {}))
            if not _is_widget_type(_t0(typ), _opts(typ))]
    return conn[slot] if slot < len(conn) else None


class _Ctx:
    """一个平面化上下文（外层图或某实例的子图内层）的链接解析。"""

    def __init__(self, nodes: dict, links: dict):
        self.nodes = nodes          # id -> ui node
        self.links = links          # link id -> link(dict)

    def resolve(self, node_id, slot: int):
        """穿透 Reroute，返回 (最终节点id, 输出slot)。"""
        seen = 0
        while True:
            n = self.nodes.get(node_id)
            if n is None or n.get("type") != "Reroute":
                return node_id, slot
            ins = n.get("inputs") or []
            if not ins or ins[0].get("link") is None:
                return None, None
            l = self.links.get(ins[0]["link"])
            if l is None or seen > 100:
                return None, None
            node_id, slot = l["origin_id"], l["origin_slot"]
            seen += 1


def convert(ui: dict, oi: dict) -> dict:
    graph: dict = {}
    sgs = {sg["id"]: sg for sg in ui.get("definitions", {}).get("subgraphs", [])}
    outer_nodes = {n["id"]: n for n in ui["nodes"]}
    outer_links = {l[0]: l for l in ui.get("links", [])}
    octx = _Ctx(outer_nodes, outer_links)

    def put(key: str, uinode: dict):
        if uinode.get("type") in SKIP_TYPES:
            return
        graph[key] = {
            "class_type": uinode["type"],
            "inputs": _align_widgets(uinode["type"], oi, list(uinode.get("widgets_values") or [])),
        }

    for n in ui["nodes"]:
        if n["type"] in sgs:
            continue
        put(str(n["id"]), n)

    def connect(tgt_key: str, uinode_tgt: dict, slot: int,
                src_ctx: _Ctx, src_id, src_slot: int, src_prefix: str = ""):
        src_id, src_slot = src_ctx.resolve(src_id, src_slot)
        if src_id is None:
            return
        src_node = src_ctx.nodes.get(src_id)
        if src_node is None or src_node.get("type") in SKIP_TYPES:
            return
        field = _field_at(uinode_tgt, slot, oi)
        if field is not None:
            src_key = f"{src_prefix}{src_id}" if src_prefix else str(src_id)
            graph[tgt_key]["inputs"][field] = [src_key, int(src_slot)]

    # 外层普通节点间链接（不碰子图实例）
    for l in ui.get("links", []):
        src_id, src_slot, tgt_id, tgt_slot = l[1], l[2], l[3], l[4]
        if outer_nodes.get(src_id, {}).get("type") in sgs or \
           outer_nodes.get(tgt_id, {}).get("type") in sgs:
            continue
        if str(tgt_id) not in graph or str(src_id) not in graph:
            continue
        connect(str(tgt_id), outer_nodes[tgt_id], tgt_slot, octx, src_id, src_slot)

    # 子图实例展平
    for n in ui["nodes"]:
        sg = sgs.get(n["type"])
        if sg is None:
            continue
        prefix = str(n["id"])
        inner_nodes = {m["id"]: m for m in sg.get("nodes", [])}
        inner_links = {l["id"]: l for l in sg.get("links", [])}
        ictx = _Ctx(inner_nodes, inner_links)
        for inner in sg["nodes"]:
            put(f"{prefix}.{inner['id']}", inner)

        # 实例 widget 值：按 sg.inputs 中 widget 型项的顺序对齐实例 widgets_values
        widget_slots = [i for i, sgin in enumerate(sg.get("inputs", [])) if _is_widget_sg_input(sgin)]
        wv = list(n.get("widgets_values") or [])
        for k, si in enumerate(widget_slots):
            if k >= len(wv):
                break
            for lid in (sg["inputs"][si].get("linkIds") or []):
                il = inner_links.get(lid)
                if not il or il["origin_id"] != sg["inputNode"]["id"]:
                    continue
                tgt = inner_nodes.get(il["target_id"])
                if tgt is None or tgt.get("type") in SKIP_TYPES:
                    continue
                field = _field_at(tgt, il["target_slot"], oi)
                if field is not None:
                    graph[f"{prefix}.{il['target_id']}"]["inputs"][field] = wv[k]

        # 实例连接输入：实例 inputs 里的已连接项按名匹配 sg.inputs，外层源穿透到内层消费节点
        for e in n.get("inputs", []):
            if e.get("link") is None:
                continue
            ol = outer_links.get(e["link"])
            if ol is None:
                continue
            if outer_nodes.get(ol[1], {}).get("type") in sgs:
                continue  # 源是另一个子图实例：不产生悬空引用
            si = next((i for i, sgin in enumerate(sg.get("inputs", []))
                       if sgin.get("name") in (e.get("name"), (e.get("widget") or {}).get("name"))), None)
            if si is None:
                continue
            for lid in (sg["inputs"][si].get("linkIds") or []):
                il = inner_links.get(lid)
                if not il:
                    continue
                tgt = inner_nodes.get(il["target_id"])
                if tgt is None:
                    continue
                connect(f"{prefix}.{il['target_id']}", tgt, il["target_slot"],
                        octx, ol[1], ol[2])

        # 子图内层普通链接（源与目标都是内层实体节点）
        in_id, out_id = sg["inputNode"]["id"], sg["outputNode"]["id"]
        for il in sg.get("links", []):
            if il["origin_id"] == in_id or il["target_id"] == out_id:
                continue
            tgt = inner_nodes.get(il["target_id"])
            src = inner_nodes.get(il["origin_id"])
            if tgt is None or src is None:
                continue
            connect(f"{prefix}.{il['target_id']}", tgt, il["target_slot"],
                    ictx, il["origin_id"], il["origin_slot"], src_prefix=prefix + ".")

        # 子图输出：内层源穿透到外层消费节点
        for so, sgout in enumerate(sg.get("outputs", [])):
            il = next((inner_links[lid] for lid in (sgout.get("linkIds") or [])
                       if lid in inner_links), None)
            if il is None:
                continue
            for ol in ui.get("links", []):
                if ol[1] != n["id"] or ol[2] != so:
                    continue
                tgt = outer_nodes.get(ol[3])
                if tgt is None or tgt.get("type") in sgs:
                    continue
                connect(str(ol[3]), tgt, ol[4], ictx, il["origin_id"], il["origin_slot"],
                        src_prefix=prefix + ".")

    return graph


def main():
    src, dst, oi_path = sys.argv[1], sys.argv[2], sys.argv[3]
    ui = json.loads(Path(src).read_text(encoding="utf-8"))
    oi = json.loads(Path(oi_path).read_text(encoding="utf-8"))
    g = convert(ui, oi)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    Path(dst).write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(g)} nodes -> {dst}")


if __name__ == "__main__":
    main()
