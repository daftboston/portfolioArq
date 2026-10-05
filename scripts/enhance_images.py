#!/usr/bin/env python3
"""Wrap <img> with <picture>+WebP where a sibling .webp exists; add loading=lazy below the fold."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]

# Above-fold: do not lazy-load
NO_LAZY_CLASS = re.compile(r"(?:^|\s)(?:hero-img|case-hero-img|profile-img)(?:\s|$)")

IMG_TAG_RE = re.compile(
    r"<img\b([^>]*?)>",
    re.IGNORECASE | re.DOTALL,
)

ATTR_RE = re.compile(
    r"""([^\s=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?""",
    re.IGNORECASE,
)


def parse_attrs(attr_str: str) -> dict[str, str | None]:
    attrs: dict[str, str | None] = {}
    for m in ATTR_RE.finditer(attr_str):
        key = m.group(1).lower()
        if key.startswith("/"):
            continue
        val = m.group(2) if m.group(2) is not None else (
            m.group(3) if m.group(3) is not None else m.group(4)
        )
        attrs[key] = val
    return attrs


def format_attrs(attrs: dict[str, str | None], prefer_order: list[str]) -> str:
    parts: list[str] = []
    seen = set()
    for key in prefer_order:
        if key in attrs:
            seen.add(key)
            val = attrs[key]
            if val is None:
                parts.append(key)
            else:
                parts.append(f'{key}="{val}"')
    for key, val in attrs.items():
        if key in seen:
            continue
        if val is None:
            parts.append(key)
        else:
            parts.append(f'{key}="{val}"')
    return " ".join(parts)


def resolve_src_to_fs(html_path: Path, src: str) -> Path | None:
    if not src or src.startswith(("http://", "https://", "data:", "//")):
        return None
    # Strip query/hash
    clean = src.split("?", 1)[0].split("#", 1)[0]
    decoded = unquote(clean)
    candidate = (html_path.parent / decoded).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def webp_src_from_original_src(src: str) -> str:
    """Replace extension with .webp and URL-encode path segments (required for srcset)."""
    from urllib.parse import quote

    base, sep, query = src.partition("?")
    base = re.sub(r"\.(jpe?g|png)$", ".webp", base, flags=re.IGNORECASE)
    if not base.lower().endswith(".webp"):
        base = re.sub(r"\.(jpe?g|png)$", ".webp", unquote(base), flags=re.IGNORECASE)
    segs = base.split("/")
    encoded = []
    for seg in segs:
        if not seg or seg in (".", ".."):
            encoded.append(seg)
        else:
            encoded.append(quote(unquote(seg), safe=".-_~"))
    new_base = "/".join(encoded)
    if sep:
        return new_base + "?" + query
    return new_base


def already_in_picture(html: str, img_start: int) -> bool:
    # Look back a bit for an open <picture without close
    window = html[max(0, img_start - 200) : img_start].lower()
    last_picture = window.rfind("<picture")
    last_close = window.rfind("</picture>")
    return last_picture != -1 and last_picture > last_close


def enhance_html(html_path: Path) -> bool:
    original = html_path.read_text(encoding="utf-8")
    html = original
    # Process from end to start so indices stay valid
    matches = list(IMG_TAG_RE.finditer(html))
    changed = False

    for m in reversed(matches):
        if already_in_picture(html, m.start()):
            continue
        attr_str = m.group(1)
        attrs = parse_attrs(attr_str)
        src = attrs.get("src")
        if not src:
            continue

        fs_path = resolve_src_to_fs(html_path, src)
        if fs_path is None or not fs_path.is_file():
            # Still may add lazy
            pass

        webp_fs = fs_path.with_suffix(".webp") if fs_path else None
        has_webp = bool(webp_fs and webp_fs.is_file())

        class_val = attrs.get("class") or ""
        is_above_fold = bool(NO_LAZY_CLASS.search(class_val))
        if not is_above_fold and "loading" not in attrs:
            attrs["loading"] = "lazy"
            changed = True
        elif is_above_fold and attrs.get("loading") == "lazy":
            # keep if explicitly set; heroes usually won't have it
            pass

        # decoding=async is a nice default for below-fold
        if not is_above_fold and "decoding" not in attrs:
            attrs["decoding"] = "async"

        order = ["src", "srcset", "alt", "class", "loading", "decoding", "width", "height"]
        new_img = f"<img {format_attrs(attrs, order)}>"

        if has_webp:
            webp_src = webp_src_from_original_src(src)
            replacement = (
                f"<picture>\n"
                f'                    <source type="image/webp" srcset="{webp_src}">\n'
                f"                    {new_img}\n"
                f"                </picture>"
            )
            # Tighten indentation for single-line imgs
            if "\n" not in m.group(0):
                replacement = (
                    f'<picture><source type="image/webp" srcset="{webp_src}">{new_img}</picture>'
                )
            html = html[: m.start()] + replacement + html[m.end() :]
            changed = True
        else:
            if new_img != m.group(0):
                html = html[: m.start()] + new_img + html[m.end() :]
                changed = True

    if changed and html != original:
        html_path.write_text(html, encoding="utf-8")
        return True
    return False


def main() -> None:
    files = [ROOT / "index.html"] + sorted((ROOT / "projects").glob("*.html"))
    updated = []
    for f in files:
        if enhance_html(f):
            updated.append(str(f.relative_to(ROOT)))
    print(f"Updated {len(updated)} files:")
    for u in updated:
        print(" ", u)


if __name__ == "__main__":
    main()
