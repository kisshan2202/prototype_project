"""Deterministic Kaplan Harvard formatter.

The LLM extracts fields from a source; this module turns those fields into a reference-list
entry and in-text citations exactly as the Kaplan Harvard Style Guide (v4.0) prescribes.
Keeping the punctuation rules in code (not in the prompt) makes the output repeatable.

Field conventions (all optional unless listed as required for the type):
  authors:  list of {"surname": "Fazel", "initials": "M"} or {"organisation": "...", "acronym": "..."}
  year:     "2015" (empty -> n.d.)
  title, container (journal/newspaper/book/website), publisher, city, edition, volume, issue,
  pages ("255-261" or "7"), url, viewed ("5 January 2021", defaults to today),
  day_month ("10 May"), report_number, medium, version, editors, conference, location,
  course, jurisdiction, court, ...
"""
from __future__ import annotations

import html
import re
from datetime import date

SOURCE_TYPES = {
    "book", "ebook", "book_chapter", "journal_article", "news_article", "report", "standard",
    "conference_paper", "conference_proceedings", "course_material", "webpage", "social_media",
    "video", "audio", "image", "dataset", "software", "brochure", "broadcast", "film",
    "legislation", "case_law", "treaty",
}

# Fields that must be present for a complete entry (missing ones are reported, never invented).
REQUIRED = {
    "book": ["authors", "year", "title", "publisher"],
    "ebook": ["authors", "year", "title", "publisher", "url"],
    "book_chapter": ["authors", "year", "title", "container", "publisher"],
    "journal_article": ["authors", "year", "title", "container", "volume", "pages"],
    "news_article": ["authors", "year", "title", "container", "day_month"],
    "report": ["authors", "year", "title", "publisher"],
    "standard": ["authors", "year", "title", "publisher"],
    "conference_paper": ["authors", "year", "title", "container"],
    "conference_proceedings": ["authors", "year", "title"],
    "course_material": ["authors", "year", "title", "container"],
    "webpage": ["authors", "year", "title", "publisher"],
    "social_media": ["authors", "year", "title", "publisher"],
    "video": ["authors", "year", "title", "publisher"],
    "audio": ["authors", "year", "title", "publisher"],
    "image": ["authors", "year", "title", "publisher"],
    "dataset": ["authors", "year", "title", "publisher"],
    "software": ["year", "title", "publisher"],
    "brochure": ["authors", "year", "title", "publisher"],
    "broadcast": ["year", "title", "publisher"],
    "film": ["year", "title", "publisher"],
    "legislation": ["title", "year", "jurisdiction"],
    "case_law": ["title", "year", "court"],
    "treaty": ["title", "year"],
}
ONLINE_TYPES = {  # always carry "viewed <URL>"
    "ebook", "webpage", "social_media", "video", "audio", "image", "dataset", "software",
    "standard",
}
ITALIC_TITLE = {
    "book", "ebook", "report", "standard", "conference_proceedings", "webpage", "social_media",
    "video", "audio", "image", "dataset", "software", "brochure", "broadcast", "film",
}
QUOTED_TITLE = {"book_chapter", "journal_article", "news_article", "conference_paper",
                "course_material"}
DEFAULT_MEDIUM = {
    "video": "online video", "audio": "podcast", "image": "image", "dataset": "electronic dataset",
    "software": "software", "brochure": "flyer", "broadcast": "television broadcast",
    "film": "film",
}
TITLE_PLACEHOLDER = "[title not found]"
JURISDICTIONS = {"cth", "act", "nsw", "nt", "qld", "sa", "tas", "vic", "wa"}


# --------------------------------------------------------------------------- helpers
def _e(text) -> str:
    return html.escape(str(text).strip(), quote=False)


def _i(text) -> str:
    return f"<i>{_e(text)}</i>"


def _q(text) -> str:
    return f"‘{_e(text)}’"


def to_plain(markup: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def _blank(v) -> bool:
    return v is None or (isinstance(v, (str, list, tuple, dict)) and not v) or str(v).strip() == ""


def _initials(raw: str) -> str:
    """Initials without full stops: 'J. K.' -> 'JK', 'SP' -> 'SP', 'Jo Kay' -> 'JK'."""
    words = re.findall(r"[A-Za-zÀ-ɏ]+", raw or "")
    if words and all(len(w) == 1 or w.isupper() for w in words):
        return "".join(words)
    return "".join(w[0].upper() for w in words)


def _ordinal(edn) -> str | None:
    """Edition only applies from the second edition; returns e.g. '3rd edn' or None."""
    if _blank(edn):
        return None
    s = str(edn).strip().lower()
    m = re.search(r"\d+", s)
    if m:
        n = int(m.group())
        if n <= 1:
            return None
        suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix} edn"
    words = {"second": "2nd", "third": "3rd", "fourth": "4th", "fifth": "5th", "sixth": "6th",
             "seventh": "7th", "eighth": "8th", "ninth": "9th", "tenth": "10th"}
    for w, o in words.items():
        if w in s:
            return f"{o} edn"
    if s in {"first", "1st"}:
        return None
    return re.sub(r"\bed(ition)?\.?$", "edn", s)


def _pages(pages) -> tuple[str, bool]:
    """Return (text, is_range) with an en dash-free hyphen as in the guide ('255-261')."""
    p = str(pages).strip()
    p = re.sub(r"^(pp?\.?)\s*", "", p, flags=re.I)
    p = re.sub(r"\s*[–—]\s*", "-", p)
    return p, bool(re.search(r"[-,&]", p))


def _page_label(pages) -> str:
    p, many = _pages(pages)
    return ("pp. " if many else "p. ") + p


def _norm_authors(authors) -> list[dict]:
    out = []
    for a in authors or []:
        if isinstance(a, str):
            a = {"organisation": a} if " " in a.strip() and "," not in a else {"surname": a}
        out.append(a)
    return out


def _is_org(a: dict) -> bool:
    return not _blank(a.get("organisation"))


def _org_name(a: dict, with_acronym=True) -> str:
    name = a["organisation"].strip()
    acr = (a.get("acronym") or "").strip()
    return f"{name} [{acr}]" if (acr and with_acronym) else name


def author_list(authors, with_acronym=True) -> str:
    """Reference-list form: 'Crauder, B, Evans, B, Johnson, J & Noell, A'."""
    names = []
    for a in _norm_authors(authors):
        if _is_org(a):
            names.append(_org_name(a, with_acronym))
        else:
            ini = _initials(a.get("initials", ""))
            names.append(f"{a['surname'].strip()}, {ini}" if ini else a["surname"].strip())
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


def _editor_list(editors) -> str:
    names = []
    for e in _norm_authors(editors):
        if _is_org(e):
            names.append(e["organisation"].strip())
        else:
            ini = _initials(e.get("initials", ""))
            names.append(f"{ini} {e['surname'].strip()}".strip())  # initials BEFORE surname
    if not names:
        return ""
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " & " + names[-1]
    return f"{joined} ({'ed.' if len(names) == 1 else 'eds'})"


def _viewed(f: dict) -> str:
    v = f.get("viewed") or ""
    if not v:
        d = date.today()
        v = f"{d.day} {d.strftime('%B %Y')}"
    return v


def _viewed_url(f: dict) -> str | None:
    if _blank(f.get("url")):
        return None
    return f"viewed {_e(_viewed(f))} &lt;{_e(f['url'].strip())}&gt;"


# --------------------------------------------------------------------------- in-text
def _surname_for_text(a: dict, first_use: bool) -> str:
    if _is_org(a):
        acr = (a.get("acronym") or "").strip()
        if acr and not first_use:
            return acr  # acronym only after the first citation
        return _org_name(a, with_acronym=first_use)
    return a["surname"].strip()


def in_text(f: dict, source_type: str, first_use: bool = True) -> dict:
    """Return parenthetical and narrative in-text citations (HTML)."""
    year = _e(f.get("year") or "n.d.")
    authors = _norm_authors(f.get("authors"))
    page = f.get("quote_page") or None
    loc = f", {_page_label(page)}" if page else ""
    title = f.get("title") or ""

    if source_type == "legislation":
        j = (f.get("jurisdiction") or "").strip()
        core = f"{_i(title)} {year}" + (f" ({_e(j)})" if j else "")
        return {"parenthetical": f"({core})", "narrative": core}
    if source_type == "case_law":
        core = f"{_i(title)} [{year}] {_e(f.get('court', ''))}".strip()
        return {"parenthetical": f"({core})", "narrative": core}
    if source_type == "treaty":
        core = f"{_i(title)} {year}"
        return {"parenthetical": f"({core})", "narrative": core}
    if source_type in {"film", "broadcast"} and not authors:
        return {"parenthetical": f"({_i(title)} {year})", "narrative": f"{_i(title)} ({year})"}
    if source_type == "software" and not authors:
        return {"parenthetical": f"({_e(title)} {year}" + (f", version {_e(f['version'])}" if f.get("version") else "") + ")",
                "narrative": f"{_e(title)} ({year}" + (f", version {_e(f['version'])}" if f.get("version") else "") + ")"}

    if not authors:  # title replaces author, in italics
        name_p = name_n = _i(title) if title else "Unknown"
        return {"parenthetical": f"({name_p} {year}{loc})", "narrative": f"{name_n} ({year}{loc})"}

    n = len(authors)
    if n >= 4:
        name_p = name_n = _e(_surname_for_text(authors[0], first_use)) + " et al."
    elif n == 1:
        name_p = name_n = _e(_surname_for_text(authors[0], first_use))
    else:
        names = [_e(_surname_for_text(a, first_use)) for a in authors]
        name_p = ", ".join(names[:-1]) + " & " + names[-1]
        name_n = ", ".join(names[:-1]) + " and " + names[-1]
    return {"parenthetical": f"({name_p} {year}{loc})", "narrative": f"{name_n} ({year}{loc})"}


# --------------------------------------------------------------------------- entries
def _lead(f: dict, t: str) -> tuple[str, bool]:
    """Author-year lead. Returns (markup, used_title_as_author)."""
    year = _e(f.get("year") or "n.d.")
    authors = f.get("authors")
    if t == "film":  # film entries lead with the title
        return f"{_i(f['title'])} {year}" + (f" [{_e(f.get('medium') or 'film')}]"), True
    if authors:
        return f"{_e(author_list(authors))} {year}", False
    if t == "software":
        return f"{_i(f.get('title', ''))} {year}", True
    title = f.get("title", "")
    lead_title = _i(title) if t in ITALIC_TITLE else _q(title)
    return f"{lead_title} {year}", True


def format_entry(source_type: str, f: dict) -> str:
    t = source_type
    if t not in SOURCE_TYPES:
        raise ValueError(f"Unknown source_type '{t}'. Use one of: {sorted(SOURCE_TYPES)}")

    # ---- legal sources have their own simple templates
    if t == "legislation":
        j = (f.get("jurisdiction") or "").strip()
        return f"{_i(f['title'])} {_e(f.get('year', ''))}" + (f" ({_e(j)})" if j else "")
    if t == "case_law":
        return f"{_i(f['title'])} [{_e(f.get('year', ''))}] {_e(f.get('court', ''))}".strip()
    if t == "treaty":
        return f"{_i(f['title'] + (' (' + f['abbreviation'] + ')' if f.get('abbreviation') else ''))} {_e(f.get('year', ''))}"

    lead, title_used = _lead(f, t)
    parts: list[str] = []
    title = f.get("title", "")
    medium = f.get("medium") or DEFAULT_MEDIUM.get(t)
    ed = _ordinal(f.get("edition"))
    pages = f.get("pages")
    page_txt = _page_label(pages) if not _blank(pages) else None
    vurl = _viewed_url(f)
    if t in ONLINE_TYPES and vurl is None and not _blank(f.get("url")):
        vurl = None
    publisher = f.get("publisher")
    city = f.get("city")

    def add(x):
        if not _blank(x):
            parts.append(x)

    if t in {"book", "ebook"}:
        if not title_used:
            add(_i(title))
        add(_e(ed) if ed else None)
        add(_e(publisher) if publisher else None)
        add(_e(city) if (city and t == "book") else None)
        add(vurl if (t == "ebook" or f.get("online")) else None)
    elif t == "book_chapter":
        add(_q(title) if not title_used else None)
        eds = _editor_list(f.get("editors"))
        add(f"in {_e(eds)}" if eds else None)
        add(_i(f.get("container", "")) if f.get("container") else None)
        add(_e(ed) if ed else None)
        add(_e(publisher) if publisher else None)
        add(_e(city) if city else None)
        add(_e(page_txt) if page_txt else None)
        add(vurl if f.get("online") or f.get("url") else None)
    elif t == "journal_article":
        add(_q(title) if not title_used else None)
        add(_i(f.get("container", "")) if f.get("container") else None)
        add(f"vol. {_e(f['volume'])}" if f.get("volume") else None)
        add(f"no. {_e(f['issue'])}" if f.get("issue") else None)
        add(_e(page_txt) if page_txt else None)
        add(vurl)
    elif t == "news_article":
        add(_q(title) if not title_used else None)
        add(_i(f.get("container", "")) if f.get("container") else None)
        add(_e(f.get("day_month", "")) if f.get("day_month") else None)
        add(_e(page_txt) if page_txt else None)
        add(vurl)
    elif t in {"report", "standard"}:
        if not title_used:
            add(_i(title))
        add(_e(f["report_number"]) if f.get("report_number") else None)
        add(_e(publisher) if publisher else None)
        add(vurl)
    elif t == "conference_paper":
        add(_q(title) if not title_used else None)
        add(_i(f.get("container", "")) if f.get("container") else None)
        add(_e(publisher) if publisher else None)
        add(_e(f["location"]) if f.get("location") else None)
        add(_e(page_txt) if page_txt else None)
        add(vurl)
    elif t == "conference_proceedings":
        add(_i(title) if not title_used else None)
        add(_e(publisher) if publisher else None)
        add(_e(f["location"]) if f.get("location") else None)
        add(_e(f["day_month"]) if f.get("day_month") else None)
        add(vurl)
    elif t == "course_material":
        add(_q(title) if not title_used else None)
        add(_i(f["container"]) if f.get("container") else None)
        add(_e(publisher) if publisher else None)
        add(_e(f["day_month"]) if f.get("day_month") else None)
    elif t in {"webpage"}:
        if not title_used:
            add(_i(title))
        add(_e(publisher) if publisher else None)
        add(vurl)
    elif t == "social_media":
        if not title_used:
            add(_i(title))
        add(_e(publisher) if publisher else None)
        add(_e(f["day_month"]) if f.get("day_month") else None)
        add(vurl)
    elif t in {"video", "audio", "image", "dataset", "software"}:
        if not title_used:
            add(f"{_i(title)} [{_e(medium)}]")
        else:  # software with no author already led with the title
            lead += f" [{_e(medium)}]"
        if t == "software" and f.get("version"):
            add(f"version {_e(f['version'])}")
        add(_e(publisher) if publisher else None)
        add(vurl)
    elif t == "brochure":
        if not title_used:
            add(f"{_i(title)} [{_e(medium)}]")
        add(_e(publisher) if publisher else None)
        add(_e(city) if city else None)
    elif t == "broadcast":
        if not title_used:
            add(f"{_i(title)} [{_e(medium)}]")
        add(_e(publisher) if publisher else None)
        add(_e(city) if city else None)
        add(_e(f["day_month"]) if f.get("day_month") else None)
    elif t == "film":
        add(_e(publisher) if publisher else None)
        add(_e(city) if city else None)

    # Entries whose lead is the title (no author) join with a plain space, per the guide.
    sep_lead = ", " if parts else ""
    return lead + sep_lead + ", ".join(parts)


def missing_fields(source_type: str, f: dict) -> list[str]:
    miss = []
    for key in REQUIRED.get(source_type, []):
        if _blank(f.get(key)):
            miss.append(key)
    if "year" in miss:
        miss.remove("year")  # n.d. is acceptable, reported separately
    return miss


def format_reference(source_type: str, fields: dict, first_use: bool = True) -> dict:
    """Build the reference-list entry and in-text citations for one source."""
    t = (source_type or "").strip().lower().replace(" ", "_").replace("-", "_")
    f = dict(fields or {})
    missing = missing_fields(t, f)  # computed before any placeholder is inserted
    if _blank(f.get("title")):
        f["title"] = TITLE_PLACEHOLDER  # never print empty quotes: make the gap impossible to miss
    entry = format_entry(t, f)
    entry_html = entry.rstrip(".") + ("" if t in {"legislation", "case_law", "treaty"} else ".")
    notes = []
    if _blank(f.get("year")) and t not in {"legislation", "case_law", "treaty"}:
        notes.append("No publication date found: 'n.d.' used.")
    if _blank(f.get("authors")) and t not in {"legislation", "case_law", "treaty", "film", "software", "broadcast"}:
        notes.append("No author found: the title is used in the author position.")
    if t == "social_media" and f.get("private"):
        notes.append("Private posts, emails and blogs are personal communication: cite in-text only.")
    cit = in_text(f, t, first_use=first_use)
    heading = {"legislation": "Legislation", "treaty": "Legislation", "case_law": "Case law"}.get(t)
    return {
        "source_type": t,
        "reference_html": entry_html,
        "reference_text": to_plain(entry_html),
        "in_text_parenthetical_html": cit["parenthetical"],
        "in_text_parenthetical": to_plain(cit["parenthetical"]),
        "in_text_narrative_html": cit["narrative"],
        "in_text_narrative": to_plain(cit["narrative"]),
        "list_heading": heading,
        "missing_fields": missing,
        "notes": notes,
    }
