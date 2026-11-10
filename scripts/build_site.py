#!/usr/bin/env python3
"""Build index.html (and optional production folder) from content/site.json."""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "site.json"
TEMPLATE_DIR = ROOT / "templates"
ASSETS = ROOT / "assets"


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def phone_tel(display: str) -> str:
    return re.sub(r"\D+", "", display)


def instagram_handle(url: str) -> str:
    path = re.sub(r"https?://(www\.)?instagram\.com/", "", url).strip("/")
    return path.split("/")[0]


def esc(text: str) -> str:
    """Escape HTML text without turning apostrophes into entities (match current markup)."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def highlight_in(text: str, word: str) -> str:
    """Wrap the first occurrence of word in <em>, keeping surrounding text escaped."""
    if not word or word not in text:
        return esc(text)
    i = text.find(word)
    return esc(text[:i]) + "<em>" + esc(word) + "</em>" + esc(text[i + len(word):])


def banner_group(items: list[str]) -> str:
    parts = []
    for item in items:
        parts.append("<span>" + esc(item) + "</span><i>✦</i>")
    return "".join(parts)


def services_html(services: list[dict]) -> str:
    chunks = []
    delays = ["", ".1s", ".2s"]
    for i, svc in enumerate(services):
        delay = delays[i] if i < len(delays) else f".{i}s"
        num = f"{i+1:02d}"
        sid = slugify(svc["title"])
        title = esc(svc["title"])
        if delay:
            open_tag = f'      <article class="card reveal" style="--d:{delay}" id="{sid}">'
        else:
            open_tag = f'      <article class="card reveal" id="{sid}">'
        chunks.append(
            f'{open_tag}\n'
            f'        <span class="card__num">{num}</span>\n'
            f'        <h3>{title}</h3>\n'
            f'        <p class="card__tagline">{esc(svc["tagline"])}</p>\n'
            f'        <p>{esc(svc["body"])}</p>\n'
            f'        <a href="#contact" class="card__link" data-service="{title}">{esc(svc["button"])} <span aria-hidden="true">→</span></a>\n'
            f'      </article>\n'
        )
    return "".join(chunks)


def testimonials_html(items: list[dict]) -> str:
    chunks = []
    delays = ["", ".1s", ".2s"]
    for i, t in enumerate(items):
        delay = delays[i] if i < len(delays) else f".{i}s"
        delay_attr = f' style="--d:{delay}"' if delay else ""
        av = initials(t["name"])
        quote = t["quote"].strip()
        # Stored without wrapping quotation marks; match the current site typography.
        chunks.append(
            f'      <figure class="quote reveal"{delay_attr}>\n'
            f'        <div class="stars" aria-label="5 out of 5 stars">★★★★★</div>\n'
            f'        <blockquote>“{html.escape(quote)}”</blockquote>\n'
            f'        <figcaption><span class="avatar">{html.escape(av)}</span><span><strong>{html.escape(t["name"])}</strong>{html.escape(t["role"])}</span></figcaption>\n'
            f'      </figure>\n'
        )
    return "".join(chunks)


def service_options(services: list[dict]) -> str:
    return "".join(f'<option>{esc(s["title"])}</option>' for s in services)


def maybe_refresh_about_photo(photo: str) -> None:
    """If Meghan uploaded a new source photo, rebuild the display WebP/JPEG set."""
    src = ROOT / photo
    if not src.is_file():
        return
    targets = [
        ROOT / "assets/img/meghan-480.webp",
        ROOT / "assets/img/meghan-720.webp",
        ROOT / "assets/img/meghan-960.webp",
        ROOT / "assets/img/meghan-720.jpg",
    ]
    # Leave the existing optimized set alone when the source is already one of them
    # or is older than the derivatives.
    if src.resolve() in {t.resolve() for t in targets if t.exists()}:
        return
    if all(t.exists() and t.stat().st_mtime >= src.stat().st_mtime for t in targets):
        return
    try:
        from PIL import Image, ImageOps
    except ImportError:
        print("Pillow is not installed; skipped photo resize.", file=sys.stderr)
        return
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    for w, name, fmt, q in [
        (480, "meghan-480.webp", "WEBP", 80),
        (720, "meghan-720.webp", "WEBP", 80),
        (960, "meghan-960.webp", "WEBP", 76),
        (720, "meghan-720.jpg", "JPEG", 82),
    ]:
        h = round(w * im.height / im.width)
        resized = im.resize((w, h), Image.Resampling.LANCZOS)
        dest = ROOT / "assets/img" / name
        if fmt == "WEBP":
            resized.save(dest, "WEBP", quality=q, method=6)
        else:
            resized.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        print(f"wrote {dest.relative_to(ROOT)} ({w}x{h})")


def build(noindex: bool = False, production: bool = False, out: Path | None = None, out_dir: Path | None = None) -> Path:
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    maybe_refresh_about_photo(data.get("about", {}).get("photo", ""))

    services = data["services"]
    for i, s in enumerate(services):
        s = dict(s)
        s["id"] = slugify(s["title"])
        s["num"] = f"{i+1:02d}"
        s["delay"] = "" if i == 0 else f".{i}s" if i == 1 else f".{i*1}s"
        # delay already handled in services_html
        services[i] = s

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    tmpl = env.get_template("index.html")

    highlight = data["hero"].get("highlight") or ""
    line2_html = highlight_in(data["hero"]["headlineLine2"], highlight)
    heading = data["contact"].get("heading") or "Let's talk."
    heading_hl = data["contact"].get("headingHighlight") or "talk."
    contact_heading_html = highlight_in(heading, heading_hl)

    html_out = tmpl.render(
        noindex=bool(noindex or (not production and out_dir is None and noindex)),
        seo=data["seo"],
        hero={**data["hero"], "line2_html": line2_html},
        about=data["about"],
        approach=data["approach"],
        contact=data["contact"],
        services=services,
        instagram_handle=instagram_handle(data["contact"]["instagram"]),
        phone_tel=phone_tel(data["contact"]["phone"]),
        banner_sr=", ".join(data["banner"]),
        banner_group=banner_group(data["banner"]),
        services_html=services_html(data["services"]),
        testimonials_html=testimonials_html(data["testimonials"]),
        service_options=service_options(data["services"]),
        contact_heading_html=contact_heading_html,
    )

    # Fix noindex: caller sets it explicitly.
    # Re-render with the actual flag (cleanup the messy default above).
    return html_out


PRODUCTION_HTACCESS = r"""# Social Butterfly static site
DirectoryIndex index.html

<IfModule mod_rewrite.c>
  RewriteEngine On
  # Leave certificate challenges alone, then force HTTPS and apex host.
  RewriteRule ^\.well-known/ - [L]
  RewriteCond %{HTTP_HOST} ^www\.socialbutterfly\.agency$ [NC]
  RewriteRule ^ https://socialbutterfly.agency%{REQUEST_URI} [L,R=301]
  RewriteCond %{HTTP:X-Forwarded-Proto} !https
  RewriteCond %{HTTPS} off
  RewriteRule ^ https://socialbutterfly.agency%{REQUEST_URI} [L,R=301]
</IfModule>

<IfModule mod_headers.c>
  Header always set Strict-Transport-Security "max-age=10886400; preload"
</IfModule>

<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/html "access plus 5 minutes"
  ExpiresByType text/css "access plus 7 days"
  ExpiresByType application/javascript "access plus 7 days"
  ExpiresByType image/webp "access plus 30 days"
  ExpiresByType image/png "access plus 30 days"
  ExpiresByType image/jpeg "access plus 30 days"
  ExpiresByType font/woff2 "access plus 30 days"
  ExpiresByType video/mp4 "access plus 30 days"
</IfModule>

<IfModule mod_deflate.c>
  AddOutputFilterByType DEFLATE text/html text/css text/plain application/javascript application/json image/svg+xml
</IfModule>

<FilesMatch "\\.(html)$">
  <IfModule mod_headers.c>
    Header set Cache-Control "public, max-age=300, must-revalidate"
  </IfModule>
</FilesMatch>
"""


def write_outputs(html_out: str, production: bool, out: Path | None, out_dir: Path | None) -> Path:
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / "index.html"
        dest.write_text(html_out, encoding="utf-8")
        # Copy the static site (assets + optional robots)
        assets_dest = out_dir / "assets"
        if assets_dest.exists():
            shutil.rmtree(assets_dest)
        shutil.copytree(ASSETS, assets_dest)
        if production:
            (out_dir / "robots.txt").write_text(
                "User-agent: *\nAllow: /\n\nSitemap: https://socialbutterfly.agency/sitemap.xml\n",
                encoding="utf-8",
            )
            (out_dir / "sitemap.xml").write_text(
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
                "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
                "  <url>\n"
                "    <loc>https://socialbutterfly.agency/</loc>\n"
                "    <changefreq>weekly</changefreq>\n"
                "    <priority>1.0</priority>\n"
                "  </url>\n"
                "</urlset>\n",
                encoding="utf-8",
            )
            (out_dir / ".htaccess").write_text(PRODUCTION_HTACCESS, encoding="utf-8")
        else:
            (out_dir / ".nojekyll").write_text("", encoding="utf-8")
            (out_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
        print(f"wrote site folder {out_dir}")
        return dest
    dest = out or (ROOT / "index.html")
    dest.write_text(html_out, encoding="utf-8")
    print(f"wrote {dest}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the static site from content/site.json")
    parser.add_argument("--noindex", action="store_true", help="Add noindex,nofollow (preview)")
    parser.add_argument("--production", action="store_true", help="Production build: no noindex, public robots.txt")
    parser.add_argument("--out", type=Path, help="Write index.html to this path")
    parser.add_argument("--out-dir", type=Path, help="Write a full static folder (index + assets)")
    args = parser.parse_args()
    noindex = args.noindex and not args.production
    data_html = build.__wrapped__ if False else None

    def walk_esc(obj, skip_keys=("photo", "facebook", "twitter", "instagram", "email")):
        if isinstance(obj, dict):
            return {k: (v if k in skip_keys else walk_esc(v, skip_keys)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk_esc(v, skip_keys) for v in obj]
        if isinstance(obj, str):
            return esc(obj)
        return obj

    raw = json.loads(CONTENT.read_text(encoding="utf-8"))
    maybe_refresh_about_photo(raw.get("about", {}).get("photo", ""))
    data = walk_esc(raw)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )
    tmpl = env.get_template("index.html")
    highlight = raw["hero"].get("highlight") or ""
    line2_html = highlight_in(raw["hero"]["headlineLine2"], highlight)
    heading = raw["contact"].get("heading") or "Let's talk."
    heading_hl = raw["contact"].get("headingHighlight") or "talk."
    html_out = tmpl.render(
        noindex=noindex,
        production=args.production,
        seo=data["seo"],
        hero={**data["hero"], "line2_html": line2_html},
        about=data["about"],
        approach=data["approach"],
        contact=data["contact"],
        services=data["services"],
        instagram_handle=instagram_handle(raw["contact"]["instagram"]),
        phone_tel=phone_tel(raw["contact"]["phone"]),
        banner_sr=", ".join(data["banner"]),
        banner_group=banner_group(raw["banner"]),
        services_html=services_html(raw["services"]),
        testimonials_html=testimonials_html(raw["testimonials"]),
        service_options=service_options(raw["services"]),
        contact_heading_html=highlight_in(heading, heading_hl),
        services_heading_html=highlight_in(
            raw.get("servicesHeading", {}).get("heading") or "Smarter social media starts here",
            raw.get("servicesHeading", {}).get("headingHighlight") or "starts here",
        ),
    )
    write_outputs(html_out, args.production, args.out, args.out_dir)


if __name__ == "__main__":
    main()
