#!/usr/bin/env python3
"""
Smart Metering Weekly Intelligence Brief
Calls Claude API with web search, generates HTML dashboard for GitHub Pages.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic

# ---------------------------------------------------------------------------
# PROMPT
# ---------------------------------------------------------------------------

BRIEF_PROMPT = """
You are a smart metering industry analyst. Today is {date}.

Produce a weekly intelligence brief for the GM of Engineering at a smart metering
company in New Zealand and Australia. The business handles meter installation,
asset ownership, and data services for electricity and gas AMI meters, serving
energy retailers, distribution companies, and end consumers.

Use web search to find developments from the past 7-10 days. Run multiple targeted
searches across each topic area below before writing your response.

TOPIC AREAS

[NZ & AU — REGULATORY & POLICY]  HIGH PRIORITY
Search: "NZ electricity metering regulation 2025", "New Zealand Commerce Commission AMI",
"AEMO smart metering policy 2025", "Australian Energy Regulator metering rules",
"NZ Electricity Authority metering", "Australia AMI mandate"
Focus: rule changes, consultations, decisions, AMI mandates, pricing rule updates

[NZ & AU — TECHNOLOGY ADOPTION]  HIGH PRIORITY
Search: "smart meter rollout New Zealand 2025", "AMI deployment Australia 2025",
"DNSP metering technology", "advanced metering infrastructure Australia NZ",
"NZ electricity retailer smart meter deployment"
Focus: what is being deployed, by whom, at what scale

[NZ & AU — MARKET MOVES]  LOWER PRIORITY
Search: "smart metering companies New Zealand 2025", "metering services Australia contract",
"AMI operator NZ AU acquisition"
Focus: contracts won, new entrants, partnerships, M&A

[INTERNATIONAL — PRODUCTS & SERVICES]
Search: "smart metering new products 2025", "advanced metering infrastructure launch",
"smart meter manufacturer announcement 2025", "utility metering platform new"
Focus: new hardware, software platforms, data services being brought to market

[INTERNATIONAL — FLEX & DEMAND RESPONSE]
Search: "smart meter demand flexibility 2025", "virtual power plant metering",
"demand response smart meter program", "flexibility market metering platform"
Focus: how metering data and infrastructure is enabling flex products and programs

[INTERNATIONAL — RENEWABLES & EV]
Search: "smart metering solar integration 2025", "EV charging smart meter",
"behind-the-meter metering renewables", "electric vehicle metering integration 2025"
Focus: products and use cases at the intersection of metering, renewables, and EVs

[INTERNATIONAL — DATA INSIGHTS & ANALYTICS]
Search: "smart meter data analytics products 2025", "metering data services utility",
"energy data platform smart meter insights", "meter data management analytics"
Focus: what data products and insight services are emerging from metering infrastructure

OUTPUT FORMAT — follow this exactly

## EXEC SUMMARY
- [bullet]
- [bullet]
- [bullet]
3-5 bullets max. The so what — most significant signals this week. Be specific.
If something matters for a NZ/AU AMI operator, say why.

---

## NZ & AU — REGULATORY & POLICY

**[Headline]** — One sentence summary. [Source Name](URL)

repeat for each item found

---

## NZ & AU — TECHNOLOGY ADOPTION

**[Headline]** — One sentence summary. [Source Name](URL)

---

## NZ & AU — MARKET MOVES

**[Headline]** — One sentence summary. [Source Name](URL)

---

## INTERNATIONAL — PRODUCTS & SERVICES

**[Headline]** — One sentence summary. [Source Name](URL)

---

## INTERNATIONAL — FLEX & DEMAND RESPONSE

**[Headline]** — One sentence summary. [Source Name](URL)

---

## INTERNATIONAL — RENEWABLES & EV

**[Headline]** — One sentence summary. [Source Name](URL)

---

## INTERNATIONAL — DATA INSIGHTS

**[Headline]** — One sentence summary. [Source Name](URL)

---

Rules:
- If a section has nothing relevant from the past 7-10 days, write: Nothing significant this week.
- Keep each item tight: headline + one sentence + link. No padding or filler.
- Do not invent or hallucinate sources. Only include items you found via search.
"""

# ---------------------------------------------------------------------------
# API CALL
# ---------------------------------------------------------------------------

def get_weekly_brief() -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%A %d %B %Y")
    prompt = BRIEF_PROMPT.format(date=today)

    print("Calling Claude API with web search...")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [
        block.text
        for block in response.content
        if hasattr(block, "text") and block.type == "text"
    ]
    return "\n".join(text_parts)

# ---------------------------------------------------------------------------
# PARSING
# ---------------------------------------------------------------------------

def parse_brief(text: str) -> dict:
    sections = {}
    current_section = None
    current_lines = []

    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped[3:].strip()
            current_lines = []
        elif stripped == "---":
            continue
        else:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections


def convert_links(text: str) -> str:
    return re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2" target="_blank" rel="noopener">\1</a>',
        text,
    )


def render_exec_summary(text: str) -> str:
    bullets = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            content = convert_links(stripped[2:])
            bullets.append(f"<li>{content}</li>")
    if not bullets:
        return "<p class='nothing'>Nothing significant this week.</p>"
    return "<ul>" + "".join(bullets) + "</ul>"


def render_feed_section(text: str) -> str:
    if not text or "nothing significant" in text.lower():
        return "<p class='nothing'>Nothing significant this week.</p>"

    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("**"):
            match = re.match(r"\*\*(.+?)\*\*\s*[—–-]?\s*(.*)", stripped)
            if match:
                headline = match.group(1)
                rest = convert_links(match.group(2))
                items.append(
                    f'<div class="feed-item">'
                    f'<span class="feed-headline">{headline}</span>'
                    f'{"<span class=feed-sep>—</span><span class=feed-body>" + rest + "</span>" if rest else ""}'
                    f'</div>'
                )

    return "\n".join(items) if items else "<p class='nothing'>Nothing significant this week.</p>"

# ---------------------------------------------------------------------------
# HTML TEMPLATE
# ---------------------------------------------------------------------------

SECTION_META = [
    ("EXEC SUMMARY",                        "exec", "📋", ""),
    ("NZ & AU — REGULATORY & POLICY",       "feed", "⚖️",  "NZ & AU"),
    ("NZ & AU — TECHNOLOGY ADOPTION",       "feed", "📡",  "NZ & AU"),
    ("NZ & AU — MARKET MOVES",              "feed", "🤝",  "NZ & AU"),
    ("INTERNATIONAL — PRODUCTS & SERVICES", "feed", "🌐",  "International"),
    ("INTERNATIONAL — FLEX & DEMAND RESPONSE","feed","⚡", "International"),
    ("INTERNATIONAL — RENEWABLES & EV",     "feed", "☀️",  "International"),
    ("INTERNATIONAL — DATA INSIGHTS",       "feed", "📊",  "International"),
]


def build_html(sections: dict, date_str: str, archive_links: list) -> str:
    section_html = ""
    last_group = None

    for title, kind, icon, group in SECTION_META:
        content_raw = sections.get(title, "")

        if group and group != last_group:
            group_label = "🇳🇿 🇦🇺 &nbsp;NZ &amp; AU" if group == "NZ & AU" else "🌍 &nbsp;International"
            section_html += f'<div class="group-divider">{group_label}</div>\n'
            last_group = group

        if kind == "exec":
            body = render_exec_summary(content_raw)
            section_html += f'<div class="exec-card"><div class="exec-title">{icon} Executive Summary</div><div class="exec-body">{body}</div></div>\n'
        else:
            short_title = title.split(" — ", 1)[-1]
            body = render_feed_section(content_raw)
            section_html += f'<div class="section-card"><div class="section-title">{icon} {short_title}</div><div class="section-body">{body}</div></div>\n'

    archive_html = ""
    if archive_links:
        links = "".join(
            f'<a href="{l["url"]}">{l["label"]}</a>'
            for l in archive_links[-8:][::-1]
        )
        archive_html = f'<div class="archive-bar"><span>📁 Previous briefs:</span>{links}</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Smart Metering Weekly Brief — {date_str}</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;color:#1a1a2e;min-height:100vh}}
.header{{background:linear-gradient(135deg,#0d1b2a 0%,#1a3a5c 100%);padding:28px 32px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;border-bottom:3px solid #00a8e8}}
.header-left h1{{color:#fff;font-size:22px;font-weight:700;letter-spacing:-0.3px}}
.header-left h1 span{{color:#00a8e8}}
.header-left p{{color:#7a9ab5;font-size:13px;margin-top:4px}}
.header-badge{{background:rgba(0,168,232,0.15);border:1px solid rgba(0,168,232,0.4);color:#00a8e8;font-size:12px;padding:5px 12px;border-radius:20px;white-space:nowrap}}
.archive-bar{{background:#1a3a5c;padding:8px 32px;font-size:12px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;color:#7a9ab5}}
.archive-bar a{{color:#7a9ab5;text-decoration:none;padding:2px 8px;border-radius:4px;transition:all 0.15s}}
.archive-bar a:hover{{background:rgba(0,168,232,0.15);color:#00a8e8}}
.content{{max-width:820px;margin:0 auto;padding:28px 20px 60px}}
.group-divider{{font-size:11px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#7a9ab5;padding:24px 0 8px;border-bottom:1px solid #dde3ec;margin-bottom:16px}}
.exec-card{{background:#0d1b2a;border-radius:10px;padding:24px 28px;margin-bottom:24px;border-left:4px solid #00a8e8}}
.exec-title{{color:#00a8e8;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px}}
.exec-body ul{{list-style:none;display:flex;flex-direction:column;gap:10px}}
.exec-body li{{color:#e8edf2;font-size:14.5px;line-height:1.65;padding-left:20px;position:relative}}
.exec-body li::before{{content:"→";color:#00a8e8;position:absolute;left:0;font-weight:700}}
.exec-body a{{color:#5bc4f5;text-decoration:none}}
.exec-body a:hover{{text-decoration:underline}}
.section-card{{background:#fff;border-radius:8px;padding:18px 22px;margin-bottom:12px;border:1px solid #dde3ec;box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
.section-title{{font-size:12px;font-weight:700;letter-spacing:0.8px;text-transform:uppercase;color:#0d1b2a;margin-bottom:14px;padding-bottom:10px;border-bottom:1px solid #eef0f4}}
.feed-item{{padding:10px 0;border-bottom:1px solid #f2f4f7;font-size:13.5px;line-height:1.6;display:flex;flex-wrap:wrap;gap:4px;align-items:baseline}}
.feed-item:last-child{{border-bottom:none;padding-bottom:0}}
.feed-headline{{font-weight:600;color:#0d1b2a}}
.feed-sep{{color:#aab;margin:0 4px}}
.feed-body{{color:#444}}
.feed-body a{{color:#00a8e8;text-decoration:none;font-weight:500}}
.feed-body a:hover{{text-decoration:underline}}
.nothing{{color:#aab;font-style:italic;font-size:13px}}
.footer{{text-align:center;font-size:11px;color:#aab;padding:20px;border-top:1px solid #dde3ec;margin-top:40px}}
.footer a{{color:#aab}}
@media(max-width:600px){{.header{{padding:20px}}.content{{padding:16px 12px 40px}}.exec-card{{padding:18px}}.section-card{{padding:14px 16px}}}}
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <h1>⚡ Smart Metering <span>Intelligence</span></h1>
    <p>Weekly Brief &nbsp;·&nbsp; {date_str} &nbsp;·&nbsp; NZ &amp; AU + International</p>
  </div>
  <div class="header-badge">🤖 Claude + Web Search</div>
</div>
{archive_html}
<div class="content">
{section_html}
</div>
<div class="footer">
  Auto-generated every Monday · Claude Sonnet + Web Search ·
  <a href="https://trent-bluecurrent.github.io/smart-metering-brief">trent-bluecurrent.github.io/smart-metering-brief</a>
</div>
</body>
</html>"""

# ---------------------------------------------------------------------------
# ARCHIVE
# ---------------------------------------------------------------------------

ARCHIVE_FILE = Path("archive/index.json")

def load_archive() -> list:
    if ARCHIVE_FILE.exists():
        return json.loads(ARCHIVE_FILE.read_text())
    return []

def save_archive(entries: list):
    ARCHIVE_FILE.parent.mkdir(exist_ok=True)
    ARCHIVE_FILE.write_text(json.dumps(entries, indent=2))

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set")

    now = datetime.now()
    date_str = now.strftime("%d %B %Y")
    date_slug = now.strftime("%Y-%m-%d")

    print(f"Generating brief for {date_str}...")
    brief_text = get_weekly_brief()

    print("Parsing and rendering HTML...")
    sections = parse_brief(brief_text)

    archive = load_archive()
    archive_filename = f"archive/{date_slug}.html"
    archive.append({"label": date_str, "url": archive_filename, "slug": date_slug})
    save_archive(archive)

    html = build_html(sections, date_str, archive)

    Path("index.html").write_text(html, encoding="utf-8")
    print("✓ index.html written")

    Path(archive_filename).write_text(html, encoding="utf-8")
    print(f"✓ {archive_filename} written")

if __name__ == "__main__":
    main()
