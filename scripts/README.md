# Phase C build scripts

Bilingual HTML at the repo root (`index.html`, `projects/*.html`) remains the **editable source of truth**.

## Regenerate after content edits

```bash
# 1) Optional: (re)create WebP siblings for new images
#    python3 -c '...'  or re-run your image conversion

# 2) Wrap <img> with <picture> + lazy where applicable (idempotent-ish; skip already pictured)
python3 scripts/enhance_images.py

# 3) Generate monolingual trees
python3 scripts/build_i18n.py
```

Outputs:

- `es/index.html`, `es/projects/*.html`
- `en/index.html`, `en/projects/*.html`

Do not hand-edit `es/` or `en/` — they are overwritten on rebuild.

Netlify: see `netlify.toml` (`/` → `/es/` or `/en/` by `Accept-Language`).
