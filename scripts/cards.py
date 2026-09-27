"""Project cards, the BOM (stack) panel and the footer rover.

Every fact on a card is taken from that repo's README or source tree.
"""
import math

from svgkit import SVG, C, measure

CW, CH = 600, 334
GUTTER = 28  # transparent gap baked into each card so the grid breathes


def _wrap(key, text, size, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if measure(key, t, size) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# ---- little animated glyphs (drawn in a 140 x 90 box) -----------------------------
def g_sar():
    m, o, a, st = C["mute"], C["orange"], C["amber"], C["steel2"]
    pts = "0,80 16,72 28,76 44,54 56,62 68,40 82,58 96,49 110,68 124,63 140,74"
    dur = "4.8s"
    return (
        f'<defs><clipPath id="sarclip"><rect x="0" y="0" height="90" width="0">'
        f'<animate attributeName="width" values="0;140;140" keyTimes="0;0.85;1" dur="{dur}" repeatCount="indefinite"/>'
        f'</rect></clipPath></defs>'
        f'<polyline points="{pts}" fill="none" stroke="{m}" stroke-width="2" stroke-linejoin="round"/>'
        f'<polyline points="{pts}" fill="none" stroke="{o}" stroke-width="2.5" stroke-linejoin="round" clip-path="url(#sarclip)"/>'
        f'<g><animateTransform attributeName="transform" type="translate" values="0 0;140 0;140 0" keyTimes="0;0.85;1" dur="{dur}" repeatCount="indefinite"/>'
        f'<path d="M0 17L-13 84M0 17L13 84" stroke="{a}" stroke-width="1" stroke-dasharray="2 3"/>'
        f'<rect x="-12" y="7" width="8" height="5" fill="{st}"/><rect x="4" y="7" width="8" height="5" fill="{st}"/>'
        f'<rect x="-4" y="4" width="8" height="11" rx="1.5" fill="{C["steel"]}"/>'
        f'</g>'
    )


def g_lane():
    m, o, g = C["mute"], C["orange"], C["line"]
    out = [f'<path d="M6 90L62 18M134 90L78 18" stroke="{m}" stroke-width="2"/>']
    # road seams rushing toward the camera (perspective)
    for i in range(4):
        b = f"{i * 0.35:.2f}s"
        out.append(
            f'<line x1="62" y1="18" x2="78" y2="18" stroke="{g}" stroke-width="2">'
            f'<animate attributeName="y1" values="18;90" dur="1.4s" begin="-{b}" repeatCount="indefinite" keySplines="0.6 0 1 1" calcMode="spline" keyTimes="0;1"/>'
            f'<animate attributeName="y2" values="18;90" dur="1.4s" begin="-{b}" repeatCount="indefinite" keySplines="0.6 0 1 1" calcMode="spline" keyTimes="0;1"/>'
            f'<animate attributeName="x1" values="62;6" dur="1.4s" begin="-{b}" repeatCount="indefinite" keySplines="0.6 0 1 1" calcMode="spline" keyTimes="0;1"/>'
            f'<animate attributeName="x2" values="78;134" dur="1.4s" begin="-{b}" repeatCount="indefinite" keySplines="0.6 0 1 1" calcMode="spline" keyTimes="0;1"/>'
            f'</line>')
    sway = "34,90 64,22 76,22 106,90;24,90 60,22 72,22 96,90;42,90 68,22 80,22 114,90;34,90 64,22 76,22 106,90"
    out.append(f'<polygon points="34,90 64,22 76,22 106,90" fill="none" stroke="{o}" stroke-width="2.5" stroke-linejoin="round">'
               f'<animate attributeName="points" values="{sway}" dur="5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.33;0.66;1" keySplines="0.45 0 0.55 1;0.45 0 0.55 1;0.45 0 0.55 1"/></polygon>')
    out.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;-6 0;6 0;0 0" dur="5s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.33;0.66;1" keySplines="0.45 0 0.55 1;0.45 0 0.55 1;0.45 0 0.55 1"/>'
               f'<path d="M63 12L70 5L77 12" fill="none" stroke="{o}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return "".join(out)


def g_rail():
    m, o, a, st = C["mute"], C["orange"], C["amber"], C["steel2"]
    N = {"A": (8, 72), "B": (38, 28), "C": (74, 56), "D": (104, 18), "E": (132, 64)}
    edges = ["AB", "BC", "CD", "DE", "CE", "BD"]
    out = [f'<path d="{" ".join(f"M{N[e[0]][0]} {N[e[0]][1]}L{N[e[1]][0]} {N[e[1]][1]}" for e in edges)}" stroke="{m}" stroke-width="2"/>']
    route = f"M{N['A'][0]} {N['A'][1]}L{N['B'][0]} {N['B'][1]}L{N['C'][0]} {N['C'][1]}L{N['E'][0]} {N['E'][1]}"
    out.append(f'<path d="{route}" fill="none" stroke="{o}" stroke-width="2" stroke-dasharray="3 4" opacity="0.9"/>')
    out.append(f'<circle cx="{N["D"][0]}" cy="{N["D"][1]}" r="5" fill="none" stroke="{a}" stroke-width="2">'
               f'<animate attributeName="r" values="5;13" dur="1.6s" repeatCount="indefinite"/>'
               f'<animate attributeName="opacity" values="1;0" dur="1.6s" repeatCount="indefinite"/></circle>')
    for k, (x, y) in N.items():
        fill = a if k == "D" else C["bg"]
        out.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{fill}" stroke="{st}" stroke-width="2"/>')
    out.append(f'<g><rect x="-8" y="-4" width="16" height="8" rx="2" fill="{o}"/>'
               f'<animateMotion dur="4.2s" repeatCount="indefinite" rotate="auto" path="{route}" '
               f'keyPoints="0;1;1" keyTimes="0;0.85;1" calcMode="linear"/></g>')
    return "".join(out)


def g_sentinel():
    m, o, a, st, g = C["mute"], C["orange"], C["amber"], C["steel2"], C["grid"]
    grid = "".join(f"M{x} 2V88" for x in range(4, 140, 16)) + "".join(f"M0 {y}H140" for y in range(6, 90, 16))
    route = "M22 72V46H74V24H116"
    L = 26 + 52 + 22 + 42
    return (
        f'<path d="{grid}" stroke="{g}" stroke-width="1"/>'
        f'<path d="M0 46H140M74 0V90M0 72H60" stroke="{C["line"]}" stroke-width="3"/>'
        f'<path d="{route}" fill="none" stroke="{o}" stroke-width="2.5" stroke-dasharray="{L}" stroke-dashoffset="{L}">'
        f'<animate attributeName="stroke-dashoffset" values="{L};0;0" keyTimes="0;0.55;1" dur="3.6s" repeatCount="indefinite"/></path>'
        f'<rect x="14" y="64" width="16" height="16" rx="2" fill="{C["bg"]}" stroke="{st}" stroke-width="2"/>'
        f'<path d="M18 72h8M22 68v8" stroke="{o}" stroke-width="2"/>'
        f'<circle cx="116" cy="24" r="4" fill="none" stroke="{a}" stroke-width="2">'
        f'<animate attributeName="r" values="4;18" dur="1.4s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="1;0" dur="1.4s" repeatCount="indefinite"/></circle>'
        f'<circle cx="116" cy="24" r="5" fill="{a}"/>'
        f'<circle r="3.5" fill="{C["ink"]}"><animateMotion dur="3.6s" repeatCount="indefinite" path="{route}" '
        f'keyPoints="0;1;1" keyTimes="0;0.55;1" calcMode="linear"/></circle>'
    )


def g_airnote():
    st, o, m = C["steel2"], C["orange"], C["mute"]
    strokes = [
        ("M16 40C22 40 22 16 28 14C31 13 32 16 31 18M22 40C19 42 15 41 16 38", 70),
        ("M38 30L50 30M44 24L44 36", 26),
        ("M58 22L66 38M66 22L58 38M69 20C71 16 76 17 73 23L69 26H76", 52),
        ("M86 28H100M86 33H100", 30),
        ("M108 38C108 24 124 24 124 32C124 38 112 38 112 32", 50),
    ]
    out = [f'<rect x="4" y="4" width="132" height="52" rx="3" fill="none" stroke="{st}" stroke-width="2"/>']
    n = len(strokes)
    for i, (d, L) in enumerate(strokes):
        t0 = i / (n + 2)
        t1 = (i + 1) / (n + 2)
        out.append(f'<path d="{d}" fill="none" stroke="{C["ink"]}" stroke-width="2" stroke-linecap="round" '
                   f'stroke-dasharray="{L}" stroke-dashoffset="{L}">'
                   f'<animate attributeName="stroke-dashoffset" values="{L};{L};0;0;{L}" '
                   f'keyTimes="0;{t0:.3f};{t1:.3f};0.96;1" dur="6s" repeatCount="indefinite"/></path>')
    for i in range(16):
        x = 10 + i * 8
        h1, h2 = 4 + (i * 7) % 11, 14 - (i * 5) % 10
        dur = 0.7 + (i % 5) * 0.13
        out.append(f'<rect x="{x}" width="4" rx="1" fill="{o if i % 4 == 1 else m}" y="{76 - h1/2}" height="{h1}">'
                   f'<animate attributeName="height" values="{h1};{h2};{h1}" dur="{dur:.2f}s" repeatCount="indefinite"/>'
                   f'<animate attributeName="y" values="{76-h1/2};{76-h2/2};{76-h1/2}" dur="{dur:.2f}s" repeatCount="indefinite"/></rect>')
    return "".join(out)


def g_triage():
    o, m, a = C["orange"], C["mute"], C["amber"]
    d = "M0 34H30L36 26L42 34H52L57 8L63 52L68 34H84L90 28L96 34H140"
    L = 200
    out = [f'<path d="M0 34H140" stroke="{C["line"]}" stroke-width="1"/>',
           f'<path d="{d}" fill="none" stroke="{o}" stroke-width="2.5" stroke-linejoin="round" '
           f'stroke-dasharray="{L}" stroke-dashoffset="{L}">'
           f'<animate attributeName="stroke-dashoffset" values="{L};0;0;{-L}" keyTimes="0;0.6;0.8;1" dur="2.6s" repeatCount="indefinite"/></path>']
    return "".join(out)


def triage_labels(s):
    """P1/P2/P3 chips need text, so they are drawn with the SVG helper."""
    m, a, bg = C["mute"], C["amber"], C["bg"]
    out = []
    for i, lab in enumerate(["P1", "P2", "P3"]):
        x = 6 + i * 46
        kt = f"0;{i/3:.3f};{(i+1)/3:.3f};1"
        out.append(f'<rect x="{x}" y="64" width="40" height="22" rx="4" fill="{bg}" stroke="{m}" stroke-width="1.5">'
                   f'<animate attributeName="fill" values="{bg};{a};{bg};{bg}" keyTimes="{kt}" '
                   f'calcMode="discrete" dur="3.6s" repeatCount="indefinite"/></rect>')
        out.append(s.text(x + 20, 79.5, lab, "monob", 12, C["dim"], anchor="middle",
                          extra="")[:-7] +
                   f'<animate attributeName="fill" values="{C["dim"]};{bg};{C["dim"]};{C["dim"]}" keyTimes="{kt}" '
                   f'calcMode="discrete" dur="3.6s" repeatCount="indefinite"/></text>')
    return "".join(out)


GLYPHS = {"sar": g_sar, "lane": g_lane, "rail": g_rail, "sentinel": g_sentinel,
          "airnote": g_airnote, "triage": g_triage}

PROJECTS = [
    dict(slug="sar2optical-terrain-india", glyph="sar", idx="01",
         label="REMOTE SENSING  ·  RESEARCH", title="SAR → OPTICAL",
         sub="Does Sentinel-1 → Sentinel-2 translation break on Indian terrain?",
         stats=[("15", "sites across five Indian regions"),
                ("+68%", "error on radar-shadow pixels"),
                ("≈ 0", "gain from adding a DEM input")],
         chips=["Python", "Earth Engine", "U-Net", "Sentinel-1/2"], live=False),
    dict(slug="Lane-Detection", glyph="lane", idx="02",
         label="COMPUTER VISION  ·  AUTONOMY", title="LANE DETECTION",
         sub="Drivable lanes and junctions on roads with no lane markings.",
         stats=[("~50 fps", "640×360 on an RTX 3050 laptop"),
                ("4 of 7", "frames to confirm a junction"),
                ("0", "training runs, pretrained only")],
         chips=["PyTorch", "OpenCV", "YOLOPv2", "RANSAC"], live=False),
    dict(slug="Railmind", glyph="rail", idx="03",
         label="AGENTS  ·  DIGITAL TWIN", title="RAILMIND",
         sub="A rail-network twin where LangGraph agents plan incident responses.",
         stats=[("21", "stations, 33 corridors"),
                ("L0–L4", "escalation ladder"),
                ("206", "backend + console tests")],
         chips=["LangGraph", "Django", "FastAPI", "React 19"], live=True),
    dict(slug="SentinelAI", glyph="sentinel", idx="04",
         label="ML  ·  EMERGENCY RESPONSE", title="SENTINELAI",
         sub="Incident copilot for dispatch: prediction, risk and history.",
         stats=[("CatBoost", "prediction models"),
                ("FAISS", "similarity search on past incidents"),
                ("Whisper", "speech-to-text")],
         chips=["Flask", "CatBoost", "FAISS", "Redis"], live=False),
    dict(slug="AirNote", glyph="airnote", idx="05",
         label="ON-DEVICE AI  ·  ANDROID", title="AIRNOTE",
         sub="Board + lecturer's voice fused into timed notes, fully on-device.",
         stats=[("0", "cloud calls, runs offline"),
                ("INT4", "LLM on the Snapdragon NPU"),
                ("3", "pipelines: vision, audio, fusion")],
         chips=["Kotlin", "CameraX", "OpenCV", "Whisper"], live=True),
    dict(slug="Pragyan_Hackathon", glyph="triage", idx="06",
         label="HEALTH ML  ·  HACKATHON", title="MEDICAL TRIAGE",
         sub="Multimodal triage from voice, text and EHR, with explanations.",
         stats=[("CTGAN", "synthetic patient records"),
                ("RF + XGB", "random forest, XGBoost"),
                ("SHAP", "why each patient was ranked")],
         chips=["XGBoost", "SHAP", "React", "Node.js"], live=True),
]


def card(p, side="left"):
    """side='left' leaves the gutter on the right, 'right' leaves it on the left,
    so a pair at 50% width lines up flush with the full-width panels."""
    svg = _card(p)
    head_old = f'width="{CW}" height="{CH}" viewBox="0 0 {CW} {CH}"'
    vx = 0 if side == "left" else -GUTTER
    head_new = f'width="{CW+GUTTER}" height="{CH}" viewBox="{vx} 0 {CW+GUTTER} {CH}"'
    assert head_old in svg
    return svg.replace(head_old, head_new, 1)


def _card(p):
    s = SVG(CW, CH, f"{p['title']}: {p['sub']}",
            f"{p['label']}. " + "; ".join(f"{v} {k}" for v, k in p["stats"]) + ". Stack: " + ", ".join(p["chips"]))
    ink, dim, mute, line, org = C["ink"], C["dim"], C["mute"], C["line"], C["orange"]
    s.add(f'<rect x="1" y="1" width="{CW-2}" height="{CH-2}" rx="14" fill="{C["bg"]}" stroke="{line}" stroke-width="1.5"/>')
    s.put_text(28, 42, p["idx"], "monob", 14, org)
    s.put_text(60, 42, p["label"], "mono", 13, dim, spacing=1)
    s.put_text(26, 92, p["title"], "disp", 42, ink, spacing=0.5)
    subl = _wrap("sans", p["sub"], 18.5, CW - 56)
    for i, ln in enumerate(subl[:2]):
        s.put_text(28, 128 + i * 23, ln, "sans", 18.5, dim)
    extra = triage_labels(s) if p["glyph"] == "triage" else ""
    s.add(f'<g transform="translate(436 22)">{GLYPHS[p["glyph"]]()}{extra}</g>')

    y0 = 160 + (23 if len(subl) > 1 else 0)
    colw = (CW - 56) / 3
    for i, (v, k) in enumerate(p["stats"]):
        x = 28 + i * colw
        if i:
            s.add(f'<path d="M{x-14:.1f} {y0+6}V{y0+62}" stroke="{line}" stroke-width="1"/>')
        s.put_text(x, y0 + 32, v, "monob", 24, org)
        for j, ln in enumerate(_wrap("sans", k, 16.5, colw - 20)[:2]):
            s.put_text(x, y0 + 56 + j * 19, ln, "sans", 16.5, dim)

    s.add(f'<path d="M28 {CH-58}H{CW-28}" stroke="{line}" stroke-width="1"/>')
    cx = 28
    for ch in p["chips"]:
        w = measure("mono", ch, 14) + 20
        s.add(f'<rect x="{cx}" y="{CH-45}" width="{w:.1f}" height="29" rx="4" fill="none" stroke="{line}" stroke-width="1.5"/>')
        s.put_text(cx + 10, CH - 25.5, ch, "mono", 14, C["steel"])
        cx += w + 8
    if p["live"]:
        s.add(f'<circle cx="{CW-104}" cy="{CH-30.5}" r="4.5" fill="{C["amber"]}">'
              f'<animate attributeName="opacity" values="1;0.25;1" dur="1.6s" repeatCount="indefinite"/></circle>')
        s.put_text(CW - 93, CH - 25.5, "LIVE", "monob", 14, C["amber"], spacing=1)
    s.put_text(CW - 28, CH - 24.5, "↗", "monob", 18, org, anchor="end")
    return s.render()


# ---- BOM / stack panel ---------------------------------------------------------------
BOM = [
    ("languages", ["Python", "C++", "C", "Java", "JavaScript", "TypeScript", "Kotlin"]),
    ("perception", ["PyTorch", "TensorFlow", "OpenCV", "YOLOPv2", "U-Net", "Earth Engine"]),
    ("learning", ["scikit-learn", "XGBoost", "CatBoost", "SHAP", "CTGAN", "FAISS"]),
    ("agents / backend", ["LangGraph", "FastAPI", "Django", "Flask", "Express", "Redis", "PostgreSQL", "MongoDB"]),
    ("interfaces", ["React", "Node.js", "TanStack Start", "Android / CameraX"]),
    ("hardware", ["ESP32", "Arduino", "Raspberry Pi", "GPS / TinyGPSPlus", "servos + PWM"]),
]


def bom():
    W, rowh, top = 1200, 54, 30
    H = top + rowh * len(BOM) + 8
    s = SVG(W, H, "Bill of materials: the tools I build with",
            "; ".join(f"{k}: {', '.join(v)}" for k, v in BOM))
    ink, dim, mute, line, org = C["ink"], C["dim"], C["mute"], C["line"], C["orange"]
    s.add(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{C["bg"]}" stroke="{line}" stroke-width="1.5"/>')
    n = len(BOM)
    for i, (k, items) in enumerate(BOM):
        y = top + i * rowh
        if i:
            s.add(f'<path d="M32 {y-11}H{W-32}" stroke="{C["grid"]}" stroke-width="1"/>')
        # status LED that scans down the rows like a panel self-test
        keyt = f"0;{i/n:.3f};{(i+1)/n:.3f};1" if i < n - 1 else f"0;{i/n:.3f};1"
        vals = f"{mute};{org};{mute};{mute}" if i < n - 1 else f"{mute};{org};{mute}"
        s.add(f'<circle cx="40" cy="{y+16}" r="4.5" fill="{mute}"><animate attributeName="fill" dur="3.6s" repeatCount="indefinite" '
              f'calcMode="discrete" keyTimes="{keyt}" values="{vals}"/></circle>')
        s.put_text(60, y + 21, k, "monob", 16, ink)
        cx = 260
        for it in items:
            w = measure("mono", it, 15) + 22
            s.add(f'<rect x="{cx}" y="{y}" width="{w:.1f}" height="32" rx="4" fill="none" stroke="{line}" stroke-width="1.5"/>')
            s.put_text(cx + 11, y + 21, it, "mono", 15, C["steel"])
            cx += w + 8
    return s.render()


# ---- footer: an AGV rolling a finished block off the line --------------------------------
def footer():
    W, H = 1200, 100
    s = SVG(W, H, "End of page", "A small wheeled robot with a spinning lidar carries an orange block along the floor line.")
    line, mute, org, st, st2 = C["line"], C["mute"], C["orange"], C["steel"], C["steel2"]
    floor = 80
    s.defs.append(f'<clipPath id="fr"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14"/></clipPath>')
    s.add(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{C["bg"]}" stroke="{line}" stroke-width="1.5"/>')
    s.add('<g clip-path="url(#fr)">')
    ticks = "".join(f"M{x} {floor}v{6 if x % 100 == 0 else 3}" for x in range(0, W, 20))
    s.add(f'<path d="M0 {floor}H{W}" stroke="{line}" stroke-width="1.5"/><path d="{ticks}" stroke="{line}" stroke-width="1"/>')
    travel, dur = W + 240, 14.0
    r = 9
    spin = 2 * math.pi * r / (travel / dur)
    wheel = lambda cx: (f'<g transform="translate({cx} {floor-r})"><g>'
                        f'<animateTransform attributeName="transform" type="rotate" values="0;360" dur="{spin:.3f}s" repeatCount="indefinite"/>'
                        f'<circle r="{r}" fill="{C["bg"]}" stroke="{st}" stroke-width="3"/>'
                        f'<path d="M-{r-3} 0H{r-3}M0 -{r-3}V{r-3}" stroke="{st2}" stroke-width="2"/></g></g>')
    agv = (
        f'<g><animateTransform attributeName="transform" type="translate" values="-140 0;{W+100} 0" dur="{dur}s" repeatCount="indefinite"/>'
        f'<rect x="0" y="{floor-38}" width="84" height="22" rx="4" fill="{st}" stroke="{C["bg"]}" stroke-width="2"/>'
        f'<rect x="0" y="{floor-24}" width="84" height="5" fill="{org}"/>'
        f'<rect x="54" y="{floor-33}" width="18" height="6" rx="1.5" fill="{C["bg"]}"/>'
        f'<circle cx="63" cy="{floor-30}" r="1.8" fill="{org}"><animate attributeName="opacity" values="1;0.2;1" dur="0.8s" repeatCount="indefinite"/></circle>'
        f'<rect x="12" y="{floor-64}" width="26" height="26" rx="3" fill="{org}"/>'
        f'<rect x="19" y="{floor-57}" width="12" height="12" rx="1.5" fill="{C["orange_dk"]}"/>'
        f'<rect x="60" y="{floor-46}" width="14" height="8" rx="2" fill="{st2}"/>'
        f'<g transform="translate(67 {floor-46})"><g><animateTransform attributeName="transform" type="rotate" values="0;360" dur="1.2s" repeatCount="indefinite"/>'
        f'<path d="M0 0L34 -10" stroke="{C["amber"]}" stroke-width="1.2" stroke-dasharray="2 3"/></g></g>'
        + wheel(18) + wheel(66) + "</g>"
    )
    s.add(agv)
    s.add("</g>")
    return s.render()


# ---- contact buttons ---------------------------------------------------------------------
def _icon(kind, c):
    if kind == "web":
        return (f'<rect x="0" y="1" width="22" height="18" rx="3" fill="none" stroke="{c}" stroke-width="2"/>'
                f'<path d="M0 6.5H22" stroke="{c}" stroke-width="2"/><circle cx="4" cy="3.8" r="1" fill="{c}"/>'
                f'<path d="M5 11h8M5 15h12" stroke="{c}" stroke-width="1.6"/>')
    if kind == "profile":
        return (f'<rect x="0" y="1" width="22" height="18" rx="3" fill="none" stroke="{c}" stroke-width="2"/>'
                f'<circle cx="7" cy="8" r="2.6" fill="{c}"/><path d="M3 15.5c1-3 7-3 8 0" stroke="{c}" stroke-width="1.8" fill="none"/>'
                f'<path d="M13 8h6M13 12h6" stroke="{c}" stroke-width="1.6"/>')
    return (f'<rect x="0" y="2" width="22" height="16" rx="2.5" fill="none" stroke="{c}" stroke-width="2"/>'
            f'<path d="M1 4l10 7 10-7" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>')


def button(label, icon):
    size, h = 15, 52
    tw = measure("monob", label, size, 1.5)
    w = int(20 + 22 + 14 + tw + 16 + 14 + 20)
    s = SVG(w, h, label, label)
    s.add(f'<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="10" fill="{C["bg"]}" stroke="{C["line"]}" stroke-width="1.5"/>')
    s.add(f'<g transform="translate(20 {h/2-10})">{_icon(icon, C["orange"])}</g>')
    s.put_text(56, h / 2 + 5.5, label, "monob", size, C["ink"], spacing=1.5)
    s.put_text(w - 20, h / 2 + 6, "↗", "monob", 17, C["orange"], anchor="end")
    return s.render()


BUTTONS = [("btn-portfolio.svg", "PORTFOLIO", "web"),
           ("btn-linkedin.svg", "LINKEDIN", "profile"),
           ("btn-email.svg", "EMAIL", "mail")]
