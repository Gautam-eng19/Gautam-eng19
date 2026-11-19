"""Animated cards for the README's Featured projects section. build.py calls render() for each card.

Layout: title, badge, description and stack on the left; a small looping animation of what the
project does on the right, with a one-line caption under it; a light travels round the border.
Everything is CSS animation, which GitHub plays inside README images.
"""
import math
import re
from html import escape

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
DEVANAGARI = "'Nirmala UI','Kohinoor Devanagari','Noto Sans Devanagari',Mangal,sans-serif"
W, H = 560, 232
VX, VY, VW, VH = 370, 24, 166, 134                # the animation area, right-hand side

THEME = {
    "dark": dict(bg="#0d1117", panel="#161b22", border="#30363d", ink="#e6edf3", muted="#8b949e", faint="#21262d"),
    "light": dict(bg="#ffffff", panel="#f6f8fa", border="#d0d7de", ink="#1f2328", muted="#656d76", faint="#e4e8ec"),
}
ACCENTS = {                                          # (dark theme, light theme)
    "green": ("#3fb950", "#1a7f37"), "cyan": ("#39c5cf", "#1b7c83"), "copper": ("#f0883e", "#bc4c00"),
    "gold": ("#e3b341", "#9a6700"), "magenta": ("#db61a2", "#bf3989"), "amber": ("#ffa116", "#b35900"),
    "blue": ("#58a6ff", "#0969da"), "violet": ("#a371f7", "#8250df"), "coral": ("#f78166", "#c4432b"),
    "red": ("#f85149", "#cf222e"), "yellow": ("#d29922", "#9a6700"), "steel": ("#6e7681", "#8c959f"),
    "purple": ("#d2a8ff", "#8250df"),
}


class Ctx:
    def __init__(self, mode):
        self.mode, self.t = mode, THEME[mode]

    def acc(self, name):
        return ACCENTS[name][0 if self.mode == "dark" else 1]


def txt(x, y, s, fill, size=12, weight=400, anchor="start", extra="", family=MONO):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" font-family="{family}"{extra}>{escape(str(s))}</text>')


def kf(name, cycle, stops):
    """Keyframes from (seconds, declarations) pairs, so timelines can be written in seconds."""
    return f"@keyframes {name}{{" + "".join(f"{min(100.0, 100 * t / cycle):.2f}%{{{d}}}" for t, d in stops) + "}"


def anim(name, cycle, easing="linear"):
    return f"animation:{name} {cycle}s {easing} infinite"


def show(name, cycle, t_on, t_off, extra_from="", extra_to=""):
    """Hidden, then shown from t_on until t_off, every cycle."""
    return kf(name, cycle, [(0, f"opacity:0;{extra_from}"), (t_on, f"opacity:0;{extra_from}"),
                            (t_on + 0.18, f"opacity:1;{extra_to}"), (t_off, f"opacity:1;{extra_to}"),
                            (t_off + 0.25, f"opacity:0;{extra_to}"), (cycle, f"opacity:0;{extra_from}")])


def check(x, y, colour, size=1.0):
    return (f'<path d="M{x:.1f} {y:.1f}l{3.2 * size:.1f} {3.2 * size:.1f} {6 * size:.1f} -{7 * size:.1f}" fill="none" '
            f'stroke="{colour}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')


def cross(x, y, colour, s=3.2):
    return (f'<path d="M{x - s:.1f} {y - s:.1f}l{2 * s:.1f} {2 * s:.1f}M{x + s:.1f} {y - s:.1f}l-{2 * s:.1f} {2 * s:.1f}" '
            f'stroke="{colour}" stroke-width="2" stroke-linecap="round"/>')


# ---------------------------------------------------------------- the eight animations

def vis_waveform(c):
    """VAANI: speech bars against a pitch trace, a pause flagged, a playhead sweeping across."""
    css, b = [], []
    cyan, copper, purple, ink, cycle = c.acc("cyan"), c.acc("copper"), c.acc("purple"), c.t["ink"], 5.0
    x0, x1, n, cy = VX + 10, VX + VW - 6, 22, VY + 44
    step = (x1 - x0) / (n - 1)
    pause = (12, 15)
    rx, rw = x0 + (pause[0] - 0.6) * step, (pause[1] - pause[0] + 1.2) * step
    css.append(".fl{animation:fl 2.4s ease-in-out infinite}@keyframes fl{50%{opacity:.45}}")
    b.append(f'<rect class="fl" x="{rx:.1f}" y="{VY + 14}" width="{rw:.1f}" height="64" rx="4" fill="{copper}" '
             f'fill-opacity=".1" stroke="{copper}" stroke-dasharray="3 3"/>')
    b.append(txt(rx + rw / 2, VY + 8, "pause", copper, 10, 700, "middle"))
    css.append(".wb{transform-box:fill-box;transform-origin:center;animation:wb 1.3s ease-in-out infinite}"
               "@keyframes wb{0%,100%{transform:scaleY(1)}50%{transform:scaleY(.6)}}")
    for i in range(n):
        a = 0.25 + 0.75 * abs(math.sin(i * 0.61) * math.sin(i * 0.19 + 0.8))
        h = 3 if pause[0] <= i <= pause[1] else 6 + 44 * a
        b.append(f'<rect class="wb" style="animation-delay:-{i * 0.09:.2f}s" x="{x0 + i * step - 1.7:.1f}" '
                 f'y="{cy - h / 2:.1f}" width="3.4" height="{h:.1f}" rx="1.7" fill="{cyan}"/>')
    pts = []
    for k in range(45):
        x = x0 + (x1 - x0) * k / 44
        flat = pause[0] - 1 <= (x - x0) / step <= pause[1] + 1
        y = VY + 104 + (1.5 if flat else 11) * math.sin(k * 0.55) * (0.6 + 0.4 * math.sin(k * 0.17))
        pts.append(f"{x:.1f},{y:.1f}")
    length = (x1 - x0) * 1.6
    css.append(kf("line", cycle, [(0, f"stroke-dashoffset:{length:.0f}"), (2.2, "stroke-dashoffset:0"),
                                  (4.6, "stroke-dashoffset:0"), (cycle, f"stroke-dashoffset:{-length:.0f}")]))
    b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{purple}" stroke-width="2" stroke-linecap="round" '
             f'stroke-linejoin="round" stroke-dasharray="{length:.0f}" style="{anim("line", cycle, "ease-in-out")}"/>')
    css.append(f"@keyframes ph{{from{{transform:translateX(0)}}to{{transform:translateX({x1 - x0:.1f}px)}}}}")
    b.append(f'<line class="rm-hide" style="{anim("ph", cycle)}" x1="{x0}" y1="{VY + 12}" x2="{x0}" y2="{VY + 122}" '
             f'stroke="{ink}" stroke-width="1.3" stroke-opacity=".85"/>')
    return css, b


def vis_verdict(c):
    """PARAKH: thirty test cases tick green, then one verdict stamps in."""
    css, b = [], []
    green, muted, cycle = c.acc("green"), c.t["muted"], 7.0
    size, gap = 15, 5
    gx, gy = VX + (VW - (6 * size + 5 * gap)) / 2, VY + 6
    css.append(".cell{transform-box:fill-box;transform-origin:center}")
    for k in range(30):
        x, y, t0 = gx + (k % 6) * (size + gap), gy + (k // 6) * (size + gap), 0.4 + k * 0.07
        css.append(show(f"c{k}", cycle, t0, 6.1, "transform:scale(.3)", "transform:scale(1)"))
        b.append(f'<g class="cell" style="{anim(f"c{k}", cycle)}"><rect x="{x:.1f}" y="{y}" width="{size}" height="{size}" '
                 f'rx="3.5" fill="{green}" fill-opacity=".2" stroke="{green}" stroke-opacity=".7"/>'
                 + check(x + 3.6, y + 7.6, green, 0.75) + "</g>")
    sx, sy = VX + VW / 2, VY + 52
    css.append(show("stamp", cycle, 2.7, 6.1, "transform:rotate(-10deg) scale(1.8)", "transform:rotate(-10deg) scale(1)"))
    css.append(f".stamp{{transform-origin:{sx:.0f}px {sy}px;transform:rotate(-10deg)}}")
    b.append(f'<g class="stamp" style="{anim("stamp", cycle, "ease-out")}">'
             f'<rect x="{sx - 54:.1f}" y="{sy - 21}" width="108" height="42" rx="7" fill="{c.t["bg"]}" fill-opacity=".88" '
             f'stroke="{green}" stroke-width="2.5"/>'
             + txt(sx, sy + 8, "SAFE", green, 22, 800, "middle", ' letter-spacing="3"') + "</g>")
    css.append(show("sub", cycle, 2.9, 6.1))
    b.append(f'<g style="{anim("sub", cycle)}">' + txt(sx, VY + 124, "30 / 30 passed", muted, 10, anchor="middle") + "</g>")
    return css, b


def vis_balance(c):
    """TARAZU: a balance scale settles while the instrument's readout steadies."""
    css, b = [], []
    gold, muted, cycle = c.acc("gold"), c.t["muted"], 5.0
    cx, py0, half = VX + VW / 2, VY + 16, 56
    b.append(f'<path d="M{cx - 24:.1f} {VY + 84}h48l-7 -8h-34z" fill="{gold}" fill-opacity=".35" stroke="{gold}" stroke-width="1.4"/>')
    b.append(f'<line x1="{cx:.1f}" y1="{py0}" x2="{cx:.1f}" y2="{VY + 76}" stroke="{gold}" stroke-width="3" stroke-linecap="round"/>')
    swing = [(0, -11), (0.9, 7), (1.7, -4), (2.4, 2), (3.0, -0.8), (3.5, 0), (cycle, 0)]
    css.append(kf("beam", cycle, [(t, f"transform:rotate({a}deg)") for t, a in swing]))
    css.append(kf("pan", cycle, [(t, f"transform:rotate({-a}deg)") for t, a in swing]))
    pans = []
    for side in (-1, 1):
        hx = cx + side * half
        load = (f'<rect x="{hx - 8:.1f}" y="{py0 + 22}" width="16" height="11" rx="2" fill="{gold}"/>' if side < 0 else
                f'<rect x="{hx - 10:.1f}" y="{py0 + 26}" width="8" height="7" rx="1.5" fill="{gold}"/>'
                f'<rect x="{hx + 1:.1f}" y="{py0 + 23}" width="9" height="10" rx="1.5" fill="{gold}"/>')
        pans.append(f'<g style="transform-origin:{hx:.1f}px {py0}px;{anim("pan", cycle, "ease-in-out")}">'
                    f'<path d="M{hx:.1f} {py0}L{hx - 18:.1f} {py0 + 33}M{hx:.1f} {py0}L{hx + 18:.1f} {py0 + 33}" '
                    f'stroke="{muted}" stroke-width="1"/>' + load +
                    f'<path d="M{hx - 21:.1f} {py0 + 33}Q{hx:.1f} {py0 + 47} {hx + 21:.1f} {py0 + 33}z" fill="{gold}" '
                    f'fill-opacity=".25" stroke="{gold}" stroke-width="1.8"/></g>')
    b.append(f'<g style="transform-origin:{cx:.1f}px {py0}px;{anim("beam", cycle, "ease-in-out")}">'
             f'<line x1="{cx - half - 2:.1f}" y1="{py0}" x2="{cx + half + 2:.1f}" y2="{py0}" stroke="{gold}" '
             f'stroke-width="3" stroke-linecap="round"/>' + "".join(pans) + "</g>")
    b.append(f'<circle cx="{cx:.1f}" cy="{py0}" r="4" fill="{c.t["bg"]}" stroke="{gold}" stroke-width="2"/>')
    lx, ly, lw, lh = VX + 18, VY + 96, VW - 36, 30
    b.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="6" fill="{gold}" fill-opacity=".08" '
             f'stroke="{gold}" stroke-opacity=".6"/>')
    b.append(txt(lx + 8, ly + 19, "R-76", muted, 9))
    for k, (value, t0, t1) in enumerate((("0.000 kg", 0, 0.8), ("1.274 kg", 0.8, 1.6), ("0.986 kg", 1.6, 2.3))):
        css.append(kf(f"r{k}", cycle, [(0, "opacity:0"), (t0, "opacity:1"), (t1, "opacity:0"), (cycle, "opacity:0")]))
        b.append(f'<g style="opacity:0;animation:r{k} {cycle}s steps(1,end) infinite">'
                 + txt(lx + lw - 8, ly + 21, value, gold, 15, 700, "end") + "</g>")
    css.append(kf("rf", cycle, [(0, "opacity:0"), (2.3, "opacity:1"), (cycle, "opacity:1")]))
    b.append(f'<g style="animation:rf {cycle}s steps(1,end) infinite">'
             + txt(lx + lw - 8, ly + 21, "1.000 kg", gold, 15, 700, "end") + "</g>")
    return css, b


def vis_label_scan(c):
    """SAKSHYA: a package label scanned; declarations found, one flagged as missing."""
    css, b = [], []
    mag, green, red, ink, muted, cycle = (c.acc("magenta"), c.acc("green"), c.acc("red"), c.t["ink"], c.t["muted"], 6.0)
    bx, by, bw, bh = VX + 6, VY + 12, 98, 114
    b.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="7" fill="{mag}" fill-opacity=".06" '
             f'stroke="{muted}" stroke-opacity=".7"/>')
    b.append(f'<path d="M{bx + 8} {by}l8 -7h{bw - 32}l8 7" fill="none" stroke="{muted}" stroke-opacity=".6"/>')
    b.append(f'<rect x="{bx + 10}" y="{by + 12}" width="50" height="8" rx="2" fill="{ink}" fill-opacity=".75"/>')
    rows = [(by + 36, 26, 38), (by + 56, 16, 34), (by + 76, 30, 30), (by + 96, None, None)]

    def when(y):
        return 0.3 + 2.4 * (y - by) / bh                   # when the scan line reaches y

    for k, (y, kw, vw) in enumerate(rows):
        if kw:
            b.append(f'<rect x="{bx + 10}" y="{y - 3}" width="{kw}" height="6" rx="2" fill="{muted}" fill-opacity=".8"/>')
            b.append(f'<rect x="{bx + 15 + kw}" y="{y - 3}" width="{vw}" height="6" rx="2" fill="{ink}" fill-opacity=".45"/>')
        css.append(show(f"bb{k}", cycle, when(y), 5.6))
        b.append(f'<rect style="{anim(f"bb{k}", cycle)}" x="{bx + 5}" y="{y - 8}" width="{bw - 10}" height="16" rx="3" '
                 f'fill="none" stroke="{mag if kw else red}" stroke-width="1.4" stroke-dasharray="3 2"/>')
    b.append(f'<defs><linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mag}" '
             f'stop-opacity="0"/><stop offset="1" stop-color="{mag}" stop-opacity=".45"/></linearGradient></defs>')
    css.append(kf("scan", cycle, [(0, "transform:translateY(0);opacity:0"), (0.3, "transform:translateY(0);opacity:1"),
                                  (2.7, f"transform:translateY({bh}px);opacity:1"),
                                  (2.85, f"transform:translateY({bh}px);opacity:0"), (cycle, "opacity:0")]))
    b.append(f'<g class="rm-hide" style="opacity:0;{anim("scan", cycle)}"><rect x="{bx}" y="{by - 16}" width="{bw}" '
             f'height="16" fill="url(#beam)"/><rect x="{bx}" y="{by - 1}" width="{bw}" height="2" fill="{mag}"/></g>')
    for k, ((label, ok), (y, _, _)) in enumerate(zip((("qty", True), ("MRP", True), ("date", True), ("care", False)), rows)):
        css.append(show(f"it{k}", cycle, when(y) + 0.1, 5.6, "transform:translateX(-5px)", "transform:translateX(0)"))
        mark = check(VX + 114, y - 0.5, green, 0.8) if ok else cross(VX + 118, y, red, 3)
        b.append(f'<g style="{anim(f"it{k}", cycle)}">{mark}' + txt(VX + 128, y + 3.5, label, ink if ok else red, 10) + "</g>")
    return css, b


CPP = [  # from the Fibonacci solution in the leetcode-solutions repo, lightly reformatted
    (0, "int fib(int n) {"), (1, "if (n <= 1) return n;"), (1, "vector<int> dp(n+1);"), (1, "dp[0]=0; dp[1]=1;"),
    (1, "for (int i=2; i<=n; i++)"), (2, "dp[i]=dp[i-1]+dp[i-2];"), (1, "return dp[n];"), (0, "}"),
]


def vis_code(c):
    """leetcode-solutions: a real solution from the repo typing itself out."""
    css, b = [], []
    kw, num, fn, ink, muted, amber, cycle = (c.acc("red"), c.acc("blue"), c.acc("purple"), c.t["ink"], c.t["muted"],
                                             c.acc("amber"), 9.0)
    b.append(f'<rect x="{VX}" y="{VY + 2}" width="{VW}" height="{VH - 6}" rx="8" fill="{c.t["panel"]}" stroke="{c.t["border"]}"/>')
    cw, lh, size, x0, y0 = 5.15, 12.4, 8.6, VX + 22, VY + 20
    code, covers, t = [], [], 0.4
    for i, (indent, line) in enumerate(CPP):
        y = y0 + i * lh
        b.append(txt(VX + 15, y, i + 1, muted, 8, anchor="end", extra=' fill-opacity=".7"'))
        spans = "".join(f'<tspan fill="{kw if tok in ("int", "if", "return", "for", "vector") else num if tok.isdigit() else fn if tok == "fib" else ink}">'
                        f"{escape(tok)}</tspan>" for tok in re.findall(r"[A-Za-z_]\w*|\d+|\s+|.", line))
        x, width = x0 + indent * 2 * cw, len(line) * cw
        code.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-family="{MONO}" textLength="{width:.1f}" '
                    f'xml:space="preserve">{spans}</text>')
        t1 = t + len(line) * 0.032
        css.append(kf(f"ty{i}", cycle, [(0, "transform:translateX(0)"), (t, "transform:translateX(0)"),
                                        (t1, f"transform:translateX({width + 2:.1f}px)"),
                                        (cycle, f"transform:translateX({width + 2:.1f}px)")]))
        css.append(kf(f"cu{i}", cycle, [(0, "opacity:0"), (t, "opacity:1"),
                                        (t1 + (8.6 - t1 if i == len(CPP) - 1 else 0.05), "opacity:0"), (cycle, "opacity:0")]))
        covers.append(f'<g class="rm-hide" style="animation:ty{i} {cycle}s steps({len(line)},end) infinite">'
                      f'<rect x="{x - 1:.1f}" y="{y - 8.5:.1f}" width="{width + 6:.1f}" height="{lh:.1f}" fill="{c.t["panel"]}"/>'
                      f'<rect style="opacity:0;animation:cu{i} {cycle}s steps(1,end) infinite" x="{x - 1:.1f}" '
                      f'y="{y - 8:.1f}" width="5" height="10" fill="{amber}"/></g>')
        t = t1 + 0.18
    css.append(kf("code", cycle, [(0, "opacity:1"), (8.4, "opacity:1"), (8.85, "opacity:0"), (cycle, "opacity:0")]))
    b.append(f'<g style="{anim("code", cycle)}">' + "".join(code) + "".join(covers) + "</g>")
    return css, b


def vis_api(c):
    """CloudForge: requests reach the Express server while the log fills with real endpoints."""
    css, b = [], []
    blue, green, yellow, red, ink, muted, cycle = (c.acc("blue"), c.acc("green"), c.acc("yellow"), c.acc("red"),
                                                   c.t["ink"], c.t["muted"], 8.0)
    cy, xc, xs, xd = VY + 22, VX + 14, VX + 82, VX + 150
    b.append(f'<line x1="{xc + 14}" y1="{cy}" x2="{xs - 26}" y2="{cy}" stroke="{muted}" stroke-dasharray="2 3"/>'
             f'<line x1="{xs + 26}" y1="{cy}" x2="{xd - 12}" y2="{cy}" stroke="{muted}" stroke-dasharray="2 3"/>')
    b.append(f'<rect x="{xc - 11}" y="{cy - 9}" width="22" height="14" rx="2" fill="none" stroke="{ink}" stroke-width="1.3"/>'
             f'<path d="M{xc - 14} {cy + 8}h28" stroke="{ink}" stroke-width="1.5" stroke-linecap="round"/>')
    css.append(".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}"
               "@keyframes pulse{from{transform:scale(1);opacity:.7}to{transform:scale(1.6);opacity:0}}")
    b.append(f'<rect class="pulse rm-hide" x="{xs - 26}" y="{cy - 15}" width="52" height="30" rx="7" fill="none" stroke="{blue}"/>'
             f'<rect x="{xs - 26}" y="{cy - 15}" width="52" height="30" rx="7" fill="{blue}" fill-opacity=".12" '
             f'stroke="{blue}" stroke-width="1.5"/>' + txt(xs, cy - 1, "express", blue, 9, 700, "middle")
             + txt(xs, cy + 10, ":3000", muted, 8, anchor="middle"))
    b.append(f'<ellipse cx="{xd}" cy="{cy - 8}" rx="11" ry="3.5" fill="none" stroke="{ink}" stroke-width="1.2"/>'
             f'<path d="M{xd - 11} {cy - 8}v15a11 3.5 0 0 0 22 0v-15" fill="none" stroke="{ink}" stroke-width="1.2"/>')
    log = [("POST", "/api/projects", "201"), ("GET", "/api/projects", "200"), ("PUT", "/api/projects/1", "200"),
           ("GET", "/api/projects/9", "404"), ("DELETE", "/api/projects/1", "200")]
    colour = {"POST": blue, "GET": green, "PUT": yellow, "DELETE": red}
    for i, (method, path, status) in enumerate(log):
        y, t0 = VY + 58 + i * 15, 0.5 + i * 1.2
        css.append(show(f"lg{i}", cycle, t0, 7.3))
        b.append(f'<g style="{anim(f"lg{i}", cycle)}">' + txt(VX + 2, y, method, colour[method], 8.6, 700)
                 + txt(VX + 42, y, path, ink, 8.6)
                 + txt(VX + VW - 2, y, status, green if status < "300" else yellow, 8.6, 700, "end") + "</g>")
        css.append(kf(f"pk{i}", cycle, [(0, "opacity:0;transform:translateX(0)"), (t0 - 0.45, "opacity:0;transform:translateX(0)"),
                                        (t0 - 0.4, "opacity:1;transform:translateX(0)"),
                                        (t0, f"opacity:1;transform:translateX({xs - xc - 40}px)"),
                                        (t0 + 0.05, f"opacity:0;transform:translateX({xs - xc - 40}px)"), (cycle, "opacity:0")]))
        b.append(f'<circle class="rm-hide" style="opacity:0;{anim(f"pk{i}", cycle)}" cx="{xc + 14}" cy="{cy}" r="3" '
                 f'fill="{colour[method]}"/>')
    return css, b


def vis_tasks(c):
    """TaskForge: the day's progress ring, tasks ticking off, a week of analytics."""
    css, b = [], []
    vio, ink, muted, cycle = c.acc("violet"), c.t["ink"], c.t["muted"], 7.0
    cx, cy, r = VX + 36, VY + 40, 30
    circ = 2 * math.pi * r
    done = circ * (1 - 0.72)
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c.t["faint"]}" stroke-width="8"/>')
    css.append(kf("ring", cycle, [(0, f"stroke-dashoffset:{circ:.1f}"), (0.3, f"stroke-dashoffset:{circ:.1f}"),
                                  (2.2, f"stroke-dashoffset:{done:.1f}"), (6.5, f"stroke-dashoffset:{done:.1f}"),
                                  (6.9, f"stroke-dashoffset:{circ:.1f}"), (cycle, f"stroke-dashoffset:{circ:.1f}")]))
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{vio}" stroke-width="8" stroke-linecap="round" '
             f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="{done:.1f}" transform="rotate(-90 {cx} {cy})" '
             f'style="{anim("ring", cycle, "ease-out")}"/>')
    b.append(txt(cx, cy + 3.5, "today", ink, 10, 700, "middle"))
    tx = VX + 80
    for k, (t0, width) in enumerate(((2.4, 64), (3.1, 50), (3.8, 58))):
        y = VY + 20 + k * 20
        b.append(f'<rect x="{tx}" y="{y - 6}" width="11" height="11" rx="2.5" fill="none" stroke="{muted}"/>')
        b.append(f'<rect x="{tx + 18}" y="{y - 2.5}" width="{width}" height="5" rx="2.5" fill="{muted}" fill-opacity=".45"/>')
        css.append(show(f"tk{k}", cycle, t0, 6.5))
        b.append(f'<g style="{anim(f"tk{k}", cycle)}"><rect x="{tx}" y="{y - 6}" width="11" height="11" rx="2.5" fill="{vio}"/>'
                 f'{check(tx + 2.2, y - 0.6, c.t["bg"], 0.7)}<rect x="{tx + 18}" y="{y - 2.5}" width="{width}" height="5" '
                 f'rx="2.5" fill="{vio}" fill-opacity=".55"/></g>')
    base = VY + 118
    for k, (day, hgt) in enumerate(zip("MTWTFSS", (0.45, 0.7, 0.55, 0.9, 0.65, 0.35, 0.8))):
        x = VX + 8 + k * 23
        css.append(kf(f"wk{k}", cycle, [(0, "transform:scaleY(0)"), (0.6 + k * 0.12, "transform:scaleY(0)"),
                                        (1.2 + k * 0.12, "transform:scaleY(1)"), (6.5, "transform:scaleY(1)"),
                                        (6.8, "transform:scaleY(0)"), (cycle, "transform:scaleY(0)")]))
        b.append(f'<rect style="transform-origin:0 {base}px;{anim(f"wk{k}", cycle, "ease-out")}" x="{x}" '
                 f'y="{base - 30 * hgt:.1f}" width="13" height="{30 * hgt:.1f}" rx="3" fill="{vio}" fill-opacity=".75"/>')
        b.append(txt(x + 6.5, base + 12, day, muted, 8, anchor="middle"))
    return css, b


def vis_hindi(c):
    """Hindi text restoration: shuffled words put back in order, punctuated, then translated."""
    css, b = [], []
    coral, ink, muted, cycle = c.acc("coral"), c.t["ink"], c.t["muted"], 8.0
    ordered, start_slot = ["आज", "मौसम", "अच्छा", "है"], {0: 1, 1: 3, 2: 0, 3: 2}
    slot_x = [VX + 21 + k * 41 for k in range(4)]
    y0, ch, cw = VY + 22, 28, 37
    for j, word in enumerate(ordered):
        dx = slot_x[start_slot[j]] - slot_x[j]
        lift = -10 if dx < 0 else 10
        css.append(kf(f"w{j}", cycle, [(0, f"transform:translate({dx}px,0)"), (1.2, f"transform:translate({dx}px,0)"),
                                       (1.65, f"transform:translate({dx / 2:.0f}px,{lift}px)"),
                                       (2.1, "transform:translate(0,0)"), (cycle, "transform:translate(0,0)")]))
        x = slot_x[j]
        shift = -4 if j == 3 else 0
        b.append(f'<g style="{anim(f"w{j}", cycle, "ease-in-out")}"><rect x="{x - cw / 2:.1f}" y="{y0}" width="{cw}" '
                 f'height="{ch}" rx="7" fill="{coral}" fill-opacity=".1" stroke="{coral}" stroke-opacity=".7"/>'
                 + txt(x + shift, y0 + 19, word, ink, 12.5, 600, "middle", family=DEVANAGARI) + "</g>")
    css.append(show("da", cycle, 2.4, 7.4))
    b.append(f'<g style="{anim("da", cycle)}">'
             + txt(slot_x[3] + 10, y0 + 19.5, "।", coral, 14, 700, "middle", family=DEVANAGARI) + "</g>")
    b.append(f'<path d="M{VX + VW / 2:.1f} {VY + 64}v10m-4 -4l4 4 4 -4" fill="none" stroke="{muted}" stroke-width="1.4" '
             f'stroke-linecap="round" stroke-linejoin="round"/>')
    css.append(show("en", cycle, 3.1, 7.4, "transform:translateY(6px)", "transform:translateY(0)"))
    b.append(f'<g style="{anim("en", cycle, "ease-out")}">'
             + txt(VX + VW / 2, VY + 98, "The weather is", ink, 12, 600, "middle", family=SANS)
             + txt(VX + VW / 2, VY + 114, "nice today.", ink, 12, 600, "middle", family=SANS) + "</g>")
    return css, b


VISUALS = {"waveform": vis_waveform, "verdict": vis_verdict, "balance": vis_balance, "label-scan": vis_label_scan,
           "code": vis_code, "api": vis_api, "tasks": vis_tasks, "hindi": vis_hindi}


# ---------------------------------------------------------------- the card

def wrap(s, width, max_lines):
    lines, line = [], ""
    for word in s.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return lines[:max_lines], len(lines) > max_lines


def render(card, mode, phase=0.0):
    """card: title, badge, about, stack, stars, link, caption, accent, visual. Returns the SVG text."""
    c = Ctx(mode)
    t, accent = c.t, c.acc(card["accent"])
    css, body = VISUALS[card["visual"]](c)
    r = 14
    perim = 2 * (W - 1 + H - 1) - 8 * r + 2 * math.pi * r
    css.append(f"@keyframes orbit{{from{{stroke-dashoffset:{perim:.1f}}}to{{stroke-dashoffset:0}}}}"
               f".orbit{{animation:orbit 10s linear infinite;animation-delay:-{phase:.2f}s}}")
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}.rm-hide,.orbit{display:none}}")
    out = [f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{r}" fill="{t["bg"]}" stroke="{t["border"]}"/>']
    for width, opacity in ((5, 0.18), (1.6, 0.95)):        # a soft glow under a crisp line
        out.append(f'<rect class="orbit" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="{r}" fill="none" '
                   f'stroke="{accent}" stroke-width="{width}" stroke-opacity="{opacity}" stroke-linecap="round" '
                   f'stroke-dasharray="110 {perim - 110:.1f}"/>')
    out.append(txt(28, 52, card["title"], t["ink"], 25, 700, family=SANS))
    if card.get("badge"):
        bw = len(card["badge"]) * 6.9 + 34
        out.append(f'<rect x="28" y="66" width="{bw:.1f}" height="25" rx="12.5" fill="{accent}" fill-opacity=".12" '
                   f'stroke="{accent}" stroke-opacity=".55"/><circle cx="41" cy="78.5" r="3.5" fill="{accent}"/>')
        out.append(txt(51, 82.5, card["badge"], accent, 11.5, 700))
    lines, cut = wrap(card["about"], 45, 4)
    if cut:
        print("WARNING: description cut short for", card["title"])
    for i, line in enumerate(lines):
        out.append(txt(28, 120 + i * 20, line, t["ink"], 14, family=SANS))
    out.append(txt(28, H - 20, card.get("stack", ""), t["muted"], 11.5))
    right = []
    if card.get("stars"):
        right.append(f"★ {card['stars']}")
    if card.get("link"):
        right.append(f"↗ {card['link']}")
    if right:
        out.append(txt(W - 26, H - 20, "  ·  ".join(right), t["muted"], 11.5, anchor="end"))
    out.append("<g>" + "".join(body) + "</g>")
    if card.get("caption"):
        out.append(txt(VX + VW / 2, VY + VH + 20, card["caption"], t["muted"], 10, anchor="middle"))
    label = escape(f"{card['title']}: {card['about']}", quote=True)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="{label}"><title>{label}</title><style>{"".join(css)}</style>' + "".join(out) + "</svg>\n")
