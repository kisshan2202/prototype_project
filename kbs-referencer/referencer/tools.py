"""Tools the agent can call: fetch a URL, look up a DOI, format a reference."""
from __future__ import annotations

import io
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from google.adk.tools import ToolContext

from .formatters import SOURCE_TYPES, format_reference as _format_reference

MAX_BYTES = 12 * 1024 * 1024
UA = "Mozilla/5.0 (compatible; KBS-Referencer/1.0; +academic referencing helper)"
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s\"<>]+)", re.I)


# ----------------------------------------------------------------- SSRF protection
def _check_public_url(url: str) -> None:
    """The service is public, so refuse localhost / private / metadata addresses."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError("Only http(s) URLs are supported.")
    for info in socket.getaddrinfo(p.hostname, None):
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise ValueError("That address is not a public website.")


async def _guard(request: httpx.Request) -> None:  # runs on every redirect hop too
    _check_public_url(str(request.url))


# ----------------------------------------------------------------- fetch_source
def _find_doi(candidates: list[str], url: str) -> str | None:
    for text in [*candidates, url]:
        m = DOI_RE.search(text or "")
        if m:
            return m.group(1).rstrip(".,;)")
    return None


def _site_from_domain(url: str) -> str:
    """'https://www.amazee.io/blog/x' -> 'amazee.io' (a last-resort publisher hint)."""
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _html_summary(url: str, raw: bytes, encoding: str | None) -> dict:
    soup = BeautifulSoup(raw.decode(encoding or "utf-8", errors="replace"), "html.parser")
    meta: dict[str, list[str]] = {}
    for m in soup.find_all("meta"):
        key = (m.get("name") or m.get("property") or "").strip().lower()
        val = (m.get("content") or "").strip()
        if key and val and (key.startswith(("citation_", "dc.", "dcterms.", "og:", "article:", "prism."))
                            or key in {"author", "description", "date", "publisher", "keywords",
                                       "twitter:site", "twitter:creator", "application-name"}):
            meta.setdefault(key, []).append(val)
    ld = []
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            ld.append(json.loads(s.string or ""))
        except (ValueError, TypeError):
            pass
    canonical = soup.find("link", rel="canonical")
    for t in soup(["script", "style", "noscript", "svg", "nav", "footer", "form"]):
        t.decompose()
    text = re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))
    footer_hint = None
    m = re.search(r"(?:©|copyright)\s*(?:\(c\))?\s*(\d{4})", soup.get_text(" ", strip=True)[-4000:], re.I)
    if m:
        footer_hint = m.group(1)
    return {
        "kind": "html",
        "title_tag": soup.title.get_text(strip=True) if soup.title else None,
        "h1": [h.get_text(" ", strip=True) for h in soup.find_all("h1")][:3],
        "meta": meta,
        "json_ld": json.dumps(ld)[:6000] if ld else None,
        "canonical_url": canonical.get("href") if canonical else None,
        "site_name_hint": (meta.get("og:site_name") or meta.get("publisher")
                           or [_site_from_domain(url)])[0],
        "copyright_year_hint": footer_hint,
        "doi_hint": _find_doi(meta.get("citation_doi", []) + meta.get("dc.identifier", []), url),
        "text_excerpt": text[:7000],
    }


def _pdf_summary(raw: bytes) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(raw))
    info = reader.metadata or {}
    pages = []
    for i, page in enumerate(reader.pages[:4]):
        pages.append(f"--- page {i + 1} ---\n{(page.extract_text() or '').strip()}")
    text = "\n".join(pages)
    doi = DOI_RE.search(text)
    return {
        "kind": "pdf",
        "page_count": len(reader.pages),
        "pdf_metadata": {k.lstrip("/"): str(v) for k, v in dict(info).items()},
        "doi_hint": doi.group(1).rstrip(".,;)") if doi else None,
        "text_excerpt": text[:9000] or None,
        "note": None if text.strip() else "No selectable text: this PDF may be a scan.",
    }


BLOCKED_MSG = ("This site blocks automated access, so the page could not be read. Paste the article's "
               "DOI link (https://doi.org/...) or a direct link to the PDF instead.")


def looks_blocked(summary: dict) -> bool:
    """A 200 response that is an empty shell or an 'access denied' page, not the real article."""
    if summary.get("kind") != "html":
        return False
    text = (summary.get("text_excerpt") or "").lower()
    has_meta = any(k.startswith(("citation_", "dc.", "og:title", "prism.")) for k in summary.get("meta", {}))
    if has_meta or summary.get("json_ld"):
        return False
    return len(text) < 300 or any(p in text[:600] for p in (
        "access denied", "request blocked", "verify you are human", "captcha", "are you a robot",
        "enable javascript", "unusual traffic"))


async def _fetch(url: str) -> dict:
    try:
        _check_public_url(url)
        async with httpx.AsyncClient(follow_redirects=True, timeout=25, max_redirects=5,
                                     headers={"User-Agent": UA, "Accept-Language": "en"},
                                     event_hooks={"request": [_guard]}) as client:
            async with client.stream("GET", url) as r:
                if r.status_code >= 400:
                    return {"error": f"The site returned HTTP {r.status_code}. " + BLOCKED_MSG}
                chunks, size = [], 0
                async for c in r.aiter_bytes():
                    size += len(c)
                    if size > MAX_BYTES:
                        return {"error": "File is too large to read (over 12 MB)."}
                    chunks.append(c)
                raw, ctype, final = b"".join(chunks), r.headers.get("content-type", ""), str(r.url)
                enc = r.encoding
        if "pdf" in ctype.lower() or raw[:5] == b"%PDF-":
            out = _pdf_summary(raw)
        elif "html" in ctype.lower() or "xml" in ctype.lower() or "text" in ctype.lower():
            out = _html_summary(final, raw, enc)
            if looks_blocked(out):
                return {"error": BLOCKED_MSG}
        else:
            return {"error": f"Unsupported content type: {ctype or 'unknown'}."}
        out["final_url"] = final
        if out.get("doi_hint"):  # authoritative metadata now, so the model needs no extra round trip
            cr = await lookup_doi(out["doi_hint"])
            if "error" not in cr:
                out["crossref"] = cr
        return out
    except Exception as exc:  # the agent reads this and explains it to the user
        return {"error": f"Could not fetch the page: {exc}"}


# ----------------------------------------------------------------- lookup_doi
async def lookup_doi(doi: str) -> dict:
    """Look up authoritative bibliographic metadata for a DOI from Crossref.

    Args:
        doi: A DOI such as '10.1000/xyz123' (with or without the https://doi.org/ prefix).

    Returns:
        Authors (surname/initials), title, journal, volume, issue, pages, year, publisher.
        Prefer these values over guesses from page text. On failure: {"error": "..."}.
    """
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)
    try:
        async with httpx.AsyncClient(timeout=8, headers={"User-Agent": UA}) as c:
            r = await c.get(f"https://api.crossref.org/works/{doi}")
        if r.status_code != 200:
            return {"error": f"Crossref has no record for DOI {doi} (HTTP {r.status_code})."}
        m = r.json()["message"]
    except Exception as exc:
        return {"error": f"Crossref lookup failed: {exc}"}

    def initials(given: str) -> str:
        return "".join(w[0].upper() for w in re.findall(r"[A-Za-zÀ-ɏ]+", given or ""))

    authors = [
        {"surname": a["family"], "initials": initials(a.get("given", ""))} if "family" in a
        else {"organisation": a.get("name", "")}
        for a in m.get("author", [])
    ]
    issued = (m.get("issued") or m.get("published") or {}).get("date-parts", [[None]])[0]
    return {
        "doi": doi,
        "type": m.get("type"),
        "authors": authors,
        "year": str(issued[0]) if issued and issued[0] else None,
        "title": " ".join(m.get("title", [])) or None,
        "container": " ".join(m.get("container-title", [])) or None,
        "volume": m.get("volume"),
        "issue": m.get("issue"),
        "pages": m.get("page"),
        "publisher": m.get("publisher"),
        "url": m.get("URL"),
    }


async def fetch_source(url: str) -> dict:
    """Download a web page or PDF and return its text and citation metadata.

    Args:
        url: The public http(s) address of the source the student wants to reference.

    Returns:
        A dict with kind ('html' or 'pdf'), meta tags (citation_*, dc.*, og:*), JSON-LD,
        a text excerpt, any DOI found, a 'crossref' entry when a DOI was found, and the
        final URL. On failure: {"error": "..."}. If the page is blocked but the URL contains
        a DOI, the result has kind 'crossref_only' with the Crossref record.
    """
    out = await _fetch(url)
    if "error" in out:
        doi = _find_doi([], url)
        if doi:  # page unreadable, but the link itself names the article
            cr = await lookup_doi(doi)
            if "error" not in cr:
                return {"kind": "crossref_only", "final_url": url, "doi_hint": doi, "crossref": cr,
                        "note": "The page could not be read; details come from Crossref only."}
    return out


# ----------------------------------------------------------------- format_reference
def format_reference(source_type: str, fields: dict, first_use: bool = True,
                     tool_context: ToolContext | None = None) -> dict:
    """Format a source in Kaplan Harvard style. Call this once you have extracted the fields.

    Args:
        source_type: One of: book, ebook, book_chapter, journal_article, news_article, report,
            standard, conference_paper, conference_proceedings, course_material, webpage,
            social_media, video, audio, image, dataset, software, brochure, broadcast, film,
            legislation, case_law, treaty.
        fields: The extracted details. Keys (use only those that were actually found):
            authors: list of {"surname","initials"} for people or {"organisation","acronym"};
            year; title (already in sentence case); container (journal / newspaper / book /
            conference name / course code and name); publisher; city; edition; volume; issue;
            pages ('255-261'); url; day_month ('10 May'); report_number; medium; version;
            editors (same shape as authors); location; jurisdiction (Cth, NSW...); court
            (e.g. NSWSC); abbreviation; online (true if read online); viewed (leave out to use today).
        first_use: True for the first citation of an organisation (adds its [ACRONYM]).

    Returns:
        reference_text / reference_html (italics as <i>), in-text citations, missing_fields, notes.
    """
    if source_type not in SOURCE_TYPES:
        return {"error": f"Unknown source_type {source_type!r}. Use one of {sorted(SOURCE_TYPES)}."}
    try:
        result = _format_reference(source_type, fields, first_use)
    except KeyError as exc:
        return {"error": f"Missing required field {exc} for {source_type}."}
    if tool_context is not None:
        tool_context.actions.skip_summarization = True  # the result IS the answer: no extra model call
    return result
