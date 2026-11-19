#!/usr/bin/env python3
"""Generate every SVG the profile README shows.

Standard library only, so it runs in GitHub Actions without installing anything.
Edit data/profile.json to change the words; this file only draws.

    python scripts/build.py

Set GITHUB_TOKEN to avoid the anonymous API rate limit (the workflow does).
"""
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import urllib.parse
import urllib.request
from base64 import b64encode
from html import escape, unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
ASSETS = ROOT / "assets"
CFG = json.loads((ROOT / "data" / "profile.json").read_text(encoding="utf-8"))
LOGIN = CFG["login"]
TOKEN = os.environ.get("GITHUB_TOKEN", "")
CACHE = os.environ.get("PROFILE_CACHE")          # optional dir, handy while iterating locally
FONT = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"

THEMES = {
    "dark": dict(bg="#0d1117", border="#30363d", ink="#e6edf3", muted="#8b949e", grid="#21262d",
                 accent="#a78bfa", ramp=["#161b22", "#4c2f9e", "#7c5cf0", "#a78bfa", "#c4b5fd"]),
    "light": dict(bg="#ffffff", border="#d0d7de", ink="#1f2328", muted="#656d76", grid="#e4e8ec",
                  accent="#7c3aed", ramp=["#ebedf0", "#ddd6fe", "#a78bfa", "#7c5cf0", "#4c2f9e"]),
}
LANG_COLOURS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#663399", "C++": "#f34b7d", "Jupyter Notebook": "#DA5B0B", "Dockerfile": "#384d54",
    "Shell": "#89e051", "C": "#555555", "Java": "#b07219", "Go": "#00ADD8", "Rust": "#dea584",
}
OTHER_COLOUR = "#8b949e"


# ---------------------------------------------------------------- data

def fetch(url, payload=None):
    key = hashlib.sha1((url + (payload or "")).encode()).hexdigest()
    if CACHE and (Path(CACHE) / key).exists():
        return (Path(CACHE) / key).read_text(encoding="utf-8")
    req = urllib.request.Request(url, data=payload.encode() if payload else None,
                                 headers={"User-Agent": "profile-readme-build",
                                          "Accept": "application/vnd.github+json"})
    if TOKEN and "api.github.com" in url:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    if CACHE:
        Path(CACHE).mkdir(parents=True, exist_ok=True)
        (Path(CACHE) / key).write_text(body, encoding="utf-8")
    return body


def api(path):
    return json.loads(fetch("https://api.github.com" + path))


def calendar_graphql():
    query = ("query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{"
             "weeks{contributionDays{date contributionCount contributionLevel}}}}}}")
    body = json.loads(fetch("https://api.github.com/graphql",
                            json.dumps({"query": query, "variables": {"l": LOGIN}})))
    levels = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"], levels[d["contributionLevel"]])
            for w in weeks for d in w["contributionDays"]]


def calendar_html():
    page = fetch(f"https://github.com/users/{LOGIN}/contributions")
    counts = {}
    for cell_id, text in re.findall(r'<tool-tip[^>]*?for="([\w-]+)"[^>]*>([^<]*)</tool-tip>', page):
        m = re.match(r"\s*([\d,]+) contribution", unescape(text))
        counts[cell_id] = int(m.group(1).replace(",", "")) if m else 0
    cells = re.findall(r'<td[^>]*?data-date="([\d-]+)"[^>]*?id="([\w-]+)"[^>]*?data-level="(\d)"', page)
    if not cells:
        raise RuntimeError("could not read the contribution calendar")
    return [(date, counts.get(cell_id, 0), int(level)) for date, cell_id, level in cells]


def load_calendar():
    days = None
    if TOKEN:
        try:
            days = calendar_graphql()
        except Exception as err:                      # fall back to the public page
            print("graphql calendar failed, using public page:", err)
    days = sorted(days or calendar_html())
    longest = run = 0
    for _, count, _ in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    tail = days[:-1] if days[-1][1] == 0 else days    # today may simply not have happened yet
    current = 0
    for _, count, _ in reversed(tail):
        if not count:
            break
        current += 1
    return dict(days=days, total=sum(d[1] for d in days), longest=longest, current=current,
                active=sum(1 for d in days if d[1]), best=max(d[1] for d in days))


def leetcode_stats():
    """Live solved counts from LeetCode's public profile data; the numbers in data/profile.json are the
    fallback when LeetCode cannot be reached (it sometimes refuses automated requests).
    Set LEETCODE_LIVE=0 to skip the request."""
    saved = dict(CFG.get("leetcode", {}), live=False)
    user = saved.get("username")
    if not user or os.environ.get("LEETCODE_LIVE", "1") == "0":
        return saved
    query = ("query($u:String!){matchedUser(username:$u){submitStatsGlobal{acSubmissionNum{difficulty count}}"
             "badges{id} userCalendar{streak totalActiveDays}}}")
    try:
        req = urllib.request.Request(
            "https://leetcode.com/graphql/", data=json.dumps({"query": query, "variables": {"u": user}}).encode(),
            headers={"Content-Type": "application/json", "Referer": f"https://leetcode.com/u/{user}/",
                     "User-Agent": "profile-readme-build"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            live = parse_leetcode(json.loads(resp.read().decode("utf-8")))
    except Exception as err:
        print("LeetCode not reachable, using the saved numbers:", err)
        return saved
    return dict(saved, **live, live=True, as_of=dt.date.today().isoformat())


def parse_leetcode(body):
    user = body["data"]["matchedUser"]
    counts = {row["difficulty"].lower(): row["count"] for row in user["submitStatsGlobal"]["acSubmissionNum"]}
    out = {"solved": counts["all"], "easy": counts["easy"], "medium": counts["medium"], "hard": counts["hard"]}
    if user.get("badges") is not None:
        out["badges"] = len(user["badges"])
    calendar = user.get("userCalendar") or {}
    if calendar.get("streak"):
        out["max_streak_days"] = calendar["streak"]
    return out


def load():
    user = api(f"/users/{LOGIN}")
    repos = [r for r in api(f"/users/{LOGIN}/repos?per_page=100&type=owner") if not r["fork"]]
    by_name = {r["name"]: r for r in repos}

    lc = dict(total=0, topics={}, levels={}, bytes=0)
    lc_repo = by_name.get(CFG.get("leetcode_repo", ""))
    if lc_repo:
        tree = api(f"/repos/{LOGIN}/{lc_repo['name']}/git/trees/{lc_repo['default_branch']}?recursive=1")
        for node in tree["tree"]:
            parts = node["path"].split("/")
            if node["type"] == "blob" and len(parts) == 3 and re.match(r"\d+\.", parts[2]):
                lc["total"] += 1
                lc["topics"][parts[0]] = lc["topics"].get(parts[0], 0) + 1
                lc["levels"][parts[1]] = lc["levels"].get(parts[1], 0) + 1
                lc["bytes"] += node.get("size", 0)

    langs = {}
    overrides = CFG.get("language_overrides", {})
    for r in repos:
        if r["name"] in overrides:                    # files GitHub cannot classify on its own
            if lc_repo and r["name"] == lc_repo["name"]:
                langs[overrides[r["name"]]] = langs.get(overrides[r["name"]], 0) + lc["bytes"]
            continue
        for lang, size in api(f"/repos/{LOGIN}/{r['name']}/languages").items():
            langs[lang] = langs.get(lang, 0) + size

    return dict(user=user, repos=by_name, lc=lc, langs=langs, cal=load_calendar(), leet=leetcode_stats(),
                stars=sum(r["stargazers_count"] for r in repos))


# ---------------------------------------------------------------- drawing helpers

def num(n):
    return f"{n:,}"


def shade(hex_colour, k):
    rgb = [int(hex_colour[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(c * k) for c in rgb)


def pts(points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def text(x, y, s, fill, size=12, weight=400, anchor="start", extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{extra}>{escape(str(s))}</text>')


def svg(w, h, body, label, style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{escape(label, quote=True)}"><title>{escape(label)}</title>'
            f'<style>text{{font-family:{FONT}}}{style}</style>{body}</svg>\n')


def frame(w, h, t):
    return (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
            f'fill="{t["bg"]}" stroke="{t["border"]}"/>')


def wrap(s, width, max_lines):
    lines, line = [], ""
    for word in s.split():
        if len(line) + len(word) + (1 if line else 0) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:width - 1].rstrip(" ,.;") + "…"
    return lines


def write(name, content):
    (ASSETS / name).write_text(content, encoding="utf-8", newline="\n")


# ---------------------------------------------------------------- hero terminal

def fills(d):
    """Values that the words in data/profile.json can refer to, such as {lc_solved}."""
    return dict(lc_solved=num(d["leet"].get("solved", d["lc"]["total"])),
                lc_repo=num(d["lc"]["total"]), contrib=num(d["cal"]["total"]),
                repos=d["user"]["public_repos"])


def hero(d):
    t = THEMES["dark"]                            # a terminal is dark in either GitHub theme
    fill = fills(d)
    art_path = ROOT / "data" / "art.json"
    art = json.loads(art_path.read_text(encoding="utf-8")) if art_path.exists() else dict(w=230, h=250, dots=[])
    AX, AY = 28, 86                               # top-left corner of the art
    W, H, CW = 800, AY + art["h"] + 56, 7.8       # CW: forced advance of a 13px monospace glyph
    tx = 28 + 2 * CW                              # where typed text starts, after "$ "
    photo = art.get("photo")                       # optional: the real photo, shown before it turns into dots
    t_in = 1.15                                   # the photo appears once `neofetch` has been typed
    t0 = 2.9 if photo else 1.1                    # when the scan starts and the dots assemble
    sweep = 1.6 if photo else 1.5                 # how long the scan takes to cross the portrait
    css, body = [], []

    css.append(
        "@keyframes rise{from{opacity:0;transform:translateY(6px)}}"
        "@keyframes pop{from{opacity:0;transform:scale(1.18)}}"
        "@keyframes blink{50%{opacity:0}}"
        "@keyframes gone{to{opacity:0}}"
        f"@keyframes cmd{{to{{transform:translateX({8 * CW:.1f}px)}}}}"
        f"@keyframes scan{{0%{{opacity:0;transform:translateY(0)}}6%,92%{{opacity:1}}"
        f"100%{{opacity:0;transform:translateY({art['h']}px)}}}}"
        ".row{animation:rise .45s cubic-bezier(.2,.7,.2,1) backwards}"
        f".dg{{transform-origin:{AX + art['w'] / 2:.0f}px {AY + art['h'] / 2:.0f}px;"
        "animation:pop .55s cubic-bezier(.2,.7,.2,1) backwards}"
        f".scan{{opacity:0;animation:scan {sweep}s linear {t0}s}}"
        f"@keyframes again{{0%{{opacity:0;transform:translateY(0)}}2%,16%{{opacity:.45}}"
        f"18%,100%{{opacity:0;transform:translateY({art['h']}px)}}}}"
        f".scan2{{opacity:0;animation:again 10s linear {t0 + sweep + 5:.1f}s infinite}}"
        "@keyframes phin{from{opacity:0;transform:scale(1.035)}to{opacity:1;transform:none}}"
        "@keyframes phout{to{opacity:0}}"
        f".ph{{opacity:0;transform-origin:{AX + art['w'] / 2:.0f}px {AY + art['h'] / 2:.0f}px;"
        f"animation:phin .7s cubic-bezier(.2,.7,.2,1) {t_in}s both}}"
        ".st{animation:phout .45s ease-in forwards}"
        ".cur{animation:blink 1s steps(1) infinite}"
        ".c0{animation:cmd .7s steps(8) .4s forwards}"
        ".c0 .cur{animation:gone .01s 1.2s forwards}"
        ".tl{opacity:0}"
    )

    # window chrome
    body.append(f'<clipPath id="win"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12"/></clipPath>'
                '<linearGradient id="glow" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7c5cf0" '
                'stop-opacity="0"/><stop offset="1" stop-color="#7c5cf0" stop-opacity=".3"/></linearGradient>')
    body.append(f'<g clip-path="url(#win)"><rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    body.append(f'<rect width="{W}" height="36" fill="#161b22"/>'
                f'<line x1="0" y1="36.5" x2="{W}" y2="36.5" stroke="{t["border"]}"/>')
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        body.append(f'<circle cx="{22 + i * 20}" cy="18" r="6" fill="{c}"/>')
    body.append(text(W / 2, 22.5, CFG["terminal_title"], t["muted"], 12, anchor="middle"))

    # $ neofetch
    body.append(text(28, 66, "$", t["accent"], 13, 700))
    body.append(text(tx, 66, "neofetch", t["ink"], 13, extra=f' textLength="{8 * CW:.1f}"'))
    body.append(f'<g class="c0"><rect x="{tx:.1f}" y="52" width="{W}" height="20" fill="{t["bg"]}"/>'
                f'<rect class="cur" x="{tx:.1f}" y="54" width="8" height="15" fill="{t["accent"]}"/></g>')

    # glitch style: the photo fades in clear, holds, glitches, settles into the glitch look,
    # then twitches briefly every few seconds. Hard cuts between pre-made frames (see scripts/glitchify.py).
    gl = art.get("glitch")
    if gl:
        gx, gy, gw, gh = AX + gl["x"], AY + gl["y"], gl["w"], gl["h"]
        frames = [gl["clean"], gl["rest"]] + gl["burst"]
        ids = ["gc", "gr"] + [f"gb{i}" for i in range(len(gl["burst"]))]
        body.append("<defs>" + "".join(
            f'<image id="{i}" x="{gx:g}" y="{gy:g}" width="{gw:g}" height="{gh:g}" preserveAspectRatio="none" href="{f}"/>'
            for i, f in zip(ids, frames)) + "</defs>")

        def cuts(name, windows, length, start=None):
            """Keyframes that show an element only inside the given windows (seconds), with hard cuts."""
            stops = ["0%{opacity:0}"]
            for a, b in windows:
                stops += [f"{100 * a / length:.3f}%{{opacity:1}}", f"{100 * b / length:.3f}%{{opacity:0}}"]
            css.append(f"@keyframes {name}{{{''.join(stops)}100%{{opacity:0}}}}")
            if start is None:                                  # one pass, from page load
                return f"opacity:0;animation:{name} {length}s steps(1,end) forwards"
            return f"opacity:0;animation:{name} {length}s steps(1,end) {start}s infinite"

        burst = 3.0                                            # the clear photo holds until here
        seq = [(0.00, 0.08, 0), (0.13, 0.22, 1), (0.22, 0.27, 2), (0.33, 0.42, 0), (0.42, 0.50, 2), (0.50, 0.56, 1)]
        settle = burst + 0.56
        clean_off = [(burst + a, burst + b) for a, b, _ in seq]
        clean_gaps = [(t_in, burst)] + [(clean_off[i][1], clean_off[i + 1][0])
                                        for i in range(len(clean_off) - 1) if clean_off[i][1] < clean_off[i + 1][0]]
        css.append("@keyframes gin{from{opacity:0;transform:scale(1.03)}to{opacity:1;transform:none}}"
                   f".gin{{transform-origin:{gx + gw / 2:.0f}px {gy + gh / 2:.0f}px;"
                   f"animation:gin .6s cubic-bezier(.2,.7,.2,1) {t_in}s both}}")
        # with reduced motion, every animation is off: the clear photo shows and nothing else does
        layers = [f'<g class="gin"><use href="#gc" style="animation:gclean {settle}s steps(1,end) forwards"/></g>']
        stops = "".join(f"{100 * a / settle:.3f}%{{opacity:1}}{100 * b / settle:.3f}%{{opacity:0}}" for a, b in clean_gaps)
        css.append(f"@keyframes gclean{{0%{{opacity:0}}{stops}100%{{opacity:0}}}}")
        css.append(f"@keyframes grest{{0%{{opacity:0}}100%{{opacity:1}}}}")
        layers.append(f'<use href="#gr" style="opacity:0;animation:grest {settle}s steps(1,end) forwards"/>')
        twitch = [(0.00, 0.07, 0), (0.07, 0.13, 2), (0.20, 0.25, 1)]
        for k in range(len(gl["burst"])):
            once = [(burst + a, burst + b) for a, b, f in seq if f == k]
            layers.append(f'<use href="#gb{k}" style="{cuts(f"gb{k}", once, settle + 0.1)}"/>')
            again = [(a, b) for a, b, f in twitch if f == k]
            if again:
                layers.append(f'<use href="#gb{k}" style="{cuts(f"gt{k}", again, 6, settle + 4)}"/>')
        body.append('<g class="glitch">' + "".join(layers) + "</g>")

    # the photo: fades in sharp, then dissolves strip by strip as the scan line passes
    if photo:
        px, py, pw, ph = AX + photo["x"], AY + photo["y"], photo["w"], photo["h"]
        strips, parts = 24, []
        body.append(f'<defs><image id="ph" x="{px:g}" y="{py:g}" width="{pw:g}" height="{ph:g}" '
                    f'preserveAspectRatio="none" href="{photo["href"]}"/>')
        for i in range(strips):
            y = py + ph * i / strips
            body.append(f'<clipPath id="st{i}"><rect x="{px:g}" y="{y:.2f}" width="{pw:g}" '
                        f'height="{ph / strips + 0.6:.2f}"/></clipPath>')
            delay = t0 + sweep * (photo["y"] + ph * (i + 0.5) / strips) / art["h"] - 0.1
            parts.append(f'<use href="#ph" clip-path="url(#st{i})" class="st" style="animation-delay:{delay:.2f}s"/>')
        body.append("</defs>")
        body.append('<g class="ph">' + "".join(parts) + "</g>")

    # dot-matrix art: a scan line sweeps down and the dots settle into place behind it
    if art["dots"]:
        step, groups = 0.06, {}
        for cx, cy, r, colour in art["dots"]:
            jitter = ((int(cx * 10) * 73856093) ^ (int(cy * 10) * 19349663)) % 1000 / 1000
            delay = t0 + sweep * cy / art["h"] + 0.3 * jitter
            groups.setdefault(round(delay / step), []).append((cx + AX, cy + AY, r, colour))
        for g in sorted(groups):
            by_colour = {}                                # one fill per colour keeps the file small
            for cx, cy, r, colour in groups[g]:
                by_colour.setdefault(colour, []).append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}"/>')
            body.append(f'<g class="dg" style="animation-delay:{g * step:.2f}s">' + "".join(
                (f'<g fill="{c}">' + "".join(dots) + "</g>") if len(dots) > 1 else dots[0].replace("/>", f' fill="{c}"/>')
                for c, dots in by_colour.items()) + "</g>")
        for cls in ("scan", "scan2"):                             # once on load, then a faint pass every 10s
            body.append(f'<g class="{cls}"><rect x="{AX}" y="{AY - 16}" width="{art["w"]}" height="16" '
                        f'fill="url(#glow)"/><rect x="{AX}" y="{AY}" width="{art["w"]}" height="1.5" '
                        'fill="#c4b5fd"/></g>')

    # info column, centred on the art
    ix, dy = AX + art["w"] + 34, max(0, (art["h"] - 250) / 2)
    head = text(ix, 114 + dy, CFG["name"], t["ink"], 26, 700)
    for i, line in enumerate(CFG["headline"]):
        head += text(ix, 137 + dy + i * 17, line, t["muted"], 12.5)
    rule = 137 + dy + len(CFG["headline"]) * 17 - 4.5
    head += f'<line x1="{ix}" y1="{rule}" x2="{W - 28}" y2="{rule}" stroke="{t["border"]}"/>'
    body.append(f'<g class="row" style="animation-delay:1.1s">{head}</g>')
    for i, (key, value) in enumerate(CFG["hero_rows"]):
        y = rule + 25.5 + i * 23
        body.append(f'<g class="row" style="animation-delay:{1.25 + i * 0.09:.2f}s">'
                    + text(ix, y, key, t["accent"], 13, 700)
                    + text(ix + 92, y, value.format(**fill), t["ink"], 13) + "</g>")

    # $ <cycling tagline>
    ty = H - 26
    lines = CFG["taglines"]
    seg, start = 5.0, 3.2                          # seconds per tagline, and when the loop begins
    total = seg * len(lines)
    body.append(text(28, ty, "$", t["accent"], 13, 700))
    vis = 100 / len(lines)
    css.append(f"@keyframes vis{{0%,{vis:.3f}%{{opacity:1}}{vis + 0.01:.3f}%,100%{{opacity:0}}}}")
    for i, line in enumerate(lines):
        n, width = len(line), len(line) * CW
        typed = min(1.6, n * 0.035)
        k1, k2, k3 = (100 * s / total for s in (typed, seg - 1.0, seg - 0.4))
        css.append(
            f"@keyframes t{i}{{0%{{transform:translateX(0)}}{k1:.3f}%,{k2:.3f}%{{transform:translateX({width:.1f}px)}}"
            f"{k3:.3f}%,100%{{transform:translateX(0)}}}}"
            f".tl{i}{{animation:vis {total}s linear {start + i * seg:.1f}s infinite}}"
            f".tl{i} .cv{{animation:t{i} {total}s steps({n}) {start + i * seg:.1f}s infinite}}")
        body.append(f'<g class="tl tl{i}">'
                    + text(tx, ty, line, t["ink"], 13, extra=f' textLength="{width:.1f}"')
                    + f'<g class="cv"><rect x="{tx:.1f}" y="{ty - 14}" width="{W}" height="20" fill="{t["bg"]}"/>'
                    f'<rect class="cur" x="{tx:.1f}" y="{ty - 12}" width="8" height="15" fill="{t["accent"]}"/></g></g>')

    body.append("</g>")
    body.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{t["border"]}"/>')
    css.append("@media (prefers-reduced-motion:reduce){*{animation:none!important}"
               ".tl0{opacity:1}.c0,.cv{display:none}}")
    label = f"Terminal showing neofetch output for {CFG['name']}: " + "; ".join(
        f"{k} {v.format(**fill)}" for k, v in CFG["hero_rows"])
    write("hero.svg", svg(W, H, "".join(body), label, "".join(css)))


# ---------------------------------------------------------------- stat tiles

def stats_card(d, mode):
    t = THEMES[mode]
    W, H = 480, 190
    cal = d["cal"]
    tiles = [(num(cal["total"]), "contributions (1y)"), (cal["longest"], "longest streak, days"),
             (cal["active"], "active days (1y)"), (d["user"]["public_repos"], "public repos"),
             (fills(d)["lc_solved"], "LeetCode solved"), (d["stars"], "stars earned")]
    body = [frame(W, H, t),
            text(24, 34, LOGIN, t["accent"], 13, 700),
            text(W - 24, 34, "at a glance", t["muted"], 11, anchor="end")]
    for i, (value, label) in enumerate(tiles):
        x, y = 24 + (i % 3) * 150, 84 + (i // 3) * 66
        body.append(text(x, y, value, t["ink"], 26, 700))
        body.append(text(x, y + 19, label, t["muted"], 11))
    label = "GitHub at a glance: " + ", ".join(f"{v} {l}" for v, l in tiles)
    write(f"stats-{mode}.svg", svg(W, H, "".join(body), label))


def langs_card(d, mode):
    t = THEMES[mode]
    ranked = sorted(d["langs"].items(), key=lambda kv: -kv[1])
    top, rest = ranked[:6], ranked[6:]
    if rest:
        top.append(("Other", sum(v for _, v in rest)))
    total = sum(v for _, v in top) or 1
    rows = math.ceil(len(top) / 2)
    W, H = 480, max(190, 86 + rows * 24)       # match the stats card beside it
    body = [frame(W, H, t),
            text(24, 34, "languages", t["ink"], 13, 700),
            text(W - 24, 34, "share of bytes, all repos", t["muted"], 11, anchor="end")]
    x, bar_w, gap = 24.0, W - 48, 2
    usable = bar_w - gap * (len(top) - 1)
    body.append(f'<clipPath id="bar"><rect x="24" y="48" width="{bar_w}" height="10" rx="5"/></clipPath><g clip-path="url(#bar)">')
    for name, size in top:
        w = usable * size / total
        body.append(f'<rect x="{x:.1f}" y="48" width="{w:.1f}" height="10" fill="{LANG_COLOURS.get(name, OTHER_COLOUR)}"/>')
        x += w + gap
    body.append("</g>")
    for i, (name, size) in enumerate(top):
        cx, cy = 24 + (i % 2) * 222, 84 + (i // 2) * 24
        body.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{LANG_COLOURS.get(name, OTHER_COLOUR)}"/>')
        body.append(text(cx + 18, cy, name, t["ink"], 12))
        body.append(text(cx + 204, cy, f"{100 * size / total:.1f}%", t["muted"], 12, anchor="end"))
    label = "Languages by share of bytes: " + ", ".join(f"{n} {100 * s / total:.1f}%" for n, s in top)
    write(f"langs-{mode}.svg", svg(W, H, "".join(body), label))


# ---------------------------------------------------------------- LeetCode card

def leetcode_card(d, mode):
    """Solved counts come from data/profile.json (LeetCode has no public API to read them from);
    topic counts come from the folders of the solutions repo: <topic>/<difficulty>/<problem>."""
    t = THEMES[mode]
    lc, prof = d["lc"], d["leet"]
    if not lc["total"] and not prof:
        return
    names = CFG.get("topic_labels", {})
    top = sorted(lc["topics"].items(), key=lambda kv: (-kv[1], kv[0]))[:8]
    peak = top[0][1] if top else 1
    W, row = 840, 26
    H = 70 + max(len(top), 8) * row + 14
    note = f"topics counted from the {CFG['leetcode_repo']} repo"
    if prof.get("as_of"):
        as_of = dt.date.fromisoformat(prof["as_of"])
        when = f"{as_of.day} {as_of:%b %Y}"
        note = (f"live from LeetCode, updated {when}" if prof.get("live") else f"profile numbers as of {when}") + " · " + note
    facts = [("easy", prof.get("easy", lc["levels"].get("Easy", 0))),
             ("medium", prof.get("medium", lc["levels"].get("Medium", 0))),
             ("hard", prof.get("hard", lc["levels"].get("Hard", 0)))]
    if prof.get("max_streak_days"):
        facts.append(("max streak", f"{prof['max_streak_days']} days"))
    if prof.get("badges"):
        facts.append(("badges", prof["badges"]))
    solved = prof.get("solved", lc["total"])
    body = [frame(W, H, t),
            text(24, 34, "LeetCode", t["ink"], 13, 700),
            text(W - 24, 34, note, t["muted"], 11, anchor="end"),
            text(24, 116, num(solved), t["ink"], 44, 700),
            text(24, 138, "problems solved", t["muted"], 12)]
    for i, (label, value) in enumerate(facts):
        y = 174 + i * 24
        body.append(text(24, y, label, t["muted"], 12))
        body.append(text(190, y, value, t["ink"], 13, 700, anchor="end"))
    body.append(f'<line x1="214.5" y1="62" x2="214.5" y2="{H - 24}" stroke="{t["grid"]}"/>')
    body.append(text(256, 66, f"top {len(top)} of {len(lc['topics'])} topics, from the {lc['total']} C++ solutions "
                              "in the repo", t["muted"], 11))
    for i, (topic, count) in enumerate(top):
        y = 92 + i * row
        w = max(4.0, 330 * count / peak)
        body.append(text(256, y + 4, names.get(topic, topic), t["ink"], 12))
        body.append(f'<path d="M420,{y - 5}h{w - 4:.1f}a4,4 0 0 1 4,4v2a4,4 0 0 1 -4,4h-{w - 4:.1f}z" fill="{t["accent"]}"/>')
        body.append(text(420 + w + 8, y + 4, count, t["muted"], 11.5))
    label = (f"LeetCode: {solved} problems solved. " + ", ".join(f"{k} {v}" for k, v in facts)
             + f". Top topics among the {lc['total']} solutions in the repository: "
             + ", ".join(f"{names.get(k, k)} {v}" for k, v in top))
    write(f"leetcode-{mode}.svg", svg(W, H, "".join(body), label))


# ---------------------------------------------------------------- isometric calendar

def calendar_card(d, mode):
    t = THEMES[mode]
    cal = d["cal"]
    W, H = 840, 292
    ux, uy, vx, vy, s = 12.6, 1.7, -5.4, 6.6, 0.84   # week axis, day axis, cell size
    ox, oy = 104.0, 106.0
    days = [(dt.date.fromisoformat(date), count, level) for date, count, level in cal["days"]]
    first = days[0][0]
    first_sunday = first - dt.timedelta(days=(first.weekday() + 1) % 7)

    def p(w, dd, lift=0.0):
        return ox + w * ux + dd * vx, oy + w * uy + dd * vy - lift

    weeks = {}
    for date, count, level in days:
        weeks.setdefault((date - first_sunday).days // 7, []).append((date, count, level))

    css = ("@keyframes up{from{opacity:0;transform:translateY(8px)}}"
           ".w{animation:up .5s cubic-bezier(.2,.7,.2,1) backwards}"
           "@media (prefers-reduced-motion:reduce){.w{animation:none}}")
    body = [frame(W, H, t),
            text(24, 34, "contributions, last 12 months", t["ink"], 13, 700),
            text(W - 24, 34, f"{num(cal['total'])} total · longest streak {cal['longest']} days · "
                             f"busiest day {cal['best']}", t["muted"], 11, anchor="end")]
    prev_month = None
    for w in sorted(weeks):
        cells = []
        for date, count, level in sorted(weeks[w]):
            dd = (date.weekday() + 1) % 7
            h = 2 if not count else 5 + 42 * math.sqrt(count / cal["best"])
            colour = t["ramp"][level]
            a, b, c, e = p(w, dd), p(w + s, dd), p(w + s, dd + s), p(w, dd + s)
            a2, b2, c2, e2 = p(w, dd, h), p(w + s, dd, h), p(w + s, dd + s, h), p(w, dd + s, h)
            cells.append(f'<polygon points="{pts([b, c, c2, b2])}" fill="{shade(colour, 0.62)}"/>'
                         f'<polygon points="{pts([e, c, c2, e2])}" fill="{shade(colour, 0.8)}"/>'
                         f'<polygon points="{pts([a2, b2, c2, e2])}" fill="{colour}"/>')
        body.append(f'<g class="w" style="animation-delay:{w * 0.014:.3f}s">{"".join(cells)}</g>')
        month = min(weeks[w])[0].month
        if month != prev_month and w < max(weeks) - 1:
            lx, ly = p(w, 7.9)
            body.append(text(lx - 4, ly + 9, min(weeks[w])[0].strftime("%b"), t["muted"], 10))
        prev_month = month

    lx, ly = 24 + 32, H - 30
    body.append(text(lx - 8, ly + 9, "less", t["muted"], 10, anchor="end"))
    for i, colour in enumerate(t["ramp"]):
        body.append(f'<rect x="{lx + i * 14}" y="{ly}" width="10" height="10" rx="2" fill="{colour}"/>')
    body.append(text(lx + 5 * 14 + 4, ly + 9, "more", t["muted"], 10))
    label = (f"Contribution calendar: {cal['total']} contributions in the last year, "
             f"{cal['active']} active days, longest streak {cal['longest']} days")
    write(f"calendar-{mode}.svg", svg(W, H, "".join(body), label, css))


# ---------------------------------------------------------------- project cards

def project_cards(d, mode):
    """Animated cards, drawn by scripts/project_cards.py. A project may have no repo (for example a
    hackathon prototype); then its title, stack and optional url come from data/profile.json."""
    import project_cards as pc
    fill = fills(d)
    for k, proj in enumerate(CFG["projects"]):
        repo = d["repos"].get(proj.get("repo") or "")
        if proj.get("repo") and not repo:
            print("skipping unknown repo", proj["repo"])
            continue
        card = dict(title=proj.get("title") or proj["repo"], badge=proj.get("badge", "").format(**fill),
                    about=proj["about"], stack=proj.get("stack") or (repo or {}).get("language") or "",
                    stars=(repo or {}).get("stargazers_count", 0), accent=proj["accent"], visual=proj["visual"],
                    caption=proj.get("caption", "").format(**fill),
                    link="repo" if repo else ("open" if proj.get("url") else ""))
        write(f"card-{card_slug(proj)}-{mode}.svg", pc.render(card, mode, phase=k * 1.1))


def card_slug(proj):
    return proj.get("repo") or proj["slug"]


# ---------------------------------------------------------------- README sections
# The skills and project blocks of README.md are generated from data/profile.json, between
# <!-- name:start --> and <!-- name:end --> markers. Everything else in the README is hand-written.

ICONS = {   # 24x24 line icons for skills that have no brand logo
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
                '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "arrows": '<path d="M4 8h15l-4-4M20 16H5l4 4"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12.5l9 5 9-5"/><path d="M3 17l9 5 9-5"/>',
    "shield": '<path d="M12 2.5l8 3v6.5c0 5-3.5 8.3-8 9.5-4.5-1.2-8-4.5-8-9.5V5.5z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="11" rx="2"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/>',
    "tree": '<circle cx="12" cy="4.5" r="2.5"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>'
            '<path d="M10.8 6.7L6.7 16.3M13.2 6.7l4.1 9.6"/>',
    "cube": '<path d="M12 2.5l8.5 4.75v9.5L12 21.5l-8.5-4.75v-9.5z"/><path d="M3.5 7.25L12 12l8.5-4.75M12 12v9.5"/>',
    "stack": '<rect x="3" y="3" width="18" height="4.5" rx="1.2"/><rect x="3" y="9.75" width="18" height="4.5" rx="1.2"/>'
             '<rect x="3" y="16.5" width="18" height="4.5" rx="1.2"/>',
    "code": '<path d="M8.5 6L2.5 12l6 6M15.5 6l6 6-6 6"/>',
}


def badge_url(name, logo, color):
    label = urllib.parse.quote(name.replace("-", "--").replace("_", "__"), safe="")
    url = f"https://img.shields.io/badge/{label}-161b22?style=for-the-badge"
    if logo.startswith("icon:"):
        icon = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#{color}" '
                f'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">{ICONS[logo[5:]]}</svg>')
        data = "data:image/svg+xml;base64," + b64encode(icon.encode()).decode()
        return url + "&logo=" + urllib.parse.quote(data, safe="")
    return url + f"&logo={logo}&logoColor={color}"


def skills_block():
    rows = []
    for group in CFG["skills"]:
        cells = "\n".join(f'<a href="{escape(it["url"], quote=True)}"><img src="{escape(badge_url(it["name"], it["logo"], it["color"]), quote=True)}" '
                          f'alt="{escape(it["name"], quote=True)}" height="28"></a>' for it in group["items"])
        rows.append(f'<tr>\n<td><b>{escape(group["group"])}</b></td>\n<td>\n{cells}\n</td>\n</tr>')
    return "<table>\n" + "\n".join(rows) + "\n</table>"


def projects_block():
    # GitHub hides a link whose address ends in #gh-dark-mode-only or #gh-light-mode-only when the viewer's
    # theme does not match, so each card is two links straight to the repo, one per theme. (A <picture>
    # inside a link does not work here: GitHub re-links the image to the raw file.)
    lines = ['<div align="center">']
    for proj in CFG["projects"]:
        slug = card_slug(proj)
        # a repo links to itself; a project without one links to its "url", or back to this section until it has one
        url = proj.get("url") or (f"https://github.com/{LOGIN}/{proj['repo']}" if proj.get("repo") else "#featured-projects")
        alt = escape(f"{proj.get('title') or proj['repo']}: {proj['about']}", quote=True)
        lines.append("".join(f'<a href="{url}#gh-{mode}-mode-only"><img src="assets/card-{slug}-{mode}.svg" '
                             f'width="49%" alt="{alt}"></a>' for mode in ("dark", "light")))
    lines.append("</div>")
    return "\n".join(lines)


def update_readme():
    path = ROOT / "README.md"
    readme = original = path.read_text(encoding="utf-8")
    for name, block in (("skills", skills_block()), ("projects", projects_block())):
        start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
        if start in readme and end in readme:
            a, b = readme.index(start) + len(start), readme.index(end)
            readme = readme[:a] + "\n\n" + block + "\n\n" + readme[b:]
    if readme != original:
        path.write_text(readme, encoding="utf-8", newline="\n")
        print("README.md sections updated")


# ---------------------------------------------------------------- main

def main():
    ASSETS.mkdir(exist_ok=True)
    d = load()
    hero(d)
    for mode in THEMES:
        stats_card(d, mode)
        langs_card(d, mode)
        leetcode_card(d, mode)
        calendar_card(d, mode)
        project_cards(d, mode)
    update_readme()
    cal, lc = d["cal"], d["lc"]
    print(f"contributions={cal['total']} active={cal['active']} longest={cal['longest']} current={cal['current']} "
          f"best={cal['best']} stars={d['stars']} leetcode={lc['total']} levels={lc['levels']}")
    leet = d["leet"]
    print(f"leetcode profile ({'live' if leet.get('live') else 'saved'}): solved={leet.get('solved')} "
          f"easy={leet.get('easy')} medium={leet.get('medium')} hard={leet.get('hard')} "
          f"max_streak={leet.get('max_streak_days')} badges={leet.get('badges')}")
    print("topics:", sorted(lc["topics"].items(), key=lambda kv: -kv[1]))
    print("langs:", sorted(d["langs"].items(), key=lambda kv: -kv[1]))


if __name__ == "__main__":
    main()
