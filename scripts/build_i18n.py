#!/usr/bin/env python3
"""
Generate monolingual /es and /en trees from bilingual source HTML.

Source of truth: root index.html + projects/*.html (stacked .esp / .eng).
Output: es/** and en/** with only one language, rewritten asset/script links,
and language toggle that navigates between locale trees.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("es", "en")
# CSS/JS class used in source for Spanish vs English snippets
CLASS_FOR = {"es": "esp", "en": "eng"}
OTHER_CLASS = {"es": "eng", "en": "esp"}


def depth_prefix(rel_posix: str) -> str:
    """Relative prefix from generated file back to site root."""
    depth = rel_posix.count("/")
    return "../" * (depth + 1)


def rewrite_root_relative(url: str, prefix: str) -> str:
    """Rewrite links that pointed at site-root-relative bilingual paths."""
    if not url or url.startswith(("http://", "https://", "mailto:", "tel:", "wa.me", "#", "data:", "//")):
        return url
    # Already absolute from domain root
    if url.startswith("/"):
        # /assets/... stays; /projects/... should become /{locale}/projects/...
        # Handled separately with locale awareness
        return url

    # Normalize ./foo
    clean = url[2:] if url.startswith("./") else url

    # Assets, styles, main.js shared at repo root
    if clean.startswith("assets/") or clean.startswith("main.js") or clean.startswith("language.js"):
        return prefix + clean

    # From a project page: ../assets, ../main.js, ../index.html
    if clean.startswith("../"):
        rest = clean[3:]
        if rest.startswith("assets/") or rest.startswith("main.js") or rest.startswith("language.js"):
            return prefix + rest
        if rest.startswith("index.html") or rest == "index.html":
            # Stay inside locale tree → ../index.html from projects/
            return "../" + rest
        if rest.startswith("projects/"):
            return "../" + rest
        # Other ../ paths: go up to locale root then apply
        return "../" + rest

    # projects/foo.html from home → keep relative inside locale
    if clean.startswith("projects/"):
        return clean

    # Bare index.html
    if clean.startswith("index.html"):
        return clean

    return url


def rewrite_href_for_locale(url: str, locale: str, rel_posix: str) -> str:
    prefix = depth_prefix(rel_posix)
    if not url or url.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:", "//")):
        return url

    # WhatsApp / external already handled

    if url.startswith("/"):
        # Domain-absolute: map bilingual paths into locale
        if url == "/" or url.startswith("/index"):
            return f"/{locale}/"
        if url.startswith("/projects/"):
            return f"/{locale}" + url
        if url.startswith("/assets/") or url.startswith("/main.js"):
            return url
        if url.startswith("/es/") or url.startswith("/en/"):
            return url
        return url

    return rewrite_root_relative(url, prefix)


def is_lang_element(classes: list[str], keep: str, drop: str) -> str | None:
    """Return 'keep', 'drop', or None (shared)."""
    has_keep = keep in classes
    has_drop = drop in classes
    if has_drop and not has_keep:
        return "drop"
    if has_keep and not has_drop:
        return "keep"
    if has_keep and has_drop:
        # Ambiguous — treat as shared but strip both lang classes later
        return "shared"
    return None


def strip_lang_tree(soup: BeautifulSoup, locale: str) -> None:
    keep = CLASS_FOR[locale]
    drop = OTHER_CLASS[locale]

    # Collect first, then decompose (mutating while iterating breaks BS4)
    to_drop = []
    for el in soup.find_all(True):
        classes = el.get("class") or []
        if not isinstance(classes, list):
            classes = [classes]
        verdict = is_lang_element(classes, keep, drop)
        if verdict == "drop":
            to_drop.append(el)

    for el in to_drop:
        el.decompose()

    # Clean remaining keep-class markers (optional: leave for CSS no-ops)
    for el in soup.find_all(True):
        classes = el.get("class") or []
        if not isinstance(classes, list):
            continue
        if keep in classes or drop in classes:
            new_classes = [c for c in classes if c not in (keep, drop, "displayOn", "displayOff")]
            if new_classes:
                el["class"] = new_classes
            elif "class" in el.attrs:
                del el["class"]


def fix_duplicate_ids(soup: BeautifulSoup) -> None:
    """After stripping, duplicate id pairs like facts-heading / facts-heading-en may remain one."""
    seen: set[str] = set()
    for el in soup.find_all(True):
        eid = el.get("id")
        if not eid:
            continue
        if eid in seen:
            del el["id"]
        else:
            seen.add(eid)


def prune_aria_refs(soup: BeautifulSoup) -> None:
    """Drop id refs that pointed at the other language's (now removed) element."""
    ids = {el.get("id") for el in soup.find_all(True) if el.get("id")}
    for attr in ("aria-labelledby", "aria-describedby"):
        for el in soup.find_all(attrs={attr: True}):
            kept = [ref for ref in el[attr].split() if ref in ids]
            if kept:
                el[attr] = " ".join(kept)
            else:
                del el[attr]


def set_document_lang(soup: BeautifulSoup, locale: str) -> None:
    html = soup.find("html")
    if html:
        html["lang"] = locale


def rewrite_urls(soup: BeautifulSoup, locale: str, rel_posix: str) -> None:
    prefix = depth_prefix(rel_posix)

    for tag in soup.find_all(["a", "link", "script", "img", "source"]):
        for attr in ("href", "src", "srcset"):
            if not tag.has_attr(attr):
                continue
            val = tag[attr]
            if attr == "srcset":
                # "url1 1x, url2 2x" or single url
                parts = []
                for chunk in val.split(","):
                    chunk = chunk.strip()
                    if not chunk:
                        continue
                    bits = chunk.split()
                    bits[0] = rewrite_href_for_locale(bits[0], locale, rel_posix)
                    parts.append(" ".join(bits))
                tag[attr] = ", ".join(parts)
            else:
                tag[attr] = rewrite_href_for_locale(val, locale, rel_posix)

    # picture sources already covered via source[srcset]


def wire_language_toggle(soup: BeautifulSoup, locale: str, rel_posix: str) -> None:
    """Ensure frosted toggle reflects locale and navigates to the counterpart page."""
    other = "en" if locale == "es" else "es"
    # Counterpart path: same relative file under other locale
    # From browser: /es/projects/foo.html ↔ /en/projects/foo.html
    counterpart = "/" + other + "/" + rel_posix
    if counterpart.endswith("/index.html"):
        counterpart = counterpart[: -len("index.html")]
    elif rel_posix == "index.html":
        counterpart = f"/{other}/"

    container = soup.select_one(".switchLanguageContainer")
    if not container:
        # Inject toggle if missing (home has it; case studies have it)
        return

    # Mark current locale on the switch for CSS/JS
    switch = (
        container.select_one(".lang-toggle")
        or container.select_one(".switch.language")
        or container.select_one(".language")
    )
    if switch:
        switch["data-locale"] = locale
        switch["data-counterpart"] = counterpart
        if switch.name != "button":
            switch["role"] = "button"
            switch["tabindex"] = "0"
        # Aria: announce the language you will switch TO
        switch["aria-label"] = (
            "Switch to English" if locale == "es" else "Cambiar a Español"
        )
        # Visual: thumb/ball — EN is ball-move (right side)
        ball = (
            switch.select_one(".lang-toggle__thumb")
            or switch.select_one(".ball-lang")
            or switch.select_one(".ball")
        )
        eng_ind = switch.select_one("#eng")
        esp_ind = switch.select_one("#esp")
        if locale == "en":
            if ball:
                classes = list(ball.get("class", []))
                if "ball-move" not in classes:
                    classes.append("ball-move")
                ball["class"] = classes
            if eng_ind:
                eng_ind["class"] = [x for x in (eng_ind.get("class") or []) if x != "langOn"]
            if esp_ind:
                c = list(esp_ind.get("class") or [])
                if "langOn" not in c:
                    c.append("langOn")
                esp_ind["class"] = c
        else:
            if ball:
                ball["class"] = [x for x in (ball.get("class") or []) if x != "ball-move"]
            if esp_ind:
                esp_ind["class"] = [x for x in (esp_ind.get("class") or []) if x != "langOn"]
            if eng_ind:
                c = list(eng_ind.get("class") or [])
                if "langOn" not in c:
                    c.append("langOn")
                eng_ind["class"] = c


def update_meta_description(soup: BeautifulSoup, locale: str) -> None:
    """Prefer the half of bilingual meta descriptions when split by / or · — leave as-is if complex."""
    # Titles are mostly shared brand names; leave them.
    pass


def add_hreflang(soup: BeautifulSoup, locale: str, rel_posix: str) -> None:
    head = soup.find("head")
    if not head:
        return
    # Remove existing alternate hreflang we may have added
    for link in head.find_all("link", rel="alternate"):
        if link.get("hreflang"):
            link.decompose()

    path = rel_posix
    if path == "index.html":
        es_href = "/es/"
        en_href = "/en/"
        x_default = "/es/"
    else:
        es_href = "/es/" + path
        en_href = "/en/" + path
        x_default = es_href

    for hreflang, href in (("es", es_href), ("en", en_href), ("x-default", x_default)):
        tag = soup.new_tag("link", rel="alternate", hreflang=hreflang, href=href)
        head.append(tag)


def process_file(src: Path, locale: str, rel_posix: str) -> str:
    html = src.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")

    strip_lang_tree(soup, locale)
    fix_duplicate_ids(soup)
    prune_aria_refs(soup)
    set_document_lang(soup, locale)
    rewrite_urls(soup, locale, rel_posix)
    wire_language_toggle(soup, locale, rel_posix)
    add_hreflang(soup, locale, rel_posix)

    # Banner comment
    banner = Comment(f" Generated by scripts/build_i18n.py — locale={locale} — do not edit; edit source then rebuild. ")
    if soup.contents:
        soup.insert(0, banner)

    # BeautifulSoup may alter formatting; acceptable for generated output
    out = str(soup)
    if not out.lstrip().lower().startswith("<!doctype"):
        out = "<!DOCTYPE html>\n" + out
    return out


def collect_sources() -> list[tuple[Path, str]]:
    items = [(ROOT / "index.html", "index.html")]
    for p in sorted((ROOT / "projects").glob("*.html")):
        items.append((p, f"projects/{p.name}"))
    return items


def build() -> None:
    sources = collect_sources()
    for locale in LOCALES:
        out_root = ROOT / locale
        if out_root.exists():
            shutil.rmtree(out_root)
        out_root.mkdir(parents=True)
        (out_root / "projects").mkdir(parents=True, exist_ok=True)

        for src, rel in sources:
            text = process_file(src, locale, rel)
            dest = out_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
            print(f"  wrote {locale}/{rel}")

    print(f"Built {len(LOCALES)} locales × {len(sources)} pages")


if __name__ == "__main__":
    build()
