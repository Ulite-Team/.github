#!/usr/bin/env python3
"""
Ulite org README generator.

Pulls live repo data from the GitHub API for a given org and renders
branded SVG cards (per repo) plus a summary banner, then rewrites the
auto-generated block inside README.md between the PROJECTS markers.

Usage:
    GITHUB_TOKEN=xxx python scripts/generate_cards.py
    python scripts/generate_cards.py --org ulite-team --sample   # offline preview

Environment:
    GITHUB_TOKEN   - required for live mode (GitHub Actions provides this
                     automatically as ${{ secrets.GITHUB_TOKEN }})
    ORG_NAME       - defaults to "ulite-team"
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Brand tokens — keep in sync with the Ulite brand guide
# ---------------------------------------------------------------------------
DARK = "#14141F"
SURFACE = "#1C1C2E"
SURFACE_2 = "#24243A"
BLUE = "#8EA3F5"
BLUE_DEEP = "#3D4FBF"
MINT = "#5EE6A0"
WHITE = "#F4F5FA"
MUTED = "#8892B0"

LANG_COLORS = {
    "Kotlin": "#A97BFF",
    "Rust": "#DEA584",
    "Swift": "#F05138",
    "Python": "#3572A5",
    "JavaScript": "#F1E05A",
    "TypeScript": "#3178C6",
    "Java": "#B07219",
    "C++": "#F34B7D",
    "Shell": "#89E051",
    "HTML": "#E44D26",
    "CSS": "#563D7C",
    "Dart": "#00B4AB",
}
DEFAULT_LANG_COLOR = MUTED

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CARDS_DIR = os.path.join(ROOT, "assets", "generated", "cards")
BANNER_PATH = os.path.join(ROOT, "assets", "generated", "banner.svg")
README_PATH = os.path.join(ROOT, "profile", "README.md")

MARK_START = "<!-- PROJECTS:START -->"
MARK_END = "<!-- PROJECTS:END -->"


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------
def fetch_repos(org: str, token: str | None):
    url = f"https://api.github.com/orgs/{org}/repos?per_page=100&sort=pushed&type=public"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "ulite-readme-generator")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.stderr.write(f"GitHub API error {e.code}: {e.read().decode()[:300]}\n")
        sys.exit(1)
    except urllib.error.URLError as e:
        sys.stderr.write(f"Network error reaching GitHub API: {e}\n")
        sys.exit(1)

    repos = [r for r in data if not r.get("fork") and not r.get("archived")]
    return repos


def sample_repos():
    """Offline preview data — used with --sample so the layout can be
    inspected without hitting the network."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "name": "***REMOVED***",
            "description": "***REMOVED*** KMP ***REMOVED*** platform for schools and learning centers.",
            "html_url": "https://github.com/ulite-team/***REMOVED***",
            "language": "Kotlin",
            "stargazers_count": 42,
            "forks_count": 6,
            "pushed_at": now,
            "fork": False,
            "archived": False,
        },
        {
            "name": "***REMOVED***",
            "description": "Rust build automation engine with a ratatui TUI for ***REMOVED*** Android/KMP client builds.",
            "html_url": "https://github.com/ulite-team/***REMOVED***",
            "language": "Rust",
            "stargazers_count": 118,
            "forks_count": 14,
            "pushed_at": now,
            "fork": False,
            "archived": False,
        },
        {
            "name": "***REMOVED***",
            "description": "Rust-based Kotlin LSP — fast, low-memory language server for Kotlin/KMP projects.",
            "html_url": "https://github.com/ulite-team/***REMOVED***",
            "language": "Rust",
            "stargazers_count": 340,
            "forks_count": 27,
            "pushed_at": now,
            "fork": False,
            "archived": False,
        },
        {
            "name": "***REMOVED***",
            "description": "Notes app with a Jetpack Compose UI and a Rust/JNI backend.",
            "html_url": "https://github.com/ulite-team/***REMOVED***",
            "language": "Kotlin",
            "stargazers_count": 19,
            "forks_count": 2,
            "pushed_at": now,
            "fork": False,
            "archived": False,
        },
    ]


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def truncate(s: str, n: int) -> str:
    s = s or "No description yet."
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def relative_time(iso_ts: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except Exception:
        return ""
    delta = datetime.now(timezone.utc) - dt
    days = delta.days
    if days < 1:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def smile_mark(stroke: str, x: float, y: float, w: float, h: float) -> str:
    return (
        f'<path d="M {x + w*0.2:.1f} {y + h*0.42:.1f} '
        f'Q {x + w*0.5:.1f} {y + h*0.62:.1f} {x + w*0.8:.1f} {y + h*0.42:.1f}" '
        f'stroke="{stroke}" stroke-width="{w*0.07:.1f}" fill="none" stroke-linecap="round"/>'
        f'<circle cx="{x + w*0.24:.1f}" cy="{y + h*0.30:.1f}" r="{w*0.045:.1f}" fill="{stroke}"/>'
        f'<circle cx="{x + w*0.76:.1f}" cy="{y + h*0.30:.1f}" r="{w*0.045:.1f}" fill="{stroke}"/>'
    )


def render_card(repo: dict) -> str:
    name = esc(repo["name"])
    desc = esc(truncate(repo.get("description"), 78))
    lang = repo.get("language") or "—"
    lang_color = LANG_COLORS.get(lang, DEFAULT_LANG_COLOR)
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    updated = relative_time(repo.get("pushed_at", ""))

    W, H = 440, 160
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="g-{name}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{SURFACE_2}"/>
      <stop offset="1" stop-color="{SURFACE}"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="16" fill="url(#g-{name})" stroke="#2A2A40" stroke-width="1"/>
  <g>{smile_mark(BLUE, 20, 20, 30, 30)}</g>
  <text x="62" y="42" font-family="Verdana, Arial, sans-serif" font-size="17" font-weight="700" fill="{WHITE}">{name}</text>
  <text x="24" y="76" font-family="Arial, sans-serif" font-size="12.5" fill="{MUTED}">
    <tspan x="24" dy="0">{desc}</tspan>
  </text>
  <circle cx="26" cy="130" r="5" fill="{lang_color}"/>
  <text x="38" y="134" font-family="Arial, sans-serif" font-size="11.5" fill="{WHITE}">{esc(lang)}</text>
  <text x="130" y="134" font-family="Arial, sans-serif" font-size="11.5" fill="{MUTED}">★ {stars}</text>
  <text x="190" y="134" font-family="Arial, sans-serif" font-size="11.5" fill="{MUTED}">⑂ {forks}</text>
  <text x="{W-16}" y="134" text-anchor="end" font-family="'JetBrains Mono', monospace" font-size="10.5" fill="{MINT}">updated {esc(updated)}</text>
</svg>"""
    return svg


def render_banner(org: str, repos: list) -> str:
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_repos = len(repos)
    W, H = 1200, 300
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <radialGradient id="glow" cx="50%" cy="35%" r="65%">
      <stop offset="0" stop-color="{BLUE}" stop-opacity="0.16"/>
      <stop offset="1" stop-color="{DARK}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="{DARK}"/>
  <rect width="{W}" height="{H}" fill="url(#glow)"/>
  <g>{smile_mark(BLUE, W/2 - 55, 46, 110, 110)}</g>
  <text x="{W/2}" y="205" text-anchor="middle" font-family="Verdana, Arial, sans-serif" font-size="46" font-weight="800" fill="{BLUE}" letter-spacing="1">{esc(org)}</text>
  <text x="{W/2}" y="235" text-anchor="middle" font-family="Arial, sans-serif" font-size="15" fill="{MUTED}">Building ***REMOVED*** KMP, Rust tooling, and developer infrastructure</text>
  <text x="{W/2 - 90}" y="272" text-anchor="middle" font-family="'JetBrains Mono', monospace" font-size="12" fill="{MINT}">{total_repos} public repos</text>
  <text x="{W/2 + 90}" y="272" text-anchor="middle" font-family="'JetBrains Mono', monospace" font-size="12" fill="{MINT}">★ {total_stars} total stars</text>
</svg>"""
    return svg


def render_projects_table(repos: list, org: str) -> str:
    rows = []
    for r in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True):
        name = r["name"]
        lang = r.get("language") or "—"
        stars = r.get("stargazers_count", 0)
        url = r.get("html_url", f"https://github.com/{org}/{name}")
        card_rel = f"assets/generated/cards/{name}.svg"
        rows.append(
            f'<a href="{url}"><img src="{card_rel}" alt="{esc(name)}" width="440"/></a>'
        )
    # 2 per row grid using a simple HTML table so it renders on GitHub
    cells = []
    for i in range(0, len(rows), 2):
        pair = rows[i : i + 2]
        cells.append("<tr>" + "".join(f"<td>{c}</td>" for c in pair) + "</tr>")
    table = "<table>\n" + "\n".join(cells) + "\n</table>"
    return table


# ---------------------------------------------------------------------------
# README injection
# ---------------------------------------------------------------------------
def update_readme(projects_block: str):
    if not os.path.exists(README_PATH):
        sys.stderr.write(f"README not found at {README_PATH}, skipping injection.\n")
        return
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if MARK_START not in content or MARK_END not in content:
        sys.stderr.write("PROJECTS markers not found in README.md, skipping injection.\n")
        return

    pre = content.split(MARK_START)[0]
    post = content.split(MARK_END)[1]
    new_content = f"{pre}{MARK_START}\n{projects_block}\n{MARK_END}{post}"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--org", default=os.environ.get("ORG_NAME", "ulite-team"))
    parser.add_argument("--sample", action="store_true", help="use offline sample data")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")

    if args.sample:
        repos = sample_repos()
    else:
        repos = fetch_repos(args.org, token)

    os.makedirs(CARDS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(BANNER_PATH), exist_ok=True)

    for repo in repos:
        svg = render_card(repo)
        out_path = os.path.join(CARDS_DIR, f"{repo['name']}.svg")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg)

    with open(BANNER_PATH, "w", encoding="utf-8") as f:
        f.write(render_banner(args.org, repos))

    table = render_projects_table(repos, args.org)
    update_readme(table)

    print(f"Generated {len(repos)} project card(s), 1 banner, and updated README.md")


if __name__ == "__main__":
    main()
