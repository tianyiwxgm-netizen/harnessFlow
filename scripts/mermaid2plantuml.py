#!/usr/bin/env python3
"""Mermaid → PlantUML batch converter for 3-1-Solution-Technical docs.

Covers:
- sequenceDiagram (100% mechanical)
- stateDiagram-v2 (near-compatible)
- flowchart / graph TB|LR|TD|BT|RL (rule-based component diagram)
- classDiagram / erDiagram (fallback)
"""
import re, os, sys, glob, html

BASE = "/Users/zhongtianyi/work/code/harnessFlow/docs/3-1-Solution-Technical"


def decode_entities(s: str) -> str:
    s = s.replace("<br/>", "\\n").replace("<br>", "\\n").replace("<BR/>", "\\n")
    s = html.unescape(s)
    return s


def convert_sequence(body: str) -> str:
    out = ["@startuml", "autonumber"]
    for line in body.splitlines():
        L = line.rstrip()
        stripped = L.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if stripped == "sequenceDiagram":
            continue
        # title
        m = re.match(r"^title\s+(.+)$", stripped)
        if m:
            out.insert(1, f"title {m.group(1)}")
            continue
        # participant X as "Y"  / participant X as Y
        m = re.match(r'^participant\s+(\S+)\s+as\s+"?([^"]+?)"?$', stripped)
        if m:
            out.append(f'participant "{m.group(2).strip()}" as {m.group(1)}')
            continue
        m = re.match(r"^participant\s+(\S+)\s*$", stripped)
        if m:
            out.append(f"participant {m.group(1)}")
            continue
        # actor X / actor X as Y
        m = re.match(r'^actor\s+(\S+)\s+as\s+"?([^"]+?)"?$', stripped)
        if m:
            out.append(f'actor "{m.group(2).strip()}" as {m.group(1)}')
            continue
        m = re.match(r"^actor\s+(\S+)\s*$", stripped)
        if m:
            out.append(f"actor {m.group(1)}")
            continue
        # X ->> Y : msg  /  X -->> Y : reply
        m = re.match(r"^(\S+)\s*->>\s*(\S+)\s*:\s*(.+)$", stripped)
        if m:
            out.append(f"{m.group(1)} -> {m.group(2)} : {decode_entities(m.group(3))}")
            continue
        m = re.match(r"^(\S+)\s*-->>\s*(\S+)\s*:\s*(.+)$", stripped)
        if m:
            out.append(f"{m.group(1)} --> {m.group(2)} : {decode_entities(m.group(3))}")
            continue
        m = re.match(r"^(\S+)\s*-x\s*(\S+)\s*:\s*(.+)$", stripped)
        if m:
            out.append(f"{m.group(1)} ->x {m.group(2)} : {decode_entities(m.group(3))}")
            continue
        # Note over/right of/left of
        m = re.match(r"^Note\s+over\s+(\S+(?:\s*,\s*\S+)?)\s*:\s*(.+)$", stripped, re.I)
        if m:
            out.append(f"note over {m.group(1).strip()} : {decode_entities(m.group(2))}")
            continue
        m = re.match(r"^Note\s+(right|left)\s+of\s+(\S+)\s*:\s*(.+)$", stripped, re.I)
        if m:
            out.append(f"note {m.group(1).lower()} of {m.group(2)} : {decode_entities(m.group(3))}")
            continue
        # activate/deactivate
        m = re.match(r"^activate\s+(\S+)$", stripped)
        if m:
            out.append(f"activate {m.group(1)}")
            continue
        m = re.match(r"^deactivate\s+(\S+)$", stripped)
        if m:
            out.append(f"deactivate {m.group(1)}")
            continue
        # loop / alt / else / opt / critical / par / end
        if re.match(r"^(loop|alt|opt|critical)(\s+.+)?$", stripped):
            out.append(stripped)
            continue
        if stripped == "else" or re.match(r"^else\s+.+$", stripped):
            out.append(stripped)
            continue
        if stripped == "end":
            out.append("end")
            continue
        # par blocks — Mermaid 'par ... and ... end' → PlantUML 'par ... else ... end'
        if re.match(r"^par(\s+.+)?$", stripped):
            out.append(stripped.replace("par", "par", 1))
            continue
        if re.match(r"^and(\s+.+)?$", stripped):
            out.append("else" + stripped[3:])
            continue
        # rect rgb → skip (use group)
        if stripped.startswith("rect "):
            out.append("group")
            continue
        # Fallback: keep as-is (PlantUML often tolerant)
        out.append(L)
    out.append("@enduml")
    return "\n".join(out)


def convert_state(body: str) -> str:
    """stateDiagram-v2 is near-identical in PlantUML; mainly wrap with @startuml/@enduml."""
    out = ["@startuml"]
    for line in body.splitlines():
        L = line.rstrip()
        stripped = L.strip()
        if stripped in ("stateDiagram-v2", "stateDiagram"):
            continue
        if not stripped or stripped.startswith("%%"):
            continue
        out.append(decode_entities(L))
    out.append("@enduml")
    return "\n".join(out)


def convert_class(body: str) -> str:
    out = ["@startuml"]
    for line in body.splitlines():
        L = line.rstrip()
        stripped = L.strip()
        if stripped == "classDiagram":
            continue
        if not stripped or stripped.startswith("%%"):
            continue
        out.append(decode_entities(L))
    out.append("@enduml")
    return "\n".join(out)


def convert_er(body: str) -> str:
    """erDiagram → PlantUML entity (近似)"""
    out = ["@startuml"]
    for line in body.splitlines():
        L = line.rstrip()
        stripped = L.strip()
        if stripped == "erDiagram":
            continue
        if not stripped or stripped.startswith("%%"):
            continue
        # X ||--o{ Y : label → X "1" -- "0..*" Y : label
        m = re.match(r"^(\S+)\s+([|o}{\-]+)\s+(\S+)\s*:\s*(.+)$", stripped)
        if m:
            out.append(f'{m.group(1)} -- {m.group(3)} : {decode_entities(m.group(4))}')
            continue
        out.append(decode_entities(L))
    out.append("@enduml")
    return "\n".join(out)


def convert_flowchart(body: str) -> str:
    """flowchart/graph TB|LR|TD|BT|RL → PlantUML component diagram."""
    out = ["@startuml"]
    # direction handling
    first = body.strip().splitlines()[0].strip() if body.strip() else ""
    if re.search(r"\b(LR|RL)\b", first):
        out.append("left to right direction")
    # else: default top-to-bottom (PlantUML default)

    # Preprocess: collect subgraph / node / edge definitions
    lines = body.splitlines()
    pending_styles_cut = []

    indent_stack = 0
    for raw_line in lines:
        L = raw_line.rstrip()
        stripped = L.strip()
        # Skip flowchart/graph header
        if re.match(r"^(flowchart|graph)\s+(TB|LR|TD|BT|RL)\s*$", stripped):
            continue
        if not stripped or stripped.startswith("%%"):
            continue

        # direction (inside subgraph)
        if re.match(r"^direction\s+(TB|LR|TD|BT|RL)\s*$", stripped):
            continue

        # subgraph X ["title"]  /  subgraph X [title]
        m = re.match(r'^subgraph\s+(\S+)\s*\[\s*"?([^"\]]+?)"?\s*\]\s*$', stripped)
        if m:
            title = decode_entities(m.group(2)).strip()
            out.append(f'package "{title}" as {m.group(1)} {{')
            continue
        # subgraph X
        m = re.match(r"^subgraph\s+(\S+)\s*$", stripped)
        if m:
            out.append(f'package "{m.group(1)}" {{')
            continue
        # end of subgraph
        if stripped == "end":
            out.append("}")
            continue

        # style / classDef / class … → skip (not directly supported)
        if stripped.startswith("style ") or stripped.startswith("classDef ") or re.match(r"^class\s+\S+\s+\w+$", stripped):
            pending_styles_cut.append(stripped)
            continue

        # linkStyle
        if stripped.startswith("linkStyle "):
            pending_styles_cut.append(stripped)
            continue

        # click / click → skip
        if stripped.startswith("click "):
            continue

        # Edge with pipe-label:  A -->|label| B   /   A -.->|label| B   /   A ==>|label| B
        m = re.match(r"^(\S+)\s*(-.->|-->|==>|---|\.->|=>)\s*\|\s*(.+?)\s*\|\s*(\S+)(.*)$", stripped)
        if m:
            src, arrow, label, dst, rest = m.groups()
            plant_arrow = {
                "-->": "-->",
                "-.->": "..>",
                "==>": "==>",
                "---": "--",
                ".->": "..>",
                "=>": "==>",
            }[arrow]
            label_dec = decode_entities(label).replace("|", "/")
            # rest may include node-def for dst (e.g., B[label])
            dst_def = ""
            if rest.strip():
                dst_def = rest.strip()
            out.append(f"{src} {plant_arrow} {dst} : {label_dec}")
            if dst_def:
                node_m = re.match(r'^\[(.*?)\]$|^\("(.*?)"\)$|^\((.+?)\)$|^\{(.+?)\}$', dst_def)
                if node_m:
                    lbl = next(g for g in node_m.groups() if g is not None)
                    out.append(f'{dst} : {decode_entities(lbl)}')
            continue

        # Simple edge: A --> B   /   A -.-> B   /   A ==> B   /   A --- B
        m = re.match(r"^(\S+?)(?:\[(.*?)\])?\s*(-.->|-->|==>|---|\.->|=>)\s*(\S+?)(?:\[(.*?)\])?\s*$", stripped)
        if m:
            src, src_lbl, arrow, dst, dst_lbl = m.groups()
            plant_arrow = {
                "-->": "-->",
                "-.->": "..>",
                "==>": "==>",
                "---": "--",
                ".->": "..>",
                "=>": "==>",
            }[arrow]
            if src_lbl:
                out.append(f'component "{decode_entities(src_lbl)}" as {src}')
            if dst_lbl:
                out.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
            out.append(f"{src} {plant_arrow} {dst}")
            continue

        # Node-only definitions:  A["label"]  /  A[label]  /  A("label")  /  A(label)  /  A{label}  /  A[[label]]  /  A((label))
        m = re.match(r'^(\S+?)\[\[(.+?)\]\]\s*$', stripped)
        if m:
            out.append(f'rectangle "{decode_entities(m.group(2))}" as {m.group(1)} <<subroutine>>')
            continue
        m = re.match(r'^(\S+?)\(\((.+?)\)\)\s*$', stripped)
        if m:
            out.append(f'usecase "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue
        m = re.match(r'^(\S+?)\{(.+?)\}\s*$', stripped)
        if m:
            out.append(f'agent "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue
        m = re.match(r'^(\S+?)\("(.+?)"\)\s*$', stripped)
        if m:
            out.append(f'component "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue
        m = re.match(r'^(\S+?)\((.+?)\)\s*$', stripped)
        if m:
            out.append(f'component "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue
        m = re.match(r'^(\S+?)\["(.+?)"\]\s*$', stripped)
        if m:
            out.append(f'component "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue
        m = re.match(r'^(\S+?)\[(.+?)\]\s*$', stripped)
        if m:
            out.append(f'component "{decode_entities(m.group(2))}" as {m.group(1)}')
            continue

        # Fallback: keep line (comment marker for manual fix)
        out.append(f"' [mermaid-fallback] {L}")

    if pending_styles_cut:
        out.append("' [styles stripped — PlantUML has different syntax]")
    out.append("@enduml")
    return "\n".join(out)


def convert_block(mermaid_body: str) -> str:
    """Dispatch conversion based on first non-empty line."""
    lines = [l for l in mermaid_body.splitlines() if l.strip()]
    if not lines:
        return "@startuml\n@enduml"
    head = lines[0].strip()
    if head == "sequenceDiagram":
        return convert_sequence(mermaid_body)
    if head in ("stateDiagram-v2", "stateDiagram"):
        return convert_state(mermaid_body)
    if head == "classDiagram":
        return convert_class(mermaid_body)
    if head == "erDiagram":
        return convert_er(mermaid_body)
    if re.match(r"^(flowchart|graph)\s+(TB|LR|TD|BT|RL)\s*$", head):
        return convert_flowchart(mermaid_body)
    # Unknown: wrap as-is
    return "@startuml\n' [unrecognized mermaid type — manual review]\n" + mermaid_body + "\n@enduml"


def process_file(path: str) -> int:
    with open(path) as f:
        content = f.read()

    # Match ```mermaid ... ``` (non-greedy)
    pattern = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)

    count = 0

    def _replace(match):
        nonlocal count
        count += 1
        body = match.group(1)
        converted = convert_block(body)
        return f"```plantuml\n{converted}\n```"

    new_content = pattern.sub(_replace, content)

    if count > 0:
        with open(path, "w") as f:
            f.write(new_content)
    return count


if __name__ == "__main__":
    targets = []
    for root, _, files in os.walk(BASE):
        for fn in files:
            if fn.endswith(".md"):
                targets.append(os.path.join(root, fn))

    total_blocks = 0
    changed_files = 0
    for p in sorted(targets):
        n = process_file(p)
        if n:
            rel = os.path.relpath(p, BASE)
            print(f"✓ {rel}: {n} blocks")
            total_blocks += n
            changed_files += 1

    print(f"\n=== Total: {total_blocks} Mermaid blocks converted in {changed_files} files ===")
