import asyncio

import pytest

from referencer import tools

HTML = b"""<html><head><title>Paper | Journal</title>
<meta name="citation_title" content="A moment of change">
<meta name="citation_author" content="Fazel, Mina">
<meta name="citation_doi" content="10.1016/j.ijedudev.2015.01.002">
<meta name="citation_publication_date" content="2015/03/01">
<script type="application/ld+json">{"@type":"ScholarlyArticle"}</script></head>
<body><nav>menu</nav><h1>A moment of change</h1><p>Body text.</p><footer>&copy; 2024 Publisher</footer></body></html>"""


def test_html_summary_extracts_citation_meta():
    s = tools._html_summary("https://example.org/a", HTML, "utf-8")
    assert s["meta"]["citation_title"] == ["A moment of change"]
    assert s["doi_hint"] == "10.1016/j.ijedudev.2015.01.002"
    assert "menu" not in s["text_excerpt"] and "Body text." in s["text_excerpt"]
    assert "ScholarlyArticle" in s["json_ld"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/", "http://169.254.169.254/latest", "ftp://example.org/x", "http://localhost:8080"])
def test_fetch_blocks_non_public(url):
    assert "error" in asyncio.run(tools.fetch_source(url))


def test_format_tool_rejects_unknown_type():
    assert "error" in tools.format_reference("poem", {})
