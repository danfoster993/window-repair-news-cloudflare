import os
import re
import html
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from xml.sax.saxutils import escape as xml_escape

import requests
import markdown
import bleach


OWNER = "danfoster993"
REPO = "window-repair-news-cloudflare"

SITE_NAME = "Window Repair News"
BASE_URL = "https://window-repair-news-cloudflare.pages.dev"

DESCRIPTION = (
    "Window Repair News shares practical articles and "
    "insights about window repairs, glass replacement, "
    "maintenance, hardware, and home improvement."
)

OUTPUT = Path("site")
ARTICLES = OUTPUT / "articles"
ARTICLES.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
    "X-GitHub-Api-Version": "2022-11-28",
}

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/issues"


CSS = """
:root {
  --burgundy: #653d43;
  --dark: #382b31;
  --gold: #c6a36b;
  --cream: #faf7f1;
  --white: #ffffff;
  --muted: #756d6d;
  --border: #e8dfd7;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--dark);
  background: var(--cream);
  line-height: 1.75;
}

a {
  color: var(--burgundy);
}

.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--border);
}

.nav {
  max-width: 1120px;
  margin: auto;
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.brand {
  font-size: 27px;
  font-weight: 700;
  color: var(--burgundy);
  text-decoration: none;
}

.nav-links a {
  margin-left: 24px;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: var(--dark);
  text-decoration: none;
}

.hero {
  padding: 95px 24px;
  background: linear-gradient(
    125deg,
    #382b31 0%,
    #653d43 70%,
    #795158 100%
  );
  color: white;
  border-bottom: 6px solid var(--gold);
}

.hero-inner {
  max-width: 1120px;
  margin: auto;
}

.eyebrow {
  color: #e7c995;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13px;
  font-weight: bold;
}

.hero h1 {
  max-width: 850px;
  font-size: clamp(38px, 5vw, 65px);
  line-height: 1.13;
  margin: 22px 0;
}

.hero p {
  max-width: 730px;
  font-size: 19px;
  color: #f2e8e4;
}

.container {
  max-width: 1120px;
  margin: 65px auto;
  padding: 0 24px;
}

.section-title {
  font-size: 34px;
  margin-bottom: 30px;
}

.article-grid {
  display: grid;
  grid-template-columns: repeat(
    auto-fit,
    minmax(280px, 1fr)
  );
  gap: 26px;
}

.article-card {
  background: white;
  padding: 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.article-card::before {
  content: "";
  display: block;
  width: 45px;
  height: 4px;
  background: var(--gold);
  margin-bottom: 20px;
}

.article-card h2 {
  font-size: 24px;
  line-height: 1.35;
}

.article-card h2 a {
  color: var(--burgundy);
  text-decoration: none;
}

.article-card h2 a:hover,
.nav-links a:hover {
  color: #a16b4b;
}

.date {
  color: var(--muted);
  font-family: Arial, Helvetica, sans-serif;
  font-size: 14px;
}

.read-more {
  display: inline-block;
  margin-top: 12px;
  font-family: Arial, Helvetica, sans-serif;
  font-weight: bold;
  text-decoration: none;
}

.article-page {
  max-width: 880px;
  margin: 55px auto;
  padding: 48px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.article-page h1 {
  font-size: clamp(32px, 4vw, 46px);
  line-height: 1.25;
}

.article-content {
  overflow-wrap: anywhere;
}

.article-content img {
  max-width: 100%;
  height: auto;
  border-radius: 6px;
}

.article-content h2,
.article-content h3 {
  margin-top: 32px;
  color: var(--burgundy);
}

.article-content blockquote {
  border-left: 4px solid var(--gold);
  background: var(--cream);
  margin: 24px 0;
  padding: 12px 22px;
}

.article-content pre,
.article-content table {
  max-width: 100%;
  overflow-x: auto;
}

.article-content table {
  display: block;
  border-collapse: collapse;
}

.article-content th,
.article-content td {
  border: 1px solid var(--border);
  padding: 10px;
}

.site-footer {
  background: var(--dark);
  color: white;
  text-align: center;
  padding: 34px 24px;
  margin-top: 65px;
  font-family: Arial, Helvetica, sans-serif;
  font-size: 14px;
}

@media (max-width: 600px) {
  .nav {
    flex-wrap: wrap;
  }

  .nav-links a {
    margin: 0 16px 0 0;
  }

  .hero {
    padding: 60px 24px;
  }

  .article-page {
    margin: 18px;
    padding: 24px;
  }
}
"""


def safe(value):
    return html.escape(str(value or ""), quote=True)


def clean_text(value):
    return re.sub(
        r"\s+",
        " ",
        bleach.clean(
            str(value or ""),
            tags=[],
            strip=True
        )
    ).strip()


def excerpt(value, limit=155):
    text = clean_text(value)

    if len(text) <= limit:
        return text

    return text[:limit].rsplit(" ", 1)[0] + "..."


def allowed_attribute(tag, name, value):
    allowed = {
        "a": {"href", "title"},
        "img": {
            "src", "alt", "title", "width", "height"
        },
        "th": {"colspan", "rowspan"},
        "td": {"colspan", "rowspan"},
    }

    if name not in allowed.get(tag, set()):
        return False

    if name in ("href", "src"):
        url = str(value).strip()
        parsed = urlsplit(url)

        if parsed.scheme:
            return parsed.scheme.lower() in (
                "https", "http"
            )

        return (
            url.startswith("/")
            and not url.startswith("//")
        ) or url.startswith("#")

    return True


def render_content(body):
    rendered = markdown.markdown(
        str(body or ""),
        extensions=[
            "extra",
            "sane_lists",
            "nl2br"
        ],
    )

    return bleach.clean(
        rendered,
        tags=[
            "p", "br", "h1", "h2", "h3", "h4",
            "strong", "b", "em", "i",
            "a", "img", "ul", "ol", "li",
            "blockquote", "code", "pre", "hr",
            "table", "thead", "tbody",
            "tr", "th", "td", "del", "s",
        ],
        attributes=allowed_attribute,
        protocols=["http", "https"],
        strip=True,
    )


def layout(
    title,
    description,
    canonical,
    content,
    page_type="website"
):
    full_title = f"{title} | {SITE_NAME}"
    year = datetime.now(timezone.utc).year

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(full_title)}</title>
<meta name="description" content="{safe(description)}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{safe(canonical)}">

<meta property="og:type" content="{safe(page_type)}">
<meta property="og:site_name" content="{safe(SITE_NAME)}">
<meta property="og:title" content="{safe(full_title)}">
<meta property="og:description" content="{safe(description)}">
<meta property="og:url" content="{safe(canonical)}">

<meta name="twitter:card" content="summary">

<style>{CSS}</style>
</head>

<body>
<header class="site-header">
  <nav class="nav" aria-label="Main navigation">
    <a class="brand" href="/">{safe(SITE_NAME)}</a>

    <div class="nav-links">
      <a href="/">Home</a>
      <a href="/#articles">Articles</a>
    </div>
  </nav>
</header>

{content}

<footer class="site-footer">
  &copy; {year} {safe(SITE_NAME)}.
  News, insights, and practical window care.
</footer>
</body>
</html>"""


def get_issues():
    issues = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={
                "state": "open",
                "per_page": 100,
                "page": page,
                "sort": "created",
                "direction": "desc",
            },
            timeout=30,
        )

        response.raise_for_status()
        batch = response.json()

        if not batch:
            break

        issues.extend(
            item for item in batch
            if "pull_request" not in item
        )

        page += 1

    return issues


def publish():
    issues = get_issues()

    cards = []
    urls = [BASE_URL + "/"]
    active_files = set()

    for issue in issues:
        number = issue["number"]
        title = issue.get("title") or "Untitled"
        body = issue.get("body") or ""
        date = issue["created_at"][:10]

        filename = f"issue-{number}.html"
        active_files.add(filename)

        url = f"{BASE_URL}/articles/{filename}"
        urls.append(url)

        description = excerpt(body) or excerpt(title)
        content_html = render_content(body)

        article = f"""
<main class="article-page">
  <article>
    <h1>{safe(title)}</h1>
    <p class="date">
      <time datetime="{date}">{date}</time>
    </p>
    <div class="article-content">
      {content_html}
    </div>
  </article>
</main>"""

        page_html = layout(
            title,
            description,
            url,
            article,
            "article"
        )

        (ARTICLES / filename).write_text(
            page_html,
            encoding="utf-8"
        )

        cards.append(f"""
<article class="article-card">
  <p class="date">{date}</p>

  <h2>
    <a href="/articles/{filename}">
      {safe(title)}
    </a>
  </h2>

  <p>{safe(excerpt(body, 190))}</p>

  <a class="read-more" href="/articles/{filename}">
    Read article →
  </a>
</article>""")

    for old in ARTICLES.glob("issue-*.html"):
        if old.name not in active_files:
            old.unlink()

    listing = "\n".join(cards) if cards else (
        "<p>No articles published yet.</p>"
    )

    home = f"""
<section class="hero">
  <div class="hero-inner">
    <div class="eyebrow">Window repair & home improvement</div>

    <h1>Window Repair News & Practical Insights</h1>

    <p>
      Explore articles about window repairs,
      glass replacement, maintenance, hardware,
      and useful ideas for a more comfortable home.
    </p>
  </div>
</section>

<main class="container" id="articles">
  <h2 class="section-title">Latest Articles</h2>

  <div class="article-grid">
    {listing}
  </div>
</main>"""

    (OUTPUT / "index.html").write_text(
        layout(
            "Window Repair Articles & News",
            DESCRIPTION,
            BASE_URL + "/",
            home
        ),
        encoding="utf-8"
    )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(
            f"  <url><loc>{xml_escape(url)}</loc></url>"
            for url in urls
        )
        + "\n</urlset>\n"
    )

    (OUTPUT / "sitemap.xml").write_text(
        sitemap,
        encoding="utf-8"
    )

    (OUTPUT / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n",
        encoding="utf-8"
    )

    print(f"Published {len(issues)} articles.")


if __name__ == "__main__":
    publish()
