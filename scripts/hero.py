"""Hero banner: a 3-DOF planar arm doing pick-and-place off a conveyor.

Joint angles are solved with closed-form inverse kinematics in Python and
written out as SMIL keyframes, so the SVG itself has no scripting at all.
Transfer moves are joint-interpolated (like a PTP move on a real controller),
approach/retreat moves are straight-line Cartesian (LIN). The gripper stays
vertical the whole cycle: q3 = 90deg - q1 - q2.
"""
import math

from svgkit import SVG, C, measure

W, H = 1200, 400
DUR = 7.0  # seconds per pick-place cycle
N = 168    # keyframes per cycle

# ---- arm geometry -------------------------------------------------------
L1, L2, L3 = 128.0, 112.0, 50.0
SH = (905.0, 282.0)          # shoulder joint
BLOCK = 26.0
BELT_TOP = 336.0
GRIP_Y = BELT_TOP - BLOCK / 2   # grip centre when holding a block on a belt
FEED_X = 619.0
PICK_X, DROP_X = 765.0, 1048.0
EXIT_X = 1240.0
HOVER = 78.0

HOME = (886.0, 170.0)
PICK = (PICK_X, GRIP_Y)
PICK_H = (PICK_X, GRIP_Y - HOVER)
DROP = (DROP_X, GRIP_Y)
DROP_H = (DROP_X, GRIP_Y - HOVER)


def ik(g, sign):
    wx, wy = g[0], g[1] - L3          # wrist sits L3 above the grip centre
    dx, dy = wx - SH[0], wy - SH[1]
    d = (dx * dx + dy * dy - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    d = max(-1.0, min(1.0, d))
    q2 = sign * math.acos(d)
    q1 = math.atan2(dy, dx) - math.atan2(L2 * math.sin(q2), L1 + L2 * math.cos(q2))
    return q1, q2


def elbow(q1):
    return SH[0] + L1 * math.cos(q1), SH[1] + L1 * math.sin(q1)


def elbow_up_sign(g):
    a, b = ik(g, 1), ik(g, -1)
    return 1 if elbow(a[0])[1] < elbow(b[0])[1] else -1


def ease(s):
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, s)))


SL = elbow_up_sign(PICK_H)


def mirror(g):
    return 2 * SH[0] - g[0], g[1]


# The drop side is reached by yawing the base 180deg (like a real 6-axis arm),
# which in this side view is a horizontal scale 1 -> -1 about the shoulder.
# So every pose is solved on the pick side, with the drop targets mirrored.
DROP_M, DROP_HM = mirror(DROP), mirror(DROP_H)

# (t0, t1, kind, a, b, yaw_a, yaw_b)   yaw: +1 facing the feeder, -1 facing outbound
SEGMENTS = [
    (0.00, 0.06, "hold", HOME, HOME, 1, 1),
    (0.06, 0.22, "joint", HOME, PICK_H, 1, 1),
    (0.22, 0.31, "lin", PICK_H, PICK, 1, 1),
    (0.31, 0.37, "hold", PICK, PICK, 1, 1),
    (0.37, 0.46, "lin", PICK, PICK_H, 1, 1),
    (0.46, 0.65, "joint", PICK_H, DROP_HM, 1, -1),
    (0.65, 0.74, "lin", DROP_HM, DROP_M, -1, -1),
    (0.74, 0.80, "hold", DROP_M, DROP_M, -1, -1),
    (0.80, 0.88, "lin", DROP_M, DROP_HM, -1, -1),
    (0.88, 1.00, "joint", DROP_HM, HOME, -1, 1),
]


def pose(t):
    """Returns (q1, q2, yaw_scale)."""
    for t0, t1, kind, a, b, ya, yb in SEGMENTS:
        if t0 <= t <= t1:
            s = ease((t - t0) / (t1 - t0))
            if kind == "hold":
                return (*ik(a, SL), ya)
            if kind == "lin":
                g = (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)
                return (*ik(g, SL), ya)
            qa, qb = ik(a, SL), ik(b, SL)
            yaw = ya if ya == yb else math.cos(math.pi * s) * ya
            return qa[0] + (qb[0] - qa[0]) * s, qa[1] + (qb[1] - qa[1]) * s, yaw
    return (*ik(HOME, SL), 1)


def fk_grip(q1, q2):
    ex, ey = elbow(q1)
    wx, wy = ex + L2 * math.cos(q1 + q2), ey + L2 * math.sin(q1 + q2)
    return wx, wy + L3


def joint_tracks():
    ts = [i / N for i in range(N + 1)]
    q1s, q2s, q3s, yaws = [], [], [], []
    for t in ts:
        q1, q2, yaw = pose(t)
        yaws.append(yaw)
        q1s.append(math.degrees(q1))
        q2s.append(math.degrees(q2))
        q3s.append(90.0 - math.degrees(q1) - math.degrees(q2))
    # unwrap to avoid 360deg spins between samples
    for arr in (q1s, q2s, q3s):
        for i in range(1, len(arr)):
            while arr[i] - arr[i - 1] > 180:
                arr[i] -= 360
            while arr[i] - arr[i - 1] < -180:
                arr[i] += 360
    return ts, q1s, q2s, q3s, yaws


def rot_anim(vals, ts):
    v = ";".join(f"{a:.2f}" for a in vals)
    k = ";".join(f"{t:.4f}" for t in ts)
    return (f'<animateTransform attributeName="transform" type="rotate" dur="{DUR}s" '
            f'repeatCount="indefinite" values="{v}" keyTimes="{k}"/>')


def discrete(attr, pairs, dur=DUR):
    """pairs: [(keytime, value)], first keytime must be 0."""
    k = ";".join(f"{t:.4f}" for t, _ in pairs)
    v = ";".join(str(x) for _, x in pairs)
    return (f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{k}" values="{v}"/>')


def spline(attr, pairs, splines, dur=DUR, kind="animate", ttype=None):
    k = ";".join(f"{t:.4f}" for t, _ in pairs)
    v = ";".join(str(x) for _, x in pairs)
    ks = ";".join(splines)
    tt = f' type="{ttype}"' if ttype else ""
    tag = "animateTransform" if kind == "transform" else "animate"
    return (f'<{tag} attributeName="{attr}"{tt} dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="{k}" values="{v}" keySplines="{ks}"/>')


EASE_OUT = "0.15 0.6 0.3 1"
EASE_IO = "0.45 0 0.55 1"
LINEAR = "0 0 1 1"

# ---- gantry engraver that rasters the name in ----------------------------------
RAIL_Y = 50
RAIL_X0, RAIL_X1 = 40, 590
PARK_X = 566
SPEED = 2400.0   # px/s along a raster pass
STEP = 0.045     # s to drop to the next raster line
COOL = 0.45      # s the freshly engraved strip stays orange


def engraver(s, jobs, t_start=0.5):
    """jobs: list of (svg_text_orange, svg_text_final, x0, x1, y_top, y_bot, strips).
    Adds clip-paths + text + the moving gantry head to s. Returns end time."""
    org = C["orange"]
    keys = [(0.0, PARK_X, RAIL_Y + 14)]
    t = t_start
    ltr = True
    passes = []
    for j, (hot, cold, x0, x1, yt, yb, n) in enumerate(jobs):
        h = (yb - yt) / n
        rects_hot, rects_cold = [], []
        for k in range(n):
            yc = yt + h * (k + 0.5)
            xa, xb = (x0, x1) if ltr else (x1, x0)
            # travel to the start of this pass
            if keys[-1][1:] != (xa, yc):
                move = 0.5 if len(keys) == 1 else (STEP if k else 0.16)
                t += move
                keys.append((t, xa, yc))
            d = (x1 - x0) / SPEED
            for rects, delay in ((rects_hot, 0.0), (rects_cold, COOL)):
                b = t + delay
                if ltr:
                    anim = (f'<animate attributeName="width" begin="{b:.3f}s" dur="{d:.3f}s" from="0" to="{x1-x0:.1f}" fill="freeze"/>')
                    rects.append(f'<rect x="{x0:.1f}" y="{yt + h*k:.2f}" width="0" height="{h+0.4:.2f}">{anim}</rect>')
                else:
                    anim = (f'<animate attributeName="width" begin="{b:.3f}s" dur="{d:.3f}s" from="0" to="{x1-x0:.1f}" fill="freeze"/>'
                            f'<animate attributeName="x" begin="{b:.3f}s" dur="{d:.3f}s" from="{x1:.1f}" to="{x0:.1f}" fill="freeze"/>')
                    rects.append(f'<rect x="{x1:.1f}" y="{yt + h*k:.2f}" width="0" height="{h+0.4:.2f}">{anim}</rect>')
            passes.append((t, t + d))
            t += d
            keys.append((t, xb, yc))
            ltr = not ltr
        s.defs.append(f'<clipPath id="eh{j}">{"".join(rects_hot)}</clipPath>')
        s.defs.append(f'<clipPath id="ec{j}">{"".join(rects_cold)}</clipPath>')
        s.add(f'<g clip-path="url(#eh{j})">{hot}</g><g clip-path="url(#ec{j})">{cold}</g>')
    t += 0.45
    keys.append((t, PARK_X, RAIL_Y + 14))
    total = t

    kt = ";".join(f"{k[0]/total:.5f}" for k in keys)
    xs = ";".join(f"{k[1]:.1f} 0" for k in keys)
    ys = ";".join(f"{k[2]-RAIL_Y:.1f}" for k in keys)
    tool_y = ";".join(f"0 {k[2]-RAIL_Y:.1f}" for k in keys)
    # laser on only while a pass is running
    lk = [(0.0, 0)]
    for a, b in passes:
        lk += [(a / total, 1), (b / total, 0)]
    lkt = ";".join(f"{a:.5f}" for a, _ in lk)
    lv = ";".join(str(v) for _, v in lk)

    st, st2, bg = C["steel"], C["steel2"], C["bg"]
    s.add(
        # rail
        f'<rect x="{RAIL_X0}" y="{RAIL_Y-4}" width="{RAIL_X1-RAIL_X0}" height="8" rx="2" fill="{C["panel"]}" stroke="{st2}" stroke-width="1.5"/>'
        f'<rect x="{RAIL_X0-6}" y="{RAIL_Y-9}" width="8" height="18" rx="2" fill="{st2}"/>'
        f'<rect x="{RAIL_X1-2}" y="{RAIL_Y-9}" width="8" height="18" rx="2" fill="{st2}"/>'
        # carriage + z-axis + tool
        f'<g><animateTransform attributeName="transform" type="translate" dur="{total:.3f}s" fill="freeze" '
        f'keyTimes="{kt}" values="{xs}"/>'
        f'<line x1="0" y1="{RAIL_Y}" x2="0" y2="{RAIL_Y+14}" stroke="{st2}" stroke-width="3">'
        f'<animate attributeName="y2" dur="{total:.3f}s" fill="freeze" keyTimes="{kt}" '
        f'values="{";".join(f"{k[2]-10:.1f}" for k in keys)}"/></line>'
        f'<rect x="-17" y="{RAIL_Y-8}" width="34" height="16" rx="3" fill="{st}" stroke="{bg}" stroke-width="2"/>'
        f'<circle cx="9" cy="{RAIL_Y}" r="2.4" fill="{C["orange"]}">'
        f'<animate attributeName="opacity" values="1;0.25;1" dur="1.4s" repeatCount="indefinite"/></circle>'
        f'<g transform="translate(0 {RAIL_Y})"><g><animateTransform attributeName="transform" type="translate" '
        f'dur="{total:.3f}s" fill="freeze" keyTimes="{kt}" values="{tool_y}"/>'
        f'<rect x="-7" y="-24" width="14" height="16" rx="2" fill="{st}" stroke="{bg}" stroke-width="2"/>'
        f'<path d="M-4 -8H4L2 -3H-2Z" fill="{st2}"/>'
        f'<g opacity="0"><animate attributeName="opacity" dur="{total:.3f}s" fill="freeze" calcMode="discrete" keyTimes="{lkt}" values="{lv}"/>'
        f'<path d="M0 -3V0" stroke="{org}" stroke-width="2"/><circle r="3.2" fill="{org}"/>'
        f'<circle r="7" fill="none" stroke="{org}" stroke-width="1" opacity="0.6"/></g>'
        f'</g></g></g>'
    )
    return total


def build():
    s = SVG(W, H, "Praneeth Maheshwaran",
            "A gantry laser engraver rasters the name Praneeth Maheshwaran onto the banner, then "
            "'ML, robotics, computer vision' and 'B.Tech CSE, SASTRA University, 2028, Tamil Nadu'. "
            "On the right, a 3-DOF robot arm picks orange blocks off a conveyor after a camera "
            "boxes each one, yaws around and places them on an outbound belt.")
    ink, dim, mute, line = C["ink"], C["dim"], C["mute"], C["line"]
    org, amb = C["orange"], C["amber"]

    s.defs.append(f'<clipPath id="frame"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14"/></clipPath>')
    s.add(f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{C["bg"]}" stroke="{line}" stroke-width="1.5"/>')
    s.add('<g clip-path="url(#frame)">')

    # dot grid over the work cell
    dots = []
    for gx in range(600, 1200, 24):
        for gy in range(84, 336, 24):
            dots.append(f"M{gx} {gy}h1.6")
    s.add(f'<path d="{"".join(dots)}" stroke="{C["grid"]}" stroke-width="1.6" stroke-linecap="round"/>')

    # ---- left: identity, engraved in by the gantry --------------------------------
    x0 = 52
    name_size = 76
    l1, l2 = "PRANEETH", "MAHESHWARAN"
    w1 = measure("disp", l1, name_size, 0.5)
    w2 = measure("disp", l2, name_size, 0.5)
    role = "ML  ·  robotics  ·  computer vision"
    meta = "B.Tech CSE  ·  SASTRA University  ·  2028  ·  Tamil Nadu"
    wr = measure("sans", role, 23)
    wm = measure("mono", meta, 14.5)
    pad = 6
    jobs = [
        (s.text(x0, 170, l1, "disp", name_size, org, spacing=0.5), s.text(x0, 170, l1, "disp", name_size, ink, spacing=0.5),
         x0 - pad, x0 + w1 + pad, 110, 174, 5),
        (s.text(x0, 248, l2, "disp", name_size, org, spacing=0.5), s.text(x0, 248, l2, "disp", name_size, ink, spacing=0.5),
         x0 - pad, x0 + w2 + pad, 188, 252, 5),
        (s.text(x0 + 2, 298, role, "sans", 23, org), s.text(x0 + 2, 298, role, "sans", 23, C["steel"]),
         x0 - pad, x0 + wr + pad, 276, 305, 2),
        (s.text(x0 + 2, 338, meta, "mono", 14.5, org), s.text(x0 + 2, 338, meta, "mono", 14.5, dim),
         x0 - pad, x0 + wm + pad, 323, 343, 1),
    ]
    engraver(s, jobs)

    # ---- right: work cell -----------------------------------------------------
    floor = 348
    ticks = "".join(f"M{x} {floor}v{6 if x % 100 == 0 else 3}" for x in range(580, 1200, 20))
    s.add(f'<path d="M572 {floor}H{W}" stroke="{line}" stroke-width="1.5"/>'
          f'<path d="{ticks}" stroke="{line}" stroke-width="1"/>')

    # camera post + bracket + FOV
    s.add(f'<path d="M662 {floor}V118H712" fill="none" stroke="{C["steel2"]}" stroke-width="4"/>')
    s.add(f'<rect x="700" y="108" width="40" height="22" rx="3" fill="{C["panel"]}" stroke="{C["steel2"]}" stroke-width="2"/>'
          f'<rect x="724" y="130" width="12" height="7" fill="{C["steel2"]}"/>'
          f'<circle cx="708" cy="115" r="2.2" fill="{org}">' + discrete("opacity", [(0, 1), (0.5, 0.2)], dur=0.9) + "</circle>")
    s.add(f'<path d="M730 137L742 300M730 137L792 300" stroke="{mute}" stroke-width="1" stroke-dasharray="3 5"/>')

    # input belt
    def belt(x1, x2, travel, t_move0, t_move1, spline_kind):
        period = travel / round(travel / 21)
        half = period / 2
        g = [f'<rect x="{x1}" y="{BELT_TOP}" width="{x2-x1}" height="10" rx="5" fill="{C["panel"]}" stroke="{C["steel2"]}" stroke-width="1.5"/>']
        for rx in (x1 + 5, x2 - 5):
            g.append(f'<circle cx="{rx}" cy="{BELT_TOP+5}" r="2" fill="{C["steel2"]}"/>')
        anim = spline("stroke-dashoffset",
                      [(0, 0), (t_move0, 0), (t_move1, round(-travel, 2)), (1, round(-travel, 2))],
                      [LINEAR, spline_kind, LINEAR])
        g.append(f'<path d="M{x1+10} {BELT_TOP+5}H{x2-10}" stroke="{mute}" stroke-width="2" '
                 f'stroke-dasharray="{half:.3f} {half:.3f}">{anim}</path>')
        return "".join(g)

    T_IN0, T_IN1 = 0.0, 0.17
    T_OUT0, T_OUT1 = 0.82, 0.99
    s.add(belt(596, 800, PICK_X - FEED_X, T_IN0 + 1e-4, T_IN1, EASE_OUT))
    s.add(belt(988, 1210, EXIT_X - DROP_X, T_OUT0, T_OUT1, EASE_IO))

    def block_rect(cx, cy, extra=""):
        b = BLOCK
        return (f'<g {extra}><rect x="{cx-b/2}" y="{cy-b/2}" width="{b}" height="{b}" rx="3" fill="{org}"/>'
                f'<rect x="{cx-b/2+7}" y="{cy-b/2+7}" width="{b-14}" height="{b-14}" rx="1.5" fill="{C["orange_dk"]}"/></g>')

    # block on the input belt: slides out of the feeder, waits, gets picked
    T_GRAB, T_RELEASE = 0.335, 0.765
    slide = spline("transform",
                   [(0, "0 0"), (T_IN0 + 1e-4, "0 0"), (T_IN1, f"{PICK_X-FEED_X:.1f} 0"), (1, f"{PICK_X-FEED_X:.1f} 0")],
                   [LINEAR, EASE_OUT, LINEAR], kind="transform", ttype="translate")
    s.add(f'<g>{discrete("opacity", [(0, 1), (T_GRAB, 0)])}'
          f'<g>{slide}{block_rect(FEED_X, GRIP_Y)}</g></g>')

    # block placed on the outbound belt, then carried off-frame
    out = spline("transform",
                 [(0, "0 0"), (T_OUT0, "0 0"), (T_OUT1, f"{EXIT_X-DROP_X:.1f} 0"), (1, f"{EXIT_X-DROP_X:.1f} 0")],
                 [LINEAR, EASE_IO, LINEAR], kind="transform", ttype="translate")
    s.add(f'<g opacity="0">{discrete("opacity", [(0, 0), (T_RELEASE, 1), (0.995, 0)])}'
          f'<g>{out}{block_rect(DROP_X, GRIP_Y)}</g></g>')

    # feeder housing (drawn over the block so it appears to slide out)
    s.add(f'<rect x="590" y="292" width="52" height="50" rx="4" fill="{C["panel"]}" stroke="{C["steel2"]}" stroke-width="2"/>'
          f'<path d="M596 300h40" stroke="{org}" stroke-width="4"/>'
          f'<path d="M602 312h28M602 320h28M602 328h28" stroke="{C["line"]}" stroke-width="2"/>')

    # vision: bounding box on the waiting block
    bx0, by0, bx1, by1 = PICK_X - 20, GRIP_Y - 20, PICK_X + 20, GRIP_Y + 18
    k = 7
    corners = (f"M{bx0} {by0+k}V{by0}H{bx0+k}M{bx1-k} {by0}H{bx1}V{by0+k}"
               f"M{bx1} {by1-k}V{by1}H{bx1-k}M{bx0+k} {by1}H{bx0}V{by1-k}")
    s.add(f'<g opacity="0">{discrete("opacity", [(0, 0), (0.18, 1), (0.195, 0), (0.205, 1), (0.255, 0)])}'
          f'<path d="{corners}" fill="none" stroke="{amb}" stroke-width="2"/></g>')

    # pedestal with hazard stripes
    s.defs.append('<clipPath id="ped"><rect x="877" y="300" width="56" height="42"/></clipPath>')
    stripes = "".join(f'<path d="M{x} 342L{x+20} 300h9L{x+9} 342z" fill="{org}"/>' for x in range(860, 940, 18))
    s.add(f'<rect x="877" y="300" width="56" height="42" fill="{C["panel"]}"/>'
          f'<g clip-path="url(#ped)">{stripes}</g>'
          f'<rect x="877" y="300" width="56" height="42" fill="none" stroke="{C["steel2"]}" stroke-width="2"/>'
          f'<rect x="860" y="340" width="90" height="8" rx="2" fill="{C["steel2"]}"/>'
          f'<rect x="886" y="282" width="38" height="20" rx="3" fill="{C["steel2"]}"/>')
    s.add(f'<circle cx="918" cy="292" r="3" fill="{C["mute"]}">'
          f'<animate attributeName="fill" dur="{DUR}s" repeatCount="indefinite" calcMode="discrete" '
          f'keyTimes="0;{T_GRAB};{T_RELEASE}" values="{C["mute"]};{org};{C["mute"]}"/></circle>')

    # ---- the arm ----------------------------------------------------------------
    ts, q1s, q2s, q3s, yaws = joint_tracks()
    yaw_anim = (f'<animateTransform attributeName="transform" type="scale" dur="{DUR}s" '
                f'repeatCount="indefinite" keyTimes="{";".join(f"{t:.4f}" for t in ts)}" '
                f'values="{";".join(f"{y:.3f} 1" for y in yaws)}"/>')
    steel, steel2, dark = C["steel"], C["steel2"], C["bg"]

    def link(length, width):
        return (f'<rect x="-{width/2}" y="-{width/2}" width="{length+width}" height="{width}" '
                f'rx="{width/2}" fill="{steel}" stroke="{dark}" stroke-width="2"/>')

    def hub(r):
        return (f'<circle r="{r}" fill="{dark}" stroke="{steel}" stroke-width="3"/>'
                f'<circle r="{r*0.32:.1f}" fill="{org}"/>')

    # fingers: offset from the grip axis, open 19 -> closed 15.5
    fo, fc = 19.0, 15.5
    t_c0, t_c1, t_o0, t_o1 = 0.312, 0.335, 0.745, 0.768
    def finger(sign):
        vals = [(0, f"0 {sign*fo}"), (t_c0, f"0 {sign*fo}"), (t_c1, f"0 {sign*fc}"),
                (t_o0, f"0 {sign*fc}"), (t_o1, f"0 {sign*fo}"), (1, f"0 {sign*fo}")]
        anim = spline("transform", vals, [LINEAR, EASE_IO, LINEAR, EASE_IO, LINEAR],
                      kind="transform", ttype="translate")
        return (f'<g>{anim}<rect x="{L3-18}" y="-2.5" width="32" height="5" rx="1.5" fill="{steel2}" '
                f'stroke="{dark}" stroke-width="1.2"/></g>')

    carried = (f'<g opacity="0">{discrete("opacity", [(0, 0), (T_GRAB, 1), (T_RELEASE, 0)])}'
               + block_rect(L3, 0) + "</g>")

    arm = (
        f'<g transform="translate({SH[0]} {SH[1]})"><g>{yaw_anim}'
        f'<g>{rot_anim(q1s, ts)}'
        f'{link(L1, 22)}'
        f'<g transform="translate({L1} 0)"><g>{rot_anim(q2s, ts)}'
        f'{link(L2, 18)}'
        f'<g transform="translate({L2} 0)"><g>{rot_anim(q3s, ts)}'
        f'<rect x="-6" y="-6" width="{L3-16}" height="12" rx="3" fill="{steel}" stroke="{dark}" stroke-width="2"/>'
        f'{carried}'
        f'<rect x="{L3-22}" y="-24" width="8" height="48" rx="2" fill="{steel}" stroke="{dark}" stroke-width="2"/>'
        f'{finger(1)}{finger(-1)}'
        f'{hub(8)}'
        f'</g></g>'
        f'{hub(11)}'
        f'</g></g>'
        f'{hub(14)}'
        f'</g></g></g>'
    )
    s.add(arm)

    s.add("</g>")
    return s.render()


def reach_report():
    worst = []
    for i in range(N + 1):
        q1, q2, _ = pose(i / N)
        ex, ey = elbow(q1)
        gx, gy = fk_grip(q1, q2)
        worst.append((round(ey), round(gx), round(gy)))
    return SL, min(w[0] for w in worst), max(w[2] for w in worst), worst[::21]


if __name__ == "__main__":
    print(reach_report())
