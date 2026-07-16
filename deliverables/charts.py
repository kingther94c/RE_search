"""Self-contained inline-SVG charts for the landed DD report.

No JS, no external assets, no chart library — the repo's reports must render from a single
HTML file forever, including offline and from a Drive folder. Every function returns an SVG
string sized by viewBox so it scales in a responsive column.

Charts here exist to make a POINT that a table buries. Ordered by how much they earn:
  psf_vs_size    the land-size effect — the whole reason a street "average psf" is a lie
  trend          median land psf by year, with n on every bar (a landed street is thin)
  transect       what actually lies between the house and a scary zone label
  distance_bars  nearest parcel edge per zone, area-annotated
"""
from __future__ import annotations

import html

INK = "#16202b"
MUT = "#6b7a8c"
LINE = "#dbe3ec"
ACCENT = "#2f6f4f"
RED = "#c0392b"
AMBER = "#b7791f"
BLUE = "#4a6fa5"

ZONE_COLOUR = {
    "RESIDENTIAL": "#8fbf9f", "PARK": "#5aa469", "OPEN SPACE": "#7fc08f",
    "ROAD": "#cfd8e3", "WATERBODY": "#7fb2d9", "BUSINESS 1": "#e0a458",
    "BUSINESS 2": "#c0603a", "RESERVE SITE": "#9b8ec4", "UTILITY": "#a8a8a8",
    "EDUCATIONAL INSTITUTION": "#d9b44a", "PLACE OF WORSHIP": "#c9a0c0",
    "TRANSPORT FACILITIES": "#b0a89a", "COMMERCIAL": "#d98cA0",
}


def _e(x) -> str:
    return html.escape(str(x))


def _zc(zone) -> str:
    return ZONE_COLOUR.get((zone or "").upper(), "#c4cdd8")


def psf_vs_size(comps: list[dict], subject_sqft: float | None = None,
                w: int = 660, h: int = 300) -> str:
    """Land psf against plot size — one dot per caveat. The downward slope IS the finding:
    small plots clear at a higher land psf, so a street average describes no real house."""
    pts = [(c["area_sqft"], c["psf"], c.get("contract_ym", "")) for c in comps
           if c.get("area_sqft") and c.get("psf")]
    if not pts:
        return ""
    pad_l, pad_r, pad_t, pad_b = 58, 14, 16, 38
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs) * 0.95, max(xs) * 1.03
    y0, y1 = min(ys) * 0.95, max(ys) * 1.03

    def X(v): return pad_l + (v - x0) / (x1 - x0) * (w - pad_l - pad_r)
    def Y(v): return h - pad_b - (v - y0) / (y1 - y0) * (h - pad_t - pad_b)

    # recency shading: older prints fade, so the eye reads the current level
    yms = sorted({p[2] for p in pts})
    rank = {ym: i for i, ym in enumerate(yms)}
    n = max(1, len(yms) - 1)

    g = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Land psf against plot size">']
    for i in range(5):  # gridlines
        v = y0 + (y1 - y0) * i / 4
        y = Y(v)
        g.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" '
                 f'stroke="{LINE}" stroke-width="1"/>')
        g.append(f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" font-size="10" '
                 f'fill="{MUT}">${v:,.0f}</text>')
    for i in range(5):
        v = x0 + (x1 - x0) * i / 4
        x = X(v)
        g.append(f'<text x="{x:.1f}" y="{h-pad_b+16}" text-anchor="middle" font-size="10" '
                 f'fill="{MUT}">{v:,.0f}</text>')
    if subject_sqft:
        x = X(subject_sqft)
        g.append(f'<line x1="{x:.1f}" y1="{pad_t}" x2="{x:.1f}" y2="{h-pad_b}" '
                 f'stroke="{RED}" stroke-width="1.5" stroke-dasharray="4 3"/>')
        g.append(f'<text x="{x+5:.1f}" y="{pad_t+11}" font-size="10" fill="{RED}" '
                 f'font-weight="700">subject {subject_sqft:,.0f} sqft</text>')
    for a, p, ym in pts:
        o = 0.25 + 0.75 * (rank.get(ym, 0) / n)
        g.append(f'<circle cx="{X(a):.1f}" cy="{Y(p):.1f}" r="4" fill="{BLUE}" '
                 f'fill-opacity="{o:.2f}" stroke="#fff" stroke-width="0.7"/>')
    g.append(f'<text x="{pad_l}" y="{h-6}" font-size="10.5" fill="{MUT}">'
             f'plot size (sqft) &#8594; · dot opacity = recency · n={len(pts)}</text>')
    g.append(f'<text transform="translate(13,{h/2}) rotate(-90)" text-anchor="middle" '
             f'font-size="10.5" fill="{MUT}">land psf</text>')
    g.append("</svg>")
    return "".join(g)


def trend(rows: list[dict], w: int = 660, h: int = 230) -> str:
    """Median land psf by year. n is printed on every bar because a landed street is thin and
    a 'trend' off n=1 is noise."""
    if not rows:
        return ""
    pad_l, pad_r, pad_t, pad_b = 58, 14, 22, 40
    ys = [r["psf_med"] for r in rows]
    y0, y1 = 0, max(ys) * 1.15
    bw = (w - pad_l - pad_r) / len(rows)

    def Y(v): return h - pad_b - (v - y0) / (y1 - y0) * (h - pad_t - pad_b)

    g = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Median land psf by year">']
    for i in range(4):
        v = y0 + (y1 - y0) * i / 3
        y = Y(v)
        g.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" '
                 f'stroke="{LINE}"/>')
        g.append(f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" font-size="10" '
                 f'fill="{MUT}">${v:,.0f}</text>')
    for i, r in enumerate(rows):
        x = pad_l + i * bw + bw * 0.18
        bwid = bw * 0.64
        y = Y(r["psf_med"])
        thin = r["n"] < 4
        g.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bwid:.1f}" '
                 f'height="{h-pad_b-y:.1f}" fill="{AMBER if thin else ACCENT}" '
                 f'fill-opacity="{0.55 if thin else 0.85}" rx="2"/>')
        g.append(f'<text x="{x+bwid/2:.1f}" y="{y-5:.1f}" text-anchor="middle" font-size="10.5" '
                 f'font-weight="700" fill="{INK}">{r["psf_med"]:,}</text>')
        g.append(f'<text x="{x+bwid/2:.1f}" y="{h-pad_b+14}" text-anchor="middle" '
                 f'font-size="10.5" fill="{MUT}">{_e(r["period"])}</text>')
        g.append(f'<text x="{x+bwid/2:.1f}" y="{h-pad_b+26}" text-anchor="middle" '
                 f'font-size="9" fill="{AMBER if thin else MUT}">n={r["n"]}</text>')
    g.append(f'<text x="{pad_l}" y="13" font-size="10.5" fill="{MUT}">'
             f'median land psf · amber = n&lt;4, too thin to read as a move</text>')
    g.append("</svg>")
    return "".join(g)


def transect(t: dict, w: int = 660, h: int = 86) -> str:
    """A horizontal band of what you cross walking toward a zone. Turns 'BUSINESS 2 at 151m'
    into 'park for 100m, then a road, then Business 2'."""
    steps = t.get("steps") or []
    if not steps:
        return ""
    end = max(s["m"] for s in steps) or 1
    segs = []
    for i, s in enumerate(steps):
        a = s["m"]
        b = steps[i + 1]["m"] if i + 1 < len(steps) else end + 20
        segs.append((a, b, s["zone"]))
    span = segs[-1][1] or 1
    pad_l, pad_r, top = 4, 4, 26
    bh = 26
    g = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Zoning transect toward {_e(t.get("toward"))}">']
    hit = t.get("reaches_target", True)
    label = (f'toward {t.get("toward")} · bearing {t.get("bearing_deg")}&#176; · '
             f'nearest edge {t.get("edge_m")}m')
    g.append(f'<text x="{pad_l}" y="13" font-size="11" font-weight="700" fill="{INK}">{label}</text>')
    if not hit:
        g.append(f'<text x="{w-pad_r}" y="13" text-anchor="end" font-size="10" fill="{RED}" '
                 f'font-weight="700">ray misses the parcel</text>')
    for a, b, z in segs:
        x = pad_l + a / span * (w - pad_l - pad_r)
        ww = max(1.0, (b - a) / span * (w - pad_l - pad_r))
        g.append(f'<rect x="{x:.1f}" y="{top}" width="{ww:.1f}" height="{bh}" '
                 f'fill="{_zc(z)}" stroke="#fff" stroke-width="1"/>')
        if ww > 52:
            g.append(f'<text x="{x+ww/2:.1f}" y="{top+17}" text-anchor="middle" font-size="9.5" '
                     f'fill="#14202c" font-weight="600">{_e((z or "gap")[:14])}</text>')
        g.append(f'<text x="{x:.1f}" y="{top+bh+13}" font-size="9" fill="{MUT}">{a}m</text>')
    g.append("</svg>")
    return "".join(g)


def distance_bars(rows: list[dict], cap_m: int = 420, w: int = 660) -> str:
    """Nearest parcel edge per zone, annotated with the parcel's AREA — because area is what
    stops a 14 sqm cable box being written up as a substation."""
    rows = [r for r in rows if r["metres"] <= cap_m]
    if not rows:
        return ""
    rh, top = 21, 16
    h = top + len(rows) * rh + 12
    pad_l, pad_r = 168, 12
    mx = max(r["metres"] for r in rows) or 1
    g = [f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" '
         f'role="img" aria-label="Nearest parcel edge per zone">']
    for i, r in enumerate(rows):
        y = top + i * rh
        g.append(f'<text x="{pad_l-8}" y="{y+11}" text-anchor="end" font-size="10.5" '
                 f'fill="{INK}">{_e(r["zone"][:26])}</text>')
        bw = max(2.0, r["metres"] / mx * (w - pad_l - pad_r - 96))
        g.append(f'<rect x="{pad_l}" y="{y+2}" width="{bw:.1f}" height="12" '
                 f'fill="{_zc(r["zone"])}" rx="2"/>')
        a = r.get("area_sqm")
        a = f'{float(a):,.0f} sqm' if a else ''
        g.append(f'<text x="{pad_l+bw+6:.1f}" y="{y+12}" font-size="10" fill="{MUT}">'
                 f'{r["metres"]}m · {a}</text>')
    g.append("</svg>")
    return "".join(g)
