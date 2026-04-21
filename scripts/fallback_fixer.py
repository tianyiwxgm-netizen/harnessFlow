#!/usr/bin/env python3
"""Fix `' [mermaid-fallback]` markers in PlantUML blocks by converting leftover Mermaid syntax."""
import os, re, glob, html

BASE = "/Users/zhongtianyi/work/code/harnessFlow/docs/3-1-Solution-Technical"


def decode_entities(s: str) -> str:
    s = s.replace("<br/>", "\\n").replace("<br>", "\\n").replace("<BR/>", "\\n")
    s = re.sub(r"<b>(.+?)</b>", r"<b>\1</b>", s)  # PlantUML supports <b>
    s = html.unescape(s)
    return s


def fix_mermaid_line(line: str) -> list[str]:
    """Convert one Mermaid line into one or more PlantUML lines."""
    stripped = line.strip()
    if not stripped:
        return [""]

    # Remove leading/trailing comment wrappers if caller didn't
    results: list[str] = []

    # 1) Edge with dotted label: A -.label.-> B  /  A -.label.- B
    m = re.match(r"^(\S+)\s*-\.\s*(.+?)\s*\.->\s*(\S+)(.*)$", stripped)
    if m:
        src, label, dst, rest = m.groups()
        results.append(f"{src} ..> {dst} : {decode_entities(label)}")
        return results

    # 2) Edge with thick label: A ==label==> B["name"]
    m = re.match(r"^(\S+)\s*==\s*(.+?)\s*==>\s*(\S+?)(?:\[(.*?)\])?\s*$", stripped)
    if m:
        src, label, dst, dst_lbl = m.groups()
        if dst_lbl:
            results.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} ==> {dst} : {decode_entities(label)}")
        return results

    # 3) Simple thick edge: A ==> B
    m = re.match(r"^(\S+)\s*==>\s*(\S+?)(?:\[(.*?)\])?\s*$", stripped)
    if m:
        src, dst, dst_lbl = m.groups()
        if dst_lbl:
            results.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} ==> {dst}")
        return results

    # 4) End-with-x edge: A --x B   (PlantUML has [bold] or red arrow as substitute)
    m = re.match(r"^(\S+)\s*--x\s*(\S+)(.*)$", stripped)
    if m:
        src, dst, rest = m.groups()
        results.append(f"{src} -[#red]-> {dst}")
        return results

    # 5) Node only: A(["label"])  /  A([label])  — sausage / stadium shape
    m = re.match(r'^(\S+?)\(\[\s*"(.+?)"\s*\]\)\s*(?:-->|==>|->|\.->)?\s*(.*)$', stripped)
    if m:
        node, label, rest = m.groups()
        results.append(f'usecase "{decode_entities(label)}" as {node}')
        if rest.strip():
            # rest may still contain edge + target
            for sub in fix_mermaid_line(f"{node} {rest.strip()}"):
                results.append(sub)
        return results
    m = re.match(r'^(\S+?)\(\[(.+?)\]\)\s*(?:-->|==>|->|\.->)?\s*(.*)$', stripped)
    if m:
        node, label, rest = m.groups()
        results.append(f'usecase "{decode_entities(label)}" as {node}')
        if rest.strip():
            for sub in fix_mermaid_line(f"{node} {rest.strip()}"):
                results.append(sub)
        return results

    # 6) Edge with pipe label: A -->|label| B["name"]
    m = re.match(r"^(\S+)\s*(-.->|-->|==>|---|\.->)\s*\|\s*(.+?)\s*\|\s*(\S+?)(?:\[(.*?)\])?\s*$", stripped)
    if m:
        src, arrow, label, dst, dst_lbl = m.groups()
        arrow_map = {"-->": "-->", "-.->": "..>", "==>": "==>", "---": "--", ".->": "..>"}
        parrow = arrow_map.get(arrow, "-->")
        if dst_lbl:
            results.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} {parrow} {dst} : {decode_entities(label)}")
        return results

    # 7) Edge with inline labels on both sides: A[label1] --> B[label2]
    m = re.match(
        r'^(\S+?)(?:\["(.+?)"\]|\[(.+?)\])?\s*(-.->|-->|==>|---|\.->)\s*(\S+?)(?:\["(.+?)"\]|\[(.+?)\])?\s*$',
        stripped,
    )
    if m:
        src, src_lbl_q, src_lbl, arrow, dst, dst_lbl_q, dst_lbl = m.groups()
        src_lbl = src_lbl_q or src_lbl
        dst_lbl = dst_lbl_q or dst_lbl
        arrow_map = {"-->": "-->", "-.->": "..>", "==>": "==>", "---": "--", ".->": "..>"}
        parrow = arrow_map.get(arrow, "-->")
        if src_lbl:
            results.append(f'component "{decode_entities(src_lbl)}" as {src}')
        if dst_lbl:
            results.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} {parrow} {dst}")
        return results

    # 8) Decision node alone: A{"label"}  /  A{label}
    m = re.match(r'^(\S+?)\{\s*"(.+?)"\s*\}\s*$', stripped)
    if m:
        results.append(f'agent "{decode_entities(m.group(2))}" as {m.group(1)}')
        return results
    m = re.match(r"^(\S+?)\{(.+?)\}\s*$", stripped)
    if m:
        results.append(f'agent "{decode_entities(m.group(2))}" as {m.group(1)}')
        return results

    # 9) Edge with decision node on dst: A --> B{"label"}
    m = re.match(r'^(\S+)\s*(-.->|-->|==>|---|\.->)\s*(\S+?)\{\s*"(.+?)"\s*\}\s*$', stripped)
    if m:
        src, arrow, dst, dst_lbl = m.groups()
        arrow_map = {"-->": "-->", "-.->": "..>", "==>": "==>", "---": "--", ".->": "..>"}
        parrow = arrow_map.get(arrow, "-->")
        results.append(f'agent "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} {parrow} {dst}")
        return results
    m = re.match(r"^(\S+)\s*(-.->|-->|==>|---|\.->)\s*(\S+?)\{(.+?)\}\s*$", stripped)
    if m:
        src, arrow, dst, dst_lbl = m.groups()
        arrow_map = {"-->": "-->", "-.->": "..>", "==>": "==>", "---": "--", ".->": "..>"}
        parrow = arrow_map.get(arrow, "-->")
        results.append(f'agent "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} {parrow} {dst}")
        return results

    # 10) Dash-label edge: A -- label --> B
    m = re.match(r"^(\S+)\s*--\s*(.+?)\s*-->\s*(\S+?)(?:\[(.*?)\])?\s*$", stripped)
    if m:
        src, label, dst, dst_lbl = m.groups()
        if dst_lbl:
            results.append(f'component "{decode_entities(dst_lbl)}" as {dst}')
        results.append(f"{src} --> {dst} : {decode_entities(label)}")
        return results

    # Unknown: keep original as PlantUML note comment with clearer prefix
    return [f"' [needs-manual-fix] {stripped}"]


def process_file(path: str) -> tuple[int, int]:
    """Return (fixed_lines, still_fallback)."""
    with open(path) as f:
        content = f.read()

    lines = content.splitlines(keepends=False)
    new_lines: list[str] = []
    fixed = 0
    still = 0

    for line in lines:
        m = re.match(r"^(\s*)'\s*\[mermaid-fallback\]\s+(.+)$", line)
        if m:
            indent, body = m.groups()
            converted = fix_mermaid_line(body)
            # Check if converter succeeded
            if converted and any("needs-manual-fix" not in c for c in converted):
                for c in converted:
                    new_lines.append(f"{indent}{c}" if c else "")
                fixed += 1
                continue
            still += 1
        # Also clean up "' [styles stripped — PlantUML has different syntax]" (keep or drop? drop)
        if re.match(r"^\s*'\s*\[styles stripped.*\]$", line):
            continue
        new_lines.append(line)

    if fixed > 0 or still > 0:
        with open(path, "w") as f:
            f.write("\n".join(new_lines) + ("\n" if content.endswith("\n") else ""))
    return fixed, still


if __name__ == "__main__":
    total_fixed = 0
    total_still = 0
    for root, _, files in os.walk(BASE):
        for fn in files:
            if not fn.endswith(".md"):
                continue
            p = os.path.join(root, fn)
            fx, st = process_file(p)
            if fx or st:
                rel = os.path.relpath(p, BASE)
                print(f"✓ {rel}: fixed={fx} still={st}")
                total_fixed += fx
                total_still += st
    print(f"\n=== Total: fixed {total_fixed} · still need manual {total_still} ===")
