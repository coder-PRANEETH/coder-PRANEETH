#!/usr/bin/env python3
"""Contribution calendar as a warehouse floor.

Every day with contributions is a tote on the floor. A warehouse robot (AGV)
leaves its dock, sweeps the weeks in a serpentine, picks each tote (the cell
flashes and empties, the load on its back grows), drives back down the aisle,
unloads, and the floor restocks. Pure SVG + SMIL, no text, no fonts.

Usage (in GitHub Actions):
    GITHUB_TOKEN=... USERNAME=coder-PRANEETH python3 scripts/contrib_agv.py generated/agv.svg
Offline test:
    python3 scripts/contrib_agv.py out.svg --demo
Only the standard library is used.
"""
import json
import os
import random
import sys
import urllib.request

BG, LINE, GRID = "#131416", "#2A2D33", "#1E2024"
MUTE, STEEL, STEEL2 = "#5A5E66", "#D6D1C8", "#A9A49B"
ORG, ORG_DK, AMBER = "#FF6B1A", "#B8480C", "#FFC247"
LEVEL_COLORS = ["#24262B", "#5C2A0E", "#9A4312", "#D65A16", "#FF7A2E"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

W = 1200
PITCH, CELL = 20, 15
X0, Y0 = 100, 26
AISLE_Y = Y0 + 7 * PITCH + 18
H = AISLE_Y + 30
DOCK = (54.0, float(AISLE_Y))

SWEEP_SPEED = 250.0   # px/s while picking
RETURN_SPEED = 750.0  # px/s back down the aisle
IDLE = 0.9            # s parked before leaving
UNLOAD = 1.6          # s parked after returning
TURN = 0.12           # s to rotate in place-ish at a corner


def fetch(login, token):
    query = ("query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{"
             "weeks{contributionDays{weekday contributionLevel}}}}}}")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"l": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "contrib-agv"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(d["weekday"], LEVELS.get(d["contributionLevel"], 0)) for d in w["contributionDays"]]
            for w in weeks]


def demo():
    rnd = random.Random(7)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            if w == 52 and d > 3:
                break
            p = 0.25 + 0.45 * (w / 52)
            days.append((d, rnd.choice([1, 1, 2, 2, 3, 4]) if rnd.random() < p else 0))
        weeks.append(days)
    return weeks


def cell_xy(w, d):
    return X0 + w * PITCH + CELL / 2, Y0 + d * PITCH + CELL / 2


def plan(weeks):
    """Serpentine pick order, Manhattan waypoints and timings."""
    targets = []
    down = False
    for w, days in enumerate(weeks):
        active = sorted((d for d, lvl in days if lvl > 0), reverse=not down)
        if not active:
            continue
        targets += [(w, d) for d in active]
        down = not down

    pts = [(0.0, DOCK)]          # (time, (x, y))
    picks = {}
    t = IDLE
    pts.append((t, DOCK))
    cur = DOCK

    def go(to, speed):
        nonlocal t, cur
        dist = abs(to[0] - cur[0]) + abs(to[1] - cur[1])
        if dist < 1e-6:
            return
        t += dist / speed
        pts.append((t, to))
        cur = to

    for w, d in targets:
        x, y = cell_xy(w, d)
        if abs(cur[0] - x) > 1e-6:
            go((x, cur[1]), SWEEP_SPEED)
        go((x, y), SWEEP_SPEED)
        picks[(w, d)] = t
    if targets:
        go((cur[0], float(AISLE_Y)), SWEEP_SPEED)
        go(DOCK, RETURN_SPEED)
    t_dock = t
    t += UNLOAD
    pts.append((t, DOCK))
    return pts, picks, targets, t_dock, t


def heading(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    if abs(dx) >= abs(dy):
        return 0.0 if dx >= 0 else 180.0
    return 90.0 if dy > 0 else -90.0


def render(weeks):
    pts, picks, targets, t_dock, T = plan(weeks)
    kt = lambda x: f"{min(max(x / T, 0.0), 1.0):.5f}"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Contribution calendar drawn as a warehouse floor; a robot picks every day with contributions and returns to its dock.">',
           f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{LINE}" stroke-width="1.5"/>']

    # aisle + dock
    gx1 = X0 + len(weeks) * PITCH
    out.append(f'<path d="M{DOCK[0]+26} {AISLE_Y}H{gx1}" stroke="{LINE}" stroke-width="2" stroke-dasharray="8 7"/>')
    out.append('<clipPath id="dock"><rect x="26" y="' + str(AISLE_Y - 26) + '" width="56" height="52" rx="4"/></clipPath>')
    stripes = "".join(f'<path d="M{x} {AISLE_Y+26}L{x+26} {AISLE_Y-26}h8L{x+8} {AISLE_Y+26}z" fill="{ORG}"/>'
                      for x in range(0, 100, 16))
    out.append(f'<g clip-path="url(#dock)"><rect x="26" y="{AISLE_Y-26}" width="56" height="52" fill="{BG}"/>{stripes}'
               f'<rect x="34" y="{AISLE_Y-18}" width="40" height="36" rx="3" fill="{BG}"/></g>'
               f'<rect x="26" y="{AISLE_Y-26}" width="56" height="52" rx="4" fill="none" stroke="{STEEL2}" stroke-width="1.5"/>')

    # floor cells
    restock0 = t_dock + 0.25
    span = max(UNLOAD - 0.6, 0.4)
    nweeks = max(len(weeks), 1)
    for w, days in enumerate(weeks):
        for d, lvl in days:
            x, y = X0 + w * PITCH, Y0 + d * PITCH
            base = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{LEVEL_COLORS[lvl]}"'
            if (w, d) in picks:
                tp = picks[(w, d)]
                tr = restock0 + span * w / nweeks
                vals = [LEVEL_COLORS[lvl], AMBER, LEVEL_COLORS[0], LEVEL_COLORS[lvl]]
                keys = [0.0, tp, tp + 0.14, tr]
                out.append(base + f'><animate attributeName="fill" dur="{T:.3f}s" repeatCount="indefinite" '
                                  f'calcMode="discrete" keyTimes="{";".join(kt(k) for k in keys)}" '
                                  f'values="{";".join(vals)}"/></rect>')
            else:
                out.append(base + "/>")

    # robot path
    times = [p[0] for p in pts]
    xy = [p[1] for p in pts]
    tr_vals = ";".join(f"{x:.1f} {y:.1f}" for x, y in xy)
    tr_keys = ";".join(kt(t) for t in times)

    # heading: rotate at each corner over TURN seconds
    rk, rv = [0.0], [0.0]
    hd = 0.0
    for i in range(1, len(xy)):
        if xy[i] == xy[i - 1]:
            continue
        nh = heading(xy[i - 1], xy[i])
        while nh - hd > 180:
            nh -= 360
        while nh - hd < -180:
            nh += 360
        if nh != hd:
            t0 = times[i - 1]
            t1 = min(t0 + TURN, times[i])
            rk += [t0, t1]
            rv += [hd, nh]
            hd = nh
    # face forward again while unloading so the loop restarts cleanly
    tgt = round(hd / 360.0) * 360.0
    if tgt != hd:
        t0 = t_dock + 0.1
        rk += [t0, t0 + 0.45]
        rv += [hd, tgt]
    rk.append(T)
    rv.append(rv[-1])
    # keyTimes must be non-decreasing and values match
    rot_keys = ";".join(kt(k) for k in rk)
    rot_vals = ";".join(f"{v:.1f}" for v in rv)

    # load meter: grows with every pick, empties at the dock
    n = max(len(targets), 1)
    lk, lv = [0.0], [0.0]
    for i, (w, d) in enumerate(targets):
        lk.append(picks[(w, d)])
        lv.append((i + 1) / n)
    lk.append(t_dock + 0.2)
    lv.append(0.0)
    load_keys = ";".join(kt(k) for k in lk)
    size = 9.0
    load_w = ";".join(f"{size * v:.2f}" for v in lv)
    load_xy = ";".join(f"{-size * v / 2:.2f}" for v in lv)

    robot = (
        f'<g><animateTransform attributeName="transform" type="translate" dur="{T:.3f}s" repeatCount="indefinite" '
        f'keyTimes="{tr_keys}" values="{tr_vals}"/>'
        f'<g><animateTransform attributeName="transform" type="rotate" dur="{T:.3f}s" repeatCount="indefinite" '
        f'keyTimes="{rot_keys}" values="{rot_vals}"/>'
        # wheels
        f'<rect x="-9" y="-13" width="9" height="4" rx="1.5" fill="{STEEL2}"/><rect x="-9" y="9" width="9" height="4" rx="1.5" fill="{STEEL2}"/>'
        # body, bumper, lidar
        f'<rect x="-12" y="-11" width="24" height="22" rx="5" fill="{STEEL}" stroke="{BG}" stroke-width="2"/>'
        f'<rect x="9" y="-9" width="4" height="18" rx="1.5" fill="{ORG}"/>'
        f'<rect x="-8" y="-8" width="16" height="16" rx="2" fill="{BG}"/>'
        f'<rect x="-4.5" y="-4.5" width="0" height="0" rx="1" fill="{ORG}">'
        f'<animate attributeName="width" dur="{T:.3f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{load_keys}" values="{load_w}"/>'
        f'<animate attributeName="height" dur="{T:.3f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{load_keys}" values="{load_w}"/>'
        f'<animate attributeName="x" dur="{T:.3f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{load_keys}" values="{load_xy}"/>'
        f'<animate attributeName="y" dur="{T:.3f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{load_keys}" values="{load_xy}"/>'
        f'</rect>'
        f'<circle cx="5" cy="0" r="1.8" fill="{AMBER}"><animate attributeName="opacity" values="1;0.2;1" dur="0.7s" repeatCount="indefinite"/></circle>'
        f'</g></g>'
    )
    out.append(robot)
    out.append("</svg>")
    return "\n".join(out), T, len(targets)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    path = sys.argv[1]
    if "--demo" in sys.argv:
        weeks = demo()
    else:
        token = os.environ.get("GITHUB_TOKEN")
        login = os.environ.get("USERNAME") or os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not token or not login:
            raise SystemExit("set GITHUB_TOKEN and USERNAME")
        weeks = fetch(login, token)
    svg, T, n = render(weeks)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {path}: {n} active days, {T:.1f}s loop, {len(svg)/1024:.0f} KB")


if __name__ == "__main__":
    main()
