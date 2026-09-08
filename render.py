"""Parse lark-doc-style markdown into a structured tree and render an HTML page with sticky sidebar TOC."""
import re
import json
from pathlib import Path

SRC = Path(r"C:\Users\lenovo\.workbuddy\draft_57d5f8c9_folder\clean.md")
DST = Path(r"C:\Users\lenovo\workbuddy\work\workbuddy-share\interactive.html")

text = SRC.read_text(encoding="utf-8")
lines = text.split("\n")

# Pull title (first line)
title = lines[0].strip()
body_lines = lines[2:]  # skip title and blank line

def slugify(s, used):
    base = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", s).strip("-").lower()
    if not base:
        base = "section"
    candidate = base
    n = 1
    while candidate in used:
        n += 1
        candidate = f"{base}-{n}"
    used.add(candidate)
    return candidate

# ---------- Block-level pass ----------
inline_tags = {
    "<b>": "<strong>", "</b>": "</strong>",
    "<em>": "<em>", "</em>": "</em>",
}

def inline(s):
    # Escape HTML
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restore allowable inline tags (we control them)
    s = s.replace("&lt;b&gt;", "<strong>").replace("&lt;/b&gt;", "</strong>")
    s = s.replace("&lt;em&gt;", "<em>").replace("&lt;/em&gt;", "</em>")
    s = s.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    # Inline code with backticks: `xxx`
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s

# State machine
out_blocks = []  # list of dicts: {"type": "h1"|"h2"|"h3"|"p"|"ul"|"ol"|"code"|"callout"|"hr"|"table", ...}
used_slugs = set()
i = 0
n = len(body_lines)
def empty_ahead(start):
    j = start
    while j < n and body_lines[j].strip() == "":
        j += 1
    return j

while i < n:
    line = body_lines[i]
    stripped = line.strip()
    if stripped == "":
        i += 1
        continue

    # Horizontal rule
    if stripped == "---":
        out_blocks.append({"type": "hr"})
        i += 1
        continue

    # Heading
    m = re.match(r"^(#{1,3})\s+(.+)$", stripped)
    if m:
        level = len(m.group(1))
        content = m.group(2).strip()
        slug = slugify(content, used_slugs)
        out_blocks.append({"type": f"h{level}", "text": content, "id": slug})
        i += 1
        continue

    # Code block
    if stripped.startswith("```"):
        lang = stripped[3:].strip()
        i += 1
        code_lines = []
        while i < n and not body_lines[i].strip().startswith("```"):
            code_lines.append(body_lines[i])
            i += 1
        i += 1  # skip closing ```
        out_blocks.append({"type": "code", "lang": lang, "content": "\n".join(code_lines).rstrip()})
        continue

    # Callout
    m = re.match(r"^<callout\s+emoji=\"([^\"]+)\">\s*$", stripped)
    if m:
        emoji = m.group(1)
        i += 1
        # Collect until "</callout>"
        buf = []
        while i < n and body_lines[i].strip() != "</callout>":
            buf.append(body_lines[i])
            i += 1
        i += 1  # skip closing
        callout_body = "\n".join(buf).strip()
        out_blocks.append({"type": "callout", "emoji": emoji, "body": callout_body})
        continue

    # Table: lines starting with |, header + divider + rows
    if stripped.startswith("|") and i + 1 < n and re.match(r"^\|?[\s:|-]+\|?\s*$", body_lines[i+1].strip()):
        header_cells = [c.strip() for c in stripped.strip("|").split("|")]
        i += 2  # skip header + divider
        rows = []
        while i < n and body_lines[i].strip().startswith("|"):
            row_cells = [c.strip() for c in body_lines[i].strip().strip("|").split("|")]
            rows.append(row_cells)
            i += 1
        out_blocks.append({"type": "table", "header": header_cells, "rows": rows})
        continue

    # Unordered list (possibly multi-line by continuation indent? we keep single-line items only)
    if re.match(r"^-\s+", stripped):
        items = []
        while i < n:
            ls = body_lines[i].strip()
            if re.match(r"^-\s+", ls):
                items.append(re.sub(r"^-\s+", "", ls))
                i += 1
            elif ls == "":
                break
            else:
                break
        out_blocks.append({"type": "ul", "items": items})
        continue

    # Ordered list
    if re.match(r"^\d+\.\s+", stripped):
        items = []
        while i < n:
            ls = body_lines[i].strip()
            if re.match(r"^\d+\.\s+", ls):
                items.append(re.sub(r"^\d+\.\s+", "", ls))
                i += 1
            elif ls == "":
                break
            else:
                break
        out_blocks.append({"type": "ol", "items": items})
        continue

    # Paragraph (collect consecutive non-blank, non-special lines)
    para_lines = [stripped]
    i += 1
    while i < n and body_lines[i].strip() != "" and not re.match(r"^(#{1,3}\s|---|```|<callout|-\s+|\d+\.\s+|\|)", body_lines[i].strip()):
        para_lines.append(body_lines[i].strip())
        i += 1
    out_blocks.append({"type": "p", "text": " ".join(para_lines)})

# ---------- Build TOC ----------
toc = []  # list of {level, text, id}
for b in out_blocks:
    if b["type"] in ("h1", "h2", "h3"):
        toc.append({"level": int(b["type"][1]), "text": b["text"], "id": b["id"]})

# ---------- Render blocks to HTML ----------
def render_blocks(blocks):
    html = []
    for b in blocks:
        t = b["type"]
        if t == "h1":
            html.append(f'<h1 id="{b["id"]}">{inline(b["text"])}</h1>')
        elif t == "h2":
            html.append(f'<h2 id="{b["id"]}">{inline(b["text"])}</h2>')
        elif t == "h3":
            html.append(f'<h3 id="{b["id"]}">{inline(b["text"])}</h3>')
        elif t == "p":
            html.append(f'<p>{inline(b["text"])}</p>')
        elif t == "ul":
            html.append("<ul>")
            for it in b["items"]:
                html.append(f'<li>{inline(it)}</li>')
            html.append("</ul>")
        elif t == "ol":
            html.append("<ol>")
            for it in b["items"]:
                html.append(f'<li>{inline(it)}</li>')
            html.append("</ol>")
        elif t == "code":
            lang = b["lang"] or "text"
            content = b["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            html.append(f'<pre class="lang-{lang}"><code>{content}</code></pre>')
        elif t == "callout":
            html.append(f'<div class="callout"><span class="emoji">{b["emoji"]}</span><div class="callout-body">{inline(b["body"])}</div></div>')
        elif t == "hr":
            html.append('<hr/>')
        elif t == "table":
            html.append('<div class="table-wrap"><table>')
            html.append("<thead><tr>")
            for c in b["header"]:
                html.append(f"<th>{inline(c)}</th>")
            html.append("</tr></thead><tbody>")
            for row in b["rows"]:
                html.append("<tr>")
                for c in row:
                    html.append(f"<td>{inline(c)}</td>")
                html.append("</tr>")
            html.append("</tbody></table></div>")
    return "\n".join(html)

# ---------- Build sidebar TOC HTML ----------
def render_toc():
    # 顶级 title 不进入 toc。前言不进；但 Part 1/2/3/4 进，h2/h3 缩进。
    rendered = []
    skip_first_h1 = True
    in_toc = False
    for entry in toc:
        if entry["level"] == 1:
            if skip_first_h1:
                skip_first_h1 = False
                continue
            rendered.append(f'<li><a href="#{entry["id"]}" data-target="{entry["id"]}"><span class="l1">{inline(entry["text"])}</span></a>')
            in_toc = True
        elif entry["level"] == 2 and in_toc:
            rendered.append(f'<ul><li><a href="#{entry["id"]}" data-target="{entry["id"]}"><span class="l2">{inline(entry["text"])}</span></a></li></ul>')
        elif entry["level"] == 3 and in_toc:
            # 简化：第三级只在视觉上略缩进，仍作为侧栏项
            rendered.append(f'<ul><ul><li><a href="#{entry["id"]}" data-target="{entry["id"]}"><span class="l3">{inline(entry["text"])}</span></a></li></ul></ul>')
    # close any open li
    return "\n".join(rendered)

# Render
content_html = render_blocks(out_blocks)
toc_html = render_toc()

DOC_TITLE = "把 AI 变成你的第二大脑"
DOC_SUB = "WorkBuddy 上手 · 个人知识库搭建 · Skill 定制"

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{DOC_TITLE}</title>
<meta name="description" content="个人经验整理：WorkBuddy 上手 + 个人知识库搭建 + Skill 定制。">
<style>
/* Reset */
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 32px; }}
body {{
  font-family: "Noto Serif SC", "Source Han Serif SC", "Songti SC", STSong, Georgia, serif;
  background: #f5f4ed;
  color: #141413;
  line-height: 1.75;
  -webkit-font-smoothing: antialiased;
}}

:root {{
  --parchment: #f5f4ed;
  --surface: #faf9f5;
  --brand: #1B365D;
  --brand-soft: #d8dde7;
  --near-black: #141413;
  --olive: #504e49;
  --stone: #6b6a64;
  --border: #e8e6dc;
  --warm-cream: #f0eee5;
}}

/* Layout */
.layout {{
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 48px;
  max-width: 1280px;
  margin: 0 auto;
  padding: 56px 40px 96px;
}}

/* Sidebar */
.sidebar {{
  position: sticky;
  top: 32px;
  align-self: start;
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;
}}

.brand {{
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 16px 24px 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}}

.brand-title {{
  font-family: "Noto Serif SC", Georgia, serif;
  font-size: 17px;
  font-weight: 600;
  color: var(--brand);
  letter-spacing: 0.02em;
  line-height: 1.4;
}}

.brand-sub {{
  font-size: 12.5px;
  color: var(--stone);
  letter-spacing: 0.02em;
}}

.toc-label {{
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--stone);
  padding: 12px 16px 8px;
}}

.toc {{
  list-style: none;
  font-size: 13.5px;
}}
.toc ul {{ list-style: none; padding-left: 0; }}
.toc ul ul {{ padding-left: 14px; }}
.toc li {{ margin: 2px 0; }}

.toc a {{
  display: block;
  padding: 6px 12px 6px 16px;
  color: var(--olive);
  text-decoration: none;
  border-left: 2px solid transparent;
  transition: color .15s, border-color .15s;
  line-height: 1.5;
}}
.toc a:hover {{
  color: var(--brand);
}}
.toc a.is-active {{
  color: var(--brand);
  border-left-color: var(--brand);
  font-weight: 500;
}}

.toc .l2 {{
  font-size: 13px;
}}
.toc .l3 {{
  font-size: 12.5px;
  color: var(--stone);
}}

/* Main */
.main {{ min-width: 0; }}

.cover {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 40px 44px;
  margin-bottom: 36px;
}}
.cover h1.doc-title {{
  font-family: "Noto Serif SC", Georgia, serif;
  font-size: 30px;
  font-weight: 600;
  color: var(--brand);
  line-height: 1.4;
  margin-bottom: 8px;
}}
.cover .doc-sub {{
  font-size: 15px;
  color: var(--stone);
  margin-bottom: 16px;
}}
.cover .doc-meta {{
  font-size: 13px;
  color: var(--stone);
  border-top: 1px solid var(--border);
  padding-top: 14px;
  margin-top: 12px;
}}

.content {{
  max-width: 760px;
  margin: 0 auto;
}}

.content h1 {{
  font-family: "Noto Serif SC", Georgia, serif;
  font-size: 26px;
  font-weight: 600;
  color: var(--brand);
  margin: 56px 0 18px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--brand);
  letter-spacing: 0.01em;
}}
.content h1:first-of-type {{ margin-top: 0; }}
.content h2 {{
  font-family: "Noto Serif SC", Georgia, serif;
  font-size: 20px;
  font-weight: 600;
  color: var(--near-black);
  margin: 36px 0 12px;
  padding-left: 12px;
  border-left: 3px solid var(--brand);
}}
.content h3 {{
  font-family: "Noto Sans SC", "PingFang SC", system-ui, sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: var(--olive);
  margin: 24px 0 10px;
}}

.content p {{ margin-bottom: 14px; }}
.content ul, .content ol {{ margin: 8px 0 14px 22px; }}
.content li {{ margin: 6px 0; }}

strong {{ color: var(--brand); font-weight: 600; }}
em {{ font-style: italic; color: var(--olive); }}

code {{
  font-family: "JetBrains Mono", "Consolas", "Source Code Pro", monospace;
  font-size: 13.5px;
  background: rgba(27, 54, 93, 0.07);
  color: var(--brand);
  padding: 1px 6px;
  border-radius: 3px;
}}

.content pre {{
  background: #1a1d24;
  color: #e6e3d8;
  border-radius: 6px;
  padding: 16px 20px;
  margin: 14px 0 20px;
  overflow-x: auto;
  font-family: "JetBrains Mono", "Consolas", "Source Code Pro", monospace;
  font-size: 13px;
  line-height: 1.65;
  border: 1px solid #2a2e36;
}}
.content pre code {{
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: inherit;
  border-radius: 0;
}}

hr {{
  border: 0;
  border-top: 1px dashed var(--border);
  margin: 36px 0;
}}

/* Callout */
.callout {{
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 14px;
  background: #f0eee5;
  border-left: 3px solid var(--brand);
  padding: 14px 18px;
  border-radius: 4px;
  margin: 16px 0 20px;
  font-size: 14.5px;
  color: var(--near-black);
}}
.callout .emoji {{ font-size: 18px; line-height: 1.55; }}
.callout-body p {{ margin: 0; }}
.callout-body p + p {{ margin-top: 8px; }}

/* Table */
.table-wrap {{ overflow-x: auto; margin: 12px 0 20px; }}
.content table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
}}
.content th, .content td {{
  padding: 9px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}}
.content th {{ background: var(--warm-cream); font-weight: 600; color: var(--olive); }}
.content tr:last-child td {{ border-bottom: 0; }}

/* Pager */
.pager {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 56px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}}
.pager a {{
  text-decoration: none;
  color: inherit;
  display: block;
}}
.pager .eyebrow {{
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--stone);
  margin-bottom: 4px;
}}
.pager .next {{ text-align: right; }}
.pager a:hover strong {{ color: var(--brand); }}

/* Mobile */
@media (max-width: 880px) {{
  .layout {{
    grid-template-columns: 1fr;
    padding: 24px 18px 80px;
    gap: 20px;
  }}
  .sidebar {{
    position: static;
    max-height: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 0 12px;
  }}
  .toc {{ display: flex; overflow-x: auto; gap: 4px; padding: 0 8px; scrollbar-width: none; }}
  .toc::-webkit-scrollbar {{ display: none; }}
  .toc ul {{ display: none; }}  /* mobile: only top-level */
  .toc > li, .toc {{
    display: inline-flex;
    flex-wrap: nowrap;
  }}
  .toc a {{
    white-space: nowrap;
    border-left: 0;
    border-bottom: 2px solid transparent;
    padding: 6px 12px;
  }}
  .toc a.is-active {{ border-bottom-color: var(--brand); }}
  .cover {{ padding: 24px 20px; }}
  .cover h1.doc-title {{ font-size: 22px; }}
  .pager {{ grid-template-columns: 1fr; gap: 12px; }}
  .pager .next {{ text-align: left; }}
}}

/* Back to top button */
#topBtn {{
  position: fixed;
  bottom: 28px;
  right: 28px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--brand);
  color: #fff;
  border: 0;
  cursor: pointer;
  font-size: 18px;
  opacity: 0;
  pointer-events: none;
  transition: opacity .25s, transform .25s;
  box-shadow: 0 4px 12px rgba(27,54,93,0.25);
  z-index: 30;
}}
#topBtn.show {{ opacity: 1; pointer-events: auto; }}
#topBtn:hover {{ transform: translateY(-2px); }}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar" aria-label="目录">
    <div class="brand">
      <div class="brand-title">静雯 · AI 学习笔记</div>
      <div class="brand-sub">WorkBuddy · 第二大脑 · Skill</div>
    </div>
    <div class="toc-label">本页内容</div>
    <ul class="toc" id="toc">
{toc_html}
    </ul>
  </aside>

  <main class="main">
    <div class="cover">
      <h1 class="doc-title">{DOC_TITLE}</h1>
      <div class="doc-sub">{DOC_SUB}</div>
      <div class="doc-meta">作者：吴静雯 · 2024 级大数据管理与应用 · 个人经验整理（请勿外传）</div>
    </div>

    <article class="content">
{content_html}
    </article>

    <div class="pager">
      <a class="prev" href="#前言">
        <div class="eyebrow">↑ 回到顶部</div>
        <strong>前言</strong>
      </a>
      <a class="next" href="#part-1-认识-workbuddy-入门篇">
        <div class="eyebrow">Next →</div>
        <strong>Part 1 · 认识 WorkBuddy</strong>
      </a>
    </div>
  </main>
</div>

<button id="topBtn" aria-label="回到顶部" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>

<script>
// Active TOC highlighting via IntersectionObserver
const tocLinks = document.querySelectorAll('#toc a');
const sections = [];
tocLinks.forEach(a => {{
  const id = a.dataset.target;
  const el = document.getElementById(id);
  if (el) sections.push({{ id, el, a }});
}});

let activeId = null;
function setActive(id) {{
  if (id === activeId) return;
  tocLinks.forEach(a => a.classList.remove('is-active'));
  const target = sections.find(s => s.id === id);
  if (target) {{
    target.a.classList.add('is-active');
    activeId = id;
  }}
}}

if ('IntersectionObserver' in window) {{
  const io = new IntersectionObserver((entries) => {{
    // Pick the topmost in-view heading
    let top = null;
    for (const e of entries) {{
      if (!e.isIntersecting) continue;
      if (!top || e.boundingClientRect.top < top.boundingClientRect.top) top = e;
    }}
    if (top) setActive(top.target.id);
  }}, {{
    rootMargin: '-80px 0px -70% 0px',
    threshold: 0
  }});
  sections.forEach(s => io.observe(s.el));
}}

// Smooth scroll: also set active immediately on click
tocLinks.forEach(a => a.addEventListener('click', () => setActive(a.dataset.target)));

// Back-to-top button
const btn = document.getElementById('topBtn');
window.addEventListener('scroll', () => {{
  if (window.scrollY > 400) btn.classList.add('show'); else btn.classList.remove('show');
}});
</script>
</body>
</html>
"""

DST.write_text(HTML, encoding="utf-8")
print(f"OK: {DST}")
print(f"blocks: {len(out_blocks)}")
print(f"toc entries: {len(toc)}")
print(f"file size: {DST.stat().st_size:,} bytes")
