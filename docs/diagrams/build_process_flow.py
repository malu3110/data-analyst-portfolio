"""Generate docs/process-flow.drawio (As-Is and To-Be swimlanes) and SVG previews.

Run: python docs/diagrams/build_process_flow.py
Open the .drawio file at https://app.diagrams.net to edit.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT_DIR = Path(__file__).resolve().parent.parent

LABEL_W, COL_W, LANE_H = 150, 170, 130
BOX_W, BOX_H = 140, 74

STYLE = {
    "step": "rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;fontSize=11;",
    "system": "rounded=1;whiteSpace=wrap;html=1;fillColor=#d5e8d4;strokeColor=#82b366;fontSize=11;",
    "decision": "rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;strokeColor=#d6b656;fontSize=10;",
    "pain": "shape=note;whiteSpace=wrap;html=1;size=12;fillColor=#f8cecc;strokeColor=#b85450;fontSize=10;align=left;spacingLeft=4;",
    "end": "ellipse;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontSize=10;",
}
FILL = {
    "step": ("#dae8fc", "#6c8ebf"), "system": ("#d5e8d4", "#82b366"),
    "decision": ("#fff2cc", "#d6b656"), "pain": ("#f8cecc", "#b85450"),
    "end": ("#f5f5f5", "#666666"),
}

AS_IS = {
    "name": "As-Is (assumed)",
    "title": "AS-IS (assumed process, design exercise): crossing chosen from a single live snapshot",
    "lanes": ["Customer (shipper)", "Dispatcher", "Driver", "CBP wait-time website"],
    "nodes": [
        ("a1", 0, 0, "step", "Tender cross-border load with delivery window"),
        ("a2", 1, 1, "step", "Assign driver; pick crossing (habitual default)"),
        ("a3", 1, 2, "step", "Check current wait for that one crossing"),
        ("a3s", 3, 2, "system", "Shows current snapshot only (no history)"),
        ("a4", 2, 3, "step", "Drive to crossing; join commercial queue"),
        ("a5", 2, 4, "decision", "Queue much longer than expected?"),
        ("a7", 1, 5, "step", "Driver phones in; revise ETA manually"),
        ("a8", 0, 6, "step", "Receives late, reactive ETA change"),
        ("a9", 2, 6, "end", "Cross (eventually); continue to delivery"),
    ],
    "edges": [
        ("a1", "a2", ""), ("a2", "a3", ""), ("a3", "a3s", "looks up"),
        ("a3", "a4", "release"), ("a4", "a5", ""), ("a5", "a7", "Yes"),
        ("a5", "a9", "No / after wait"), ("a7", "a8", "phone/email"),
    ],
    "pains": [
        "PP1 Snapshot only: no view of wait at arrival hour",
        "PP2 Crossing chosen by habit, not comparison",
        "PP3 Delays never recorded: no learning",
        "PP4 ETA changes are reactive and phone-driven",
    ],
}

TO_BE = {
    "name": "To-Be (proposed)",
    "title": "TO-BE (proposed): history captured hourly; dispatcher compares crossings before release",
    "lanes": ["Customer (shipper)", "Dispatcher / Planner", "Driver",
              "Pipeline (hourly)", "Dashboard (public app)"],
    "nodes": [
        ("b1", 3, 0, "system", "Hourly: fetch CBP commercial-lane snapshot"),
        ("b2", 3, 1, "system", "Store raw snapshot in Postgres (idempotent)"),
        ("b3", 3, 2, "system", "Transform: clean, flag stale/missing, hourly patterns"),
        ("b4", 4, 3, "system", "Current + typical wait by crossing & hour; freshness"),
        ("b5", 0, 3, "step", "Tender load with delivery window"),
        ("b6", 1, 4, "step", "Compare candidate crossings for planned arrival hour"),
        ("b7", 1, 5, "step", "Choose crossing; set ETA incl. border buffer"),
        ("b8", 2, 5, "end", "Cross at chosen crossing"),
        ("b9", 0, 6, "step", "Receives ETA that already includes border"),
        ("b10", 1, 7, "step", "Weekly: review crossing reliability & FAST savings"),
    ],
    "edges": [
        ("b1", "b2", ""), ("b2", "b3", ""), ("b3", "b4", ""), ("b5", "b6", ""),
        ("b4", "b6", "informs"), ("b6", "b7", ""), ("b7", "b8", ""),
        ("b7", "b9", ""), ("b4", "b10", "weekly view"),
    ],
    "pains": [
        "Addresses PP1 via US-06 (typical wait by hour)",
        "Addresses PP2 via US-07 (compare crossings)",
        "Addresses PP3 via US-04/US-09 (history, quality)",
        "Human decides; dashboard informs (no auto-routing)",
    ],
}


def layout(page):
    n_cols = 1 + max(c for _, _, c, _, _ in page["nodes"])
    width = LABEL_W + n_cols * COL_W + 20
    top = 50
    pos = {}
    for nid, lane, col, kind, _ in page["nodes"]:
        x = LABEL_W + col * COL_W + (COL_W - BOX_W) / 2
        y = top + lane * LANE_H + (LANE_H - BOX_H) / 2
        pos[nid] = (x, y, kind)
    lanes_h = len(page["lanes"]) * LANE_H
    pain_y = top + lanes_h + 20
    return width, top, lanes_h, pain_y, pos


def drawio_page(page, page_id):
    width, top, lanes_h, pain_y, pos = layout(page)
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    cells.append(
        f'<mxCell id="{page_id}-title" value="{escape(page["title"])}" '
        'style="text;html=1;fontSize=15;fontStyle=1;align=left;verticalAlign=middle;" '
        f'vertex="1" parent="1"><mxGeometry x="0" y="5" width="{width}" height="35" as="geometry"/></mxCell>'
    )
    for i, lane in enumerate(page["lanes"]):
        y = top + i * LANE_H
        cells.append(
            f'<mxCell id="{page_id}-lane{i}" value="{escape(lane)}" '
            'style="swimlane;horizontal=0;startSize=' + str(LABEL_W - 10) + ';html=1;fontSize=12;'
            f'fillColor={"#f5f5f5" if i % 2 == 0 else "#ffffff"};swimlaneFillColor=none;" vertex="1" parent="1">'
            f'<mxGeometry x="0" y="{y}" width="{width}" height="{LANE_H}" as="geometry"/></mxCell>'
        )
    for nid, lane, col, kind, label in page["nodes"]:
        x, y, _ = pos[nid]
        cells.append(
            f'<mxCell id="{nid}" value="{escape(label)}" style="{STYLE[kind]}" vertex="1" parent="1">'
            f'<mxGeometry x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" as="geometry"/></mxCell>'
        )
    for i, (src, dst, label) in enumerate(page["edges"]):
        cells.append(
            f'<mxCell id="{page_id}-e{i}" value="{escape(label)}" '
            'style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;endArrow=block;fontSize=10;" '
            f'edge="1" parent="1" source="{src}" target="{dst}"><mxGeometry relative="1" as="geometry"/></mxCell>'
        )
    pw = (width - 30) / len(page["pains"])
    for i, text in enumerate(page["pains"]):
        cells.append(
            f'<mxCell id="{page_id}-p{i}" value="{escape(text)}" style="{STYLE["pain"] if page is AS_IS else STYLE["system"]}" '
            f'vertex="1" parent="1"><mxGeometry x="{i * (pw + 10)}" y="{pain_y}" width="{pw}" height="46" as="geometry"/></mxCell>'
        )
    body = "".join(cells)
    return (f'<diagram id="{page_id}" name="{escape(page["name"])}"><mxGraphModel dx="1400" dy="900" '
            f'grid="1" gridSize="10" page="1" pageWidth="{int(width) + 40}" pageHeight="{int(pain_y) + 90}">'
            f'<root>{body}</root></mxGraphModel></diagram>')


def svg_page(page):
    """Static preview with straight-line connectors (draw.io routes them properly)."""
    width, top, lanes_h, pain_y, pos = layout(page)
    h = pain_y + 70
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" '
           f'font-family="Helvetica,Arial,sans-serif"><rect width="100%" height="100%" fill="#fff"/>',
           '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
           '<path d="M0,0 L8,4 L0,8 z" fill="#333"/></marker></defs>',
           f'<text x="4" y="30" font-size="15" font-weight="bold">{escape(page["title"])}</text>']
    for i, lane in enumerate(page["lanes"]):
        y = top + i * LANE_H
        out.append(f'<rect x="0" y="{y}" width="{width}" height="{LANE_H}" fill="{"#f5f5f5" if i % 2 == 0 else "#fff"}" stroke="#999"/>')
        out.append(f'<rect x="0" y="{y}" width="{LABEL_W - 10}" height="{LANE_H}" fill="#e6e6e6" stroke="#999"/>')
        out.append(f'<text x="{(LABEL_W - 10) / 2}" y="{y + LANE_H / 2 + 4}" font-size="12" text-anchor="middle" font-weight="bold">{escape(lane)}</text>')

    def center(n):
        x, y, _ = pos[n]
        return x + BOX_W / 2, y + BOX_H / 2

    for src, dst, label in page["edges"]:
        (x1, y1), (x2, y2) = center(src), center(dst)
        # clip to box edges approximately
        dx, dy = x2 - x1, y2 - y1
        scale = lambda: min((BOX_W / 2) / abs(dx) if dx else 1e9, (BOX_H / 2) / abs(dy) if dy else 1e9)
        s = scale()
        out.append(f'<line x1="{x1 + dx * s}" y1="{y1 + dy * s}" x2="{x2 - dx * s}" y2="{y2 - dy * s}" '
                   'stroke="#333" stroke-width="1.3" marker-end="url(#arr)"/>')
        if label:
            out.append(f'<text x="{(x1 + x2) / 2 + 4}" y="{(y1 + y2) / 2 - 4}" font-size="10" fill="#333">{escape(label)}</text>')
    for nid, lane, col, kind, label in page["nodes"]:
        x, y, _ = pos[nid]
        fill, stroke = FILL[kind]
        if kind == "decision":
            cx, cy = x + BOX_W / 2, y + BOX_H / 2
            out.append(f'<polygon points="{cx},{y} {x + BOX_W},{cy} {cx},{y + BOX_H} {x},{cy}" fill="{fill}" stroke="{stroke}"/>')
        elif kind == "end":
            out.append(f'<ellipse cx="{x + BOX_W / 2}" cy="{y + BOX_H / 2}" rx="{BOX_W / 2}" ry="{BOX_H / 2}" fill="{fill}" stroke="{stroke}"/>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="8" fill="{fill}" stroke="{stroke}"/>')
        out.append(_wrapped(label, x + BOX_W / 2, y + BOX_H / 2, 22 if kind != "decision" else 16, 11 if kind != "decision" else 10))
    pw = (width - 30) / len(page["pains"])
    fill, stroke = FILL["pain"] if page is AS_IS else FILL["system"]
    for i, text in enumerate(page["pains"]):
        x = i * (pw + 10)
        out.append(f'<rect x="{x}" y="{pain_y}" width="{pw}" height="46" fill="{fill}" stroke="{stroke}"/>')
        out.append(_wrapped(text, x + pw / 2, pain_y + 23, 40, 10))
    out.append("</svg>")
    return "".join(out)


def _wrapped(text, cx, cy, max_chars, size):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > max_chars and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    start = cy - (len(lines) - 1) * (size + 2) / 2 + size / 3
    return "".join(f'<text x="{cx}" y="{start + i * (size + 2)}" font-size="{size}" text-anchor="middle">{escape(l)}</text>'
                   for i, l in enumerate(lines))


if __name__ == "__main__":
    xml = ('<mxfile host="app.diagrams.net">' + drawio_page(AS_IS, "asis") + drawio_page(TO_BE, "tobe") + "</mxfile>")
    (OUT_DIR / "process-flow.drawio").write_text(xml, encoding="utf-8")
    (OUT_DIR / "diagrams" / "as-is.svg").write_text(svg_page(AS_IS), encoding="utf-8")
    (OUT_DIR / "diagrams" / "to-be.svg").write_text(svg_page(TO_BE), encoding="utf-8")
    print("wrote process-flow.drawio, diagrams/as-is.svg, diagrams/to-be.svg")
