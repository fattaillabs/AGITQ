#!/usr/bin/env python3
"""AGITQ 페이지 SEO 후처리 — 멱등. 페이지를 고친 뒤 다시 실행한다.

  python3 tools/seo.py

각 HTML 에 <!-- seo-meta --> 블록을 (다시) 주입한다:
  canonical · hreflang(ko=기본, -en, -ja, x-default=ko) · Open Graph · Twitter ·
  description(없으면 본문 첫 문단에서 생성) · JSON-LD(홈=MobileApplication, 전략=Article,
  허브=CollectionPage, 모두 BreadcrumbList) . index_old_backup.html 은 noindex.
그리고 sitemap.xml 을 쓴다. 이미지·배지 등은 건드리지 않는다.
"""
import glob
import html
import json
import os
import re
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://fattaillabs.com/AGITQ/"
MARK, MARK_END = "<!-- seo-meta -->", "<!-- /seo-meta -->"
LANG_SUFFIX = {"ko": "", "en": "-en", "ja": "-ja"}
OG_LOCALE = {"ko": "ko_KR", "en": "en_US", "ja": "ja_JP"}
OG_IMAGE = BASE + "assets/og.jpg"
APP_NAME = {"ko": "아기티큐 플레이북 (AGITQ Playbook)", "en": "AGITQ Playbook", "ja": "アギティキュー・プレイブック (AGITQ Playbook)"}
SKIP = {"index_old_backup.html"}


def family_and_lang(fname):
    b = fname[:-5]
    for lang, suf in (("en", "-en"), ("ja", "-ja")):
        if b.endswith(suf):
            return b[: -len(suf)], lang
    return b, "ko"


def page_url(family, lang):
    b = family + LANG_SUFFIX[lang] + ".html"
    return BASE if b == "index.html" else BASE + b


def text(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return html.unescape(re.sub(r"\s+", " ", s)).strip()


def lead_description(body):
    """<h1> 다음 문단들을 이어 붙여 150자 안팎의 설명을 만든다."""
    b = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    m = re.search(r"<h1[^>]*>.*?</h1>", b, re.S)
    after = b[m.end():] if m else b
    ps = [text(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", after, re.S)]
    ps = [x for x in ps if len(x) > 30 and not x.startswith("©")]
    out = ""
    for p in ps:
        out = (out + " " + p).strip()
        if len(out) >= 120:
            break
    if len(out) > 158:
        cut = out[:158]
        out = cut[: max(cut.rfind(". "), cut.rfind("。"), cut.rfind(", "), 120)].rstrip(" ,") + "…"
    return out


def attr(s, rx):
    m = re.search(rx, s, re.S)
    return html.unescape(m.group(1).strip()) if m else ""


def esc(s):
    return html.escape(s, quote=True)


def seo_block(fname, s):
    family, lang = family_and_lang(fname)
    url = page_url(family, lang)
    body = s.split("<body", 1)[1] if "<body" in s else s
    title = attr(s, r"<title>([^<]*)</title>")
    desc = attr(s, r'<meta name="description" content="([^"]*)"') or lead_description(body)
    h1 = text(attr(s, r"<h1[^>]*>(.*?)</h1>")) or title
    lines = [MARK]
    if not re.search(r'<meta name="description"', s):
        lines.append(f'<meta name="description" content="{esc(desc)}">')
    lines.append(f'<link rel="canonical" href="{url}">')
    for l in ("ko", "en", "ja"):
        alt = family + LANG_SUFFIX[l] + ".html"
        if os.path.exists(os.path.join(ROOT, alt)):
            lines.append(f'<link rel="alternate" hreflang="{l}" href="{page_url(family, l)}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{page_url(family, "ko")}">')
    lines += [
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="AGITQ Playbook">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">',
        f'<meta property="og:image" content="{OG_IMAGE}">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:locale" content="{OG_LOCALE[lang]}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{esc(title)}">',
        f'<meta name="twitter:description" content="{esc(desc)}">',
        f'<meta name="twitter:image" content="{OG_IMAGE}">',
    ]
    org = {"@id": "https://fattaillabs.com/#org"}
    crumbs = [{"@type": "ListItem", "position": 1, "name": APP_NAME[lang], "item": page_url("index", lang)}]
    graph = []
    if family == "index":
        graph.append({"@type": "MobileApplication", "@id": url + "#app", "name": "AGITQ Playbook",
                      "alternateName": ["아기티큐 플레이북", "AGITQ"], "url": url, "inLanguage": lang,
                      "operatingSystem": "iOS, Android", "applicationCategory": "FinanceApplication",
                      "description": desc,
                      "installUrl": ["https://apps.apple.com/app/id6757210926",
                                     "https://play.google.com/store/apps/details?id=com.fattail.agitq"],
                      "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
                      "publisher": org})
        graph.append({"@type": "WebSite", "url": BASE, "name": "AGITQ Playbook", "inLanguage": ["ko", "en", "ja"], "publisher": org})
    else:
        if family.startswith("strategy-"):
            hub = page_url("strategies", lang)
            crumbs.append({"@type": "ListItem", "position": 2, "name": text(attr(open(os.path.join(ROOT, "strategies" + LANG_SUFFIX[lang] + ".html")).read(), r"<h1[^>]*>(.*?)</h1>")) or "Strategies", "item": hub})
            crumbs.append({"@type": "ListItem", "position": 3, "name": h1, "item": url})
            graph.append({"@type": "Article", "@id": url + "#article", "headline": h1, "description": desc,
                          "inLanguage": lang, "mainEntityOfPage": url, "image": OG_IMAGE,
                          "author": {"@type": "Organization", "name": "FatTail Labs", "url": "https://fattaillabs.com/"},
                          "publisher": org})
        elif family == "strategies":
            crumbs.append({"@type": "ListItem", "position": 2, "name": h1, "item": url})
            items = []
            for i, f in enumerate(sorted(glob.glob(os.path.join(ROOT, "strategy-*" + LANG_SUFFIX[lang] + ".html")))):
                fam2, l2 = family_and_lang(os.path.basename(f))
                if l2 != lang:
                    continue
                items.append({"@type": "ListItem", "position": len(items) + 1, "url": page_url(fam2, lang),
                              "name": text(attr(open(f).read(), r"<h1[^>]*>(.*?)</h1>"))})
            graph.append({"@type": "CollectionPage", "@id": url, "url": url, "name": title, "inLanguage": lang, "description": desc, "publisher": org})
            graph.append({"@type": "ItemList", "itemListElement": items})
        else:
            crumbs.append({"@type": "ListItem", "position": 2, "name": h1, "item": url})
            graph.append({"@type": "WebPage", "@id": url, "url": url, "name": title, "inLanguage": lang, "description": desc, "publisher": org})
    graph.append({"@type": "BreadcrumbList", "itemListElement": crumbs})
    lines.append('<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False) + "</script>")
    lines.append(MARK_END)
    return "\n".join(lines)


def process(fname):
    path = os.path.join(ROOT, fname)
    s = open(path).read()
    s = re.sub(re.escape(MARK) + r".*?" + re.escape(MARK_END) + r"\n?", "", s, flags=re.S)
    if fname in SKIP:
        if 'name="robots"' not in s:
            s = s.replace("</head>", '<meta name="robots" content="noindex, nofollow">\n</head>', 1)
        open(path, "w").write(s)
        return None
    s = s.replace("</head>", seo_block(fname, s) + "\n</head>", 1)
    open(path, "w").write(s)
    return fname


def main():
    done = []
    for f in sorted(os.listdir(ROOT)):
        if f.endswith(".html"):
            r = process(f)
            if r:
                done.append(r)
    today = datetime.date.today().isoformat()
    urls = []
    for f in done:
        fam, lang = family_and_lang(f)
        urls.append(page_url(fam, lang))
    body = "\n".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    open(os.path.join(ROOT, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n")
    print(f"{len(done)} pages, sitemap.xml")


if __name__ == "__main__":
    main()
