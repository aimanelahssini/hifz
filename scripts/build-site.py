#!/usr/bin/env python3
"""Build localized Hifz landing pages with hreflang, sitemap and robots.txt."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
sys.path.insert(0, str(SITE / "i18n"))
from locales import LOCALES, NAMES  # noqa: E402

CONFIG = json.loads((SITE / "config.json").read_text())
BASE = os.environ.get("HIFZ_SITE_URL", CONFIG["base_url"]).rstrip("/")
DEFAULT = CONFIG["default_locale"]
ORDER = CONFIG["locales"]

APPLE = (SITE / "assets" / "icon-apple.svg").read_text()
LINUX = (SITE / "assets" / "icon-linux.svg").read_text()
# Inline SVGs for buttons (strip XML declaration, keep viewBox fill).
APPLE_INLINE = re.sub(r"<\?xml[^>]*>", "", APPLE).strip().replace(
    "<svg ", '<svg width="22" height="22" aria-hidden="true" '
)
LINUX_INLINE = re.sub(r"<\?xml[^>]*>", "", LINUX).strip().replace(
    "<svg ", '<svg width="22" height="22" aria-hidden="true" '
)


def url_for(locale: str) -> str:
    return f"{BASE}/" if locale == DEFAULT else f"{BASE}/{locale}/"


def path_for(locale: str) -> Path:
    return SITE / "index.html" if locale == DEFAULT else SITE / locale / "index.html"


def asset_root(locale: str) -> str:
    return "" if locale == DEFAULT else "../"


def hreflang_tags() -> str:
    lines = []
    for loc in ORDER:
        lines.append(f'<link rel="alternate" hreflang="{loc}" href="{url_for(loc)}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url_for(DEFAULT)}">')
    return "\n".join(lines)


def lang_href(current: str, target: str) -> str:
    if current == DEFAULT:
        return "./" if target == DEFAULT else f"{target}/"
    return "../" if target == DEFAULT else f"../{target}/"


def lang_menu(current: str) -> str:
    items = []
    for loc in ORDER:
        cur = ' aria-current="page"' if loc == current else ""
        items.append(
            f'<a href="{lang_href(current, loc)}" data-lang="{loc}"{cur}>'
            f'<span>{NAMES[loc]}</span><span lang="{loc}">{loc.upper()}</span></a>'
        )
    return "\n          ".join(items)


def json_ld(t: dict, locale: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": t["schema_name"],
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "macOS 14+, Linux (GNOME)",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "description": t["schema_desc"],
        "url": url_for(locale),
        "inLanguage": locale,
        "downloadUrl": [
            f"{BASE}/downloads/Hifz-macOS.dmg",
            f"{BASE}/downloads/Hifz-linux-installer.sh",
        ],
        "license": "https://opensource.org/licenses/MIT",
        "isAccessibleForFree": True,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def render(locale: str) -> str:
    t = LOCALES[locale]
    root = asset_root(locale)
    canonical = url_for(locale)
    geo = (
        f'<script src="{root}assets/geo.js" defer></script>'
        if locale == DEFAULT
        else ""
    )
    hifz = {
        "locale": locale,
        "assetRoot": root,
        "whereBismillah": t["where_bismillah"],
        "whereAyah": t["where_ayah"],
        "endHint": t["end_hint"],
        "soFarFirst": t["so_far_first"],
        "soFarOne": t["so_far_one"],
        "soFarN": t["so_far_n"],
        "recitationOff": t["recitation_off"],
        "recitationOn": t["recitation_on"],
        "coach": {k: t[f"coach_{k}"] for k in range(1, 7)},
    }
    fine = t["fine"].replace("{version}", '<span id="version">1.0.0</span>')

    return f"""<!doctype html>
<html lang="{t['locale']}" dir="{t['dir']}" data-base="{BASE}/">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t['title']}</title>
<meta name="description" content="{t['description']}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta name="theme-color" content="#f6f0e4">
<link rel="canonical" href="{canonical}">
{hreflang_tags()}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Hifz">
<meta property="og:locale" content="{t['og_locale']}">
{chr(10).join(f'<meta property="og:locale:alternate" content="{LOCALES[loc]["og_locale"]}">' for loc in ORDER if loc != locale)}
<meta property="og:title" content="{t['title']}">
<meta property="og:description" content="{t['og_description']}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{BASE}/assets/demo-poster.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t['title']}">
<meta name="twitter:description" content="{t['og_description']}">
<meta name="twitter:image" content="{BASE}/assets/demo-poster.jpg">
<link rel="icon" href="{root}assets/logo.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Amiri&family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}assets/site.css">
<script type="application/ld+json">
{json_ld(t, locale)}
</script>
</head>
<body>

<div class="top">
  <div class="wrap">
    <a class="brand" href="{canonical}"><img src="{root}assets/logo.svg" alt="">Hifz <span class="ar" lang="ar">حفظ</span></a>
    <nav>
      <a href="#always">{t['nav_always']}</a>
      <a href="#walkthrough">{t['nav_walkthrough']}</a>
      <a href="#phonetics">{t['nav_phonetics']}</a>
      <a class="nav-dl" href="#download">{t['nav_download']}</a>
      <details class="lang">
        <summary aria-label="{t['lang_label']}">{t['locale'].upper()}</summary>
        <div class="menu" role="list">
          {lang_menu(locale)}
        </div>
      </details>
    </nav>
  </div>
</div>

<header class="hero">
  <div class="wrap">
    <div>
      <p class="eyebrow"><span class="ar" lang="ar">حِفْظ</span>{t['eyebrow']}</p>
      <h1>{t['h1']}</h1>
      <p class="lead">{t['lead']}</p>
      <div class="dl-row">
        <a class="dl primary" href="{root}downloads/Hifz-macOS.dmg" download>
          {APPLE_INLINE}
          <span class="t">{t['dl_mac']}</span>
          <span class="s" data-size="Hifz-macOS.dmg">{t['dl_mac_sub']}</span>
        </a>
        <a class="dl secondary" href="{root}downloads/Hifz-linux-installer.sh" download>
          {LINUX_INLINE}
          <span class="t">{t['dl_linux']}</span>
          <span class="s" data-size="Hifz-linux-installer.sh">{t['dl_linux_sub']}</span>
        </a>
      </div>
      <p class="fine">{fine}</p>
    </div>

    <div>
      <div class="stage">
        <div class="menubar"><span>{t['notes']}</span><span id="clock">21:58</span></div>
        <div class="window" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
        <div class="card" id="card" tabindex="0" role="application" aria-label="{t['card_aria']}">
          <div class="head">
            <span class="num">56</span><b>Al-Wâqi'a</b>
            <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 3.5l3 3 3-3" fill="none" stroke="rgba(255,255,255,.4)" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
            <span id="where">{t['where_bismillah']}</span><span class="sp"></span>
            <span class="speed">1×</span>
            <button type="button" class="spk" id="spk" aria-label="{t['recitation_off']}" title="M">
              <svg width="15" height="14" viewBox="0 0 15 14" aria-hidden="true">
                <path d="M0 4.5h3l4-3.5v12l-4-3.5H0z" fill="currentColor"/>
                <path id="spk-waves" d="M9.5 4.5l4 4m0-4l-4 4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
            <span class="count zero" id="count"><svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M1.5 5.3l2.4 2.4 4.6-5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg><span id="n">0</span></span>
          </div>
          <div class="view"><div class="lines" id="lines"></div></div>
          <div class="ask"><b>{t['finish_q']}</b><small id="so-far">{t['so_far_first']}</small>
            <div><button type="button" id="no">{t['not_yet']}</button><button type="button" class="yes" id="yes">{t['yes_finished']}</button></div>
          </div>
        </div>
      </div>
      <div class="coach">
        <div class="steps" aria-hidden="true"><span id="s1"></span><span id="s2"></span><span id="s3"></span><span id="s4"></span></div>
        <p id="coach-text" aria-live="polite">{t['coach_1']}</p>
        <div class="keys">
          <button type="button" id="prev" aria-label="{t['prev_aria']}">↑</button>
          <button type="button" id="next" aria-label="{t['next_aria']}">↓</button>
        </div>
      </div>
    </div>
  </div>
</header>

<section id="always">
  <div class="wrap">
    <div class="intro">
      <h2>{t['always_h2']}</h2>
      <p>{t['always_p']}</p>
    </div>
    <div class="desk" id="desk" aria-hidden="true">
      <div class="bar"><span>{t['desktop']}</span><span>22:00</span></div>
      <div class="win notes">
        <div class="tb"><span class="dots"><i></i><i></i><i></i></span>{t['notes']}</div>
        <div class="body"><i style="width:88%"></i><i style="width:72%"></i><i style="width:94%"></i><i style="width:61%"></i><i style="width:80%"></i><i style="width:45%"></i></div>
      </div>
      <div class="win mail">
        <div class="tb"><span class="dots"><i></i><i></i><i></i></span>{t['mail']}</div>
        <div class="body"><i style="width:70%"></i><i style="width:92%"></i><i style="width:55%"></i><i style="width:78%"></i></div>
      </div>
      <div class="win cal">
        <div class="tb"><span class="dots"><i></i><i></i><i></i></span>{t['calendar']}</div>
        <div class="body"><b>1</b><b>2</b><b>3</b><b>4</b><b>5</b><b>6</b><b>7</b><b>8</b><b>9</b><b>10</b><b>11</b><b>12</b><b>13</b><b>14</b></div>
      </div>
      <div class="fly" id="fly">
        <div class="fh"><span>56</span><b>Al-Wâqi'a</b><span style="flex:1"></span><span>1×</span></div>
        <div class="flines">
          <p class="cur">Idhâ waqa'ati-l-wâqi'ah</p>
          <p>Laysa liwaq'atihâ kâdhibah</p>
          <p>Khâfidatour-râfi'ah</p>
          <p>Idhâ roujjati-l-ardou rajjâ</p>
        </div>
      </div>
    </div>
  </div>
</section>

<section id="walkthrough">
  <div class="wrap">
    <div class="intro">
      <h2>{t['walk_h2']}</h2>
      <p>{t['walk_p']}</p>
    </div>
    <div class="video">
      <video controls preload="metadata" poster="{root}assets/demo-poster.jpg" playsinline>
        <source src="{root}assets/demo.mp4" type="video/mp4">
      </video>
    </div>
  </div>
</section>

<section id="phonetics">
  <div class="wrap split">
    <div>
      <h2>{t['ph_h2']}</h2>
      <p>{t['ph_p']}</p>
      <div class="sample">
        <p class="ph">Idhâ waqa'ati-l-wâqi'ah</p>
        <p class="ar" lang="ar">إِذَا وَقَعَتِ ٱلْوَاقِعَةُ</p>
        <p class="ph">Laysa liwaq'atihâ kâdhibah</p>
        <p class="ph">Khâfidatour-râfi'ah</p>
      </div>
      <dl class="legend">
        <dt>ou</dt><dd>{t['leg_ou']}</dd>
        <dt>â î oû</dt><dd>{t['leg_long']}</dd>
        <dt>ch kh gh</dt><dd>{t['leg_ch']}</dd>
        <dt>'</dt><dd>{t['leg_hamza']}</dd>
        <dt>-</dt><dd>{t['leg_hyphen']}</dd>
      </dl>
    </div>
    <div>
      <h2>{t['keys_h2']}</h2>
      <p>{t['keys_p']}</p>
      <table class="keys">
        <tr><td><kbd>↓</kbd><kbd>Space</kbd></td><td>{t['key_next']}</td></tr>
        <tr><td><kbd>↑</kbd><kbd>⌫</kbd></td><td>{t['key_prev']}</td></tr>
        <tr><td><kbd>→</kbd><kbd>←</kbd></td><td>{t['key_speed']}</td></tr>
        <tr><td><kbd>M</kbd></td><td>{t['key_m']}</td></tr>
        <tr><td><kbd>A</kbd></td><td>{t['key_a']}</td></tr>
        <tr><td><kbd>H</kbd></td><td>{t['key_h']}</td></tr>
        <tr><td><kbd>Home</kbd></td><td>{t['key_home']}</td></tr>
      </table>
      <p style="margin-top:20px">{t['keys_more']}</p>
    </div>
  </div>
</section>

<section id="download">
  <div class="wrap">
    <div class="intro">
      <h2>{t['dl_h2']}</h2>
      <p>{t['dl_p']}</p>
    </div>
    <div class="platforms">
      <article class="platform">
        <header>
          {APPLE_INLINE}
          <div><h3>macOS</h3><p class="req">{t['mac_req']}</p></div>
        </header>
        <ol>
          <li>{t['mac_1']}</li>
          <li>{t['mac_2']}</li>
          <li>{t['mac_3']}</li>
        </ol>
        <a class="dl primary" href="{root}downloads/Hifz-macOS.dmg" download>
          {APPLE_INLINE}
          <span class="t">{t['dl_mac']}</span>
          <span class="s" data-size="Hifz-macOS.dmg">.dmg</span>
        </a>
      </article>
      <article class="platform">
        <header>
          {LINUX_INLINE}
          <div><h3>Linux</h3><p class="req">{t['linux_req']}</p></div>
        </header>
        <ol>
          <li>{t['linux_1']}</li>
          <li>{t['linux_2']}</li>
          <li>{t['linux_3']}</li>
        </ol>
        <a class="dl secondary" href="{root}downloads/Hifz-linux-installer.sh" download>
          {LINUX_INLINE}
          <span class="t">{t['dl_linux']}</span>
          <span class="s" data-size="Hifz-linux-installer.sh">.sh</span>
        </a>
      </article>
    </div>
  </div>
</section>

<footer>
  <div class="wrap">
    <span>{t['footer_credits']}</span>
    <span>{t['footer_source']}</span>
  </div>
</footer>

<script>window.HIFZ = {json.dumps(hifz, ensure_ascii=False)};</script>
{geo}
<script src="{root}assets/demo.js" defer></script>
</body>
</html>
"""


def write_sitemap() -> None:
    urls = []
    for loc in ORDER:
        urls.append(
            f"""  <url>
    <loc>{url_for(loc)}</loc>
    <changefreq>weekly</changefreq>
    <priority>{"1.0" if loc == DEFAULT else "0.8"}</priority>
  </url>"""
        )
    (SITE / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )


def write_robots() -> None:
    (SITE / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n"
    )


def main() -> None:
    for loc in ORDER:
        if loc not in LOCALES:
            raise SystemExit(f"missing locale: {loc}")
        out = path_for(loc)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(loc))
        print(f"[hifz] site: wrote {out.relative_to(ROOT)}")
    write_sitemap()
    write_robots()
    print(f"[hifz] site: sitemap + robots · base={BASE}")


if __name__ == "__main__":
    main()
