"""
Scrapes journal articles from the UNSW research profile for Sven Rogge and
rebuilds publications.html. Papers from the last 7 years are listed
in full; earlier papers link out to the UNSW profile.
"""

import re
import time
import html as html_module
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.parse

UNSW_BASE = "https://research.unsw.edu.au/people/scientia-professor-sven-rogge/publications"
SCHOLAR_URL = "https://scholar.google.com/citations?user=0EeBxOIAAAAJ"
CUTOFF_YEAR = datetime.now().year - 7

# Only include these publication types
WANTED_SECTIONS = {"Journal articles", "Journal Articles"}


def fetch_page(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "rogge-group-website/1.0 (public research site)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s).strip()


def clean(s):
    return html_module.unescape(strip_tags(s)).strip()


def extract_doi(text):
    m = re.search(r'href=["\']([^"\']*doi\.org/[^"\']+)["\']', text)
    if m:
        url = m.group(1)
        doi = re.sub(r'https?://(?:dx\.)?doi\.org/', '', url).strip()
        return doi
    m = re.search(r'10\.\d{4,}/\S+', text)
    if m:
        return m.group(0).rstrip('.,)')
    return ""


def parse_year(text):
    m = re.search(r'\b(20\d{2}|19\d{2})\b', text)
    return int(m.group(1)) if m else 0


def parse_entries(html):
    """
    The UNSW page uses CSS classes: rg-author, rg-year, rg-title, rg-source-title.
    Each entry is a <p> tag within the Journal articles section.
    """
    # Extract just the Journal articles section
    section_match = re.search(
        r'Journal articles?</h\d>(.*?)(?:<h\d|$)',
        html, re.DOTALL | re.IGNORECASE
    )
    section = section_match.group(1) if section_match else html

    papers = []
    seen = set()

    for block in re.findall(r'<p>(.*?)</p>', section, re.DOTALL):
        authors_m = re.search(r'class="rg-author">(.*?)</span>', block, re.DOTALL)
        year_m    = re.search(r'class="rg-year">(.*?)</span>', block, re.DOTALL)
        title_m   = re.search(r'class="rg-title">(.*?)</span>', block, re.DOTALL)
        venue_m   = re.search(r'class="rg-source-title">(.*?)</i>', block, re.DOTALL)

        if not (authors_m and year_m and title_m):
            continue

        authors = re.sub(r'\s*;\s*', ', ', clean(authors_m.group(1)))
        year    = int(clean(year_m.group(1)))
        title   = clean(title_m.group(1)).strip("'''""")
        venue   = clean(venue_m.group(1)) if venue_m else ""
        doi     = extract_doi(block)

        key = title.lower()
        if key in seen or year < 2000:
            continue
        seen.add(key)

        papers.append({"year": year, "authors": authors,
                       "title": title, "venue": venue, "doi": doi})

    return papers


def fetch_all_papers():
    papers = []
    page = 0
    while True:
        url = UNSW_BASE if page == 0 else f"{UNSW_BASE}?page={page}"
        print(f"  Fetching page {page}: {url}")
        html = fetch_page(url)
        batch = parse_entries(html)
        if not batch:
            break
        papers.extend(batch)
        # Check if there's a next page link
        if f'page={page + 1}' not in html:
            break
        page += 1
        time.sleep(1)
    return papers


def render_paper(p):
    title = p.get("title") or "Untitled"
    venue = p.get("venue") or ""
    authors = p.get("authors") or ""
    doi = p.get("doi") or ""
    doi_html = (f'<a href="https://doi.org/{doi}" target="_blank" '
                f'rel="noopener" class="pub-doi">DOI &rarr;</a>') if doi else ""
    venue_html = f'<span class="pub-journal">{venue}</span>' if venue else ""
    meta_inner = " ".join(filter(None, [venue_html, doi_html]))
    return f"""
          <div class="pub-item">
            <div class="pub-authors">{authors}</div>
            <div class="pub-title">{title}</div>
            <div class="pub-meta">{meta_inner}</div>
          </div>"""


def build_body(papers):
    recent = [p for p in papers if p["year"] >= CUTOFF_YEAR]
    recent.sort(key=lambda p: (-p["year"], p.get("title") or ""))

    by_year = {}
    for p in recent:
        by_year.setdefault(p["year"], []).append(p)

    blocks = []
    for year in sorted(by_year.keys(), reverse=True):
        items = "".join(render_paper(p) for p in by_year[year])
        blocks.append(f"""
      <!-- {year} -->
      <div class="pub-year-block">
        <div class="pub-year-label">{year}</div>
        <div class="pub-list">{items}
        </div>
      </div>""")

    blocks.append(f"""
      <!-- Earlier -->
      <div class="pub-year-block">
        <div class="pub-year-label">Earlier</div>
        <div class="pub-list">
          <div class="pub-item">
            <div class="pub-title">
              For publications before {CUTOFF_YEAR}, visit the
              <a href="{UNSW_BASE}" target="_blank" rel="noopener" class="pub-doi">UNSW Research Profile &rarr;</a>
            </div>
            <div class="pub-meta"></div>
          </div>
        </div>
      </div>""")

    return "\n".join(blocks)


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Publications &mdash; Rogge Group</title>
  <link rel="stylesheet" href="style.css" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@0,300;0,400;0,600;1,300;1,400&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />
</head>
<body>

  <nav class="nav">
    <a href="index.html" class="nav-brand">
      <span class="nav-brand-name">Rogge Group</span>
      <span class="nav-brand-sub">UNSW School of Physics</span>
    </a>
    <div class="nav-links">
      <a href="index.html" class="nav-link">Home</a>
      <a href="research.html" class="nav-link">Research</a>
      <a href="people.html" class="nav-link">People</a>
      <a href="publications.html" class="nav-link active">Publications</a>
      <a href="news.html" class="nav-link">News</a>
      <a href="positions.html" class="nav-link">Positions</a>
    </div>
    <button class="nav-menu-toggle" aria-label="Toggle menu">&#9776;</button>
  </nav>

  <div class="page-header">
    <div class="container">
      <div class="section-label">Research Output</div>
      <h1 class="page-title">Publications</h1>
      <p class="page-subtitle">
        Journal articles by the Rogge Group, auto-updated from the UNSW Research Profile.
        For the complete list see
        <a href="{unsw}" target="_blank" rel="noopener" class="page-header-link">UNSW Research</a>
        or
        <a href="{scholar}" target="_blank" rel="noopener" class="page-header-link">Google Scholar</a>.
        <span class="pub-updated">Last updated: {updated}</span>
      </p>
    </div>
  </div>

  <section class="section">
    <div class="container">
{body}
    </div>
  </section>

  <footer class="footer">
    <div class="container footer-inner">
      <div class="footer-brand">
        <div class="footer-name">Rogge Group</div>
        <div class="footer-sub">School of Physics &middot; UNSW Sydney</div>
        <div class="footer-sub">ARC Centre of Excellence for Quantum Computer Performance and Integration</div>
      </div>
      <nav class="footer-nav">
        <a href="index.html">Home</a>
        <a href="research.html">Research</a>
        <a href="people.html">People</a>
        <a href="publications.html">Publications</a>
        <a href="news.html">News</a>
        <a href="positions.html">Positions</a>
      </nav>
      <div class="footer-copy">&copy; {year} Rogge Group, UNSW Sydney.</div>
    </div>
  </footer>

  <script src="nav.js" defer></script>
</body>
</html>
"""


def main():
    print("Scraping UNSW research profile...")
    papers = fetch_all_papers()
    print(f"  Parsed {len(papers)} journal articles")

    if not papers:
        print("  No papers found -- aborting to avoid overwriting existing file.")
        return

    body = build_body(papers)
    now = datetime.utcnow()
    html = HTML_TEMPLATE.format(
        unsw=UNSW_BASE,
        scholar=SCHOLAR_URL,
        updated=now.strftime("%d %b %Y"),
        body=body,
        year=now.year,
    )

    out = Path(__file__).parent.parent / "publications.html"
    out.write_text(html, encoding="utf-8")
    print(f"  Written to {out}")


if __name__ == "__main__":
    main()
