"""Check the formatter against worked examples printed in the Kaplan Harvard guide (v4.0)."""
from referencer.formatters import format_reference

P = lambda a: [{"surname": s, "initials": i} for s, i in a]


def ref(t, **f):
    return format_reference(t, f)["reference_text"]


def test_book():
    assert ref("book", authors=P([("Robbins", "SP")]), year="2016",
               title="Management: the essentials", edition="3", publisher="Pearson Australia",
               city="Melbourne") == "Robbins, SP 2016, Management: the essentials, 3rd edn, Pearson Australia, Melbourne."


def test_first_edition_omitted():
    assert "edn" not in ref("book", authors=P([("A", "B")]), year="2020", title="T", edition="1",
                            publisher="P", city="C")


def test_journal_library():
    assert ref("journal_article", authors=P([("Fazel", "M")]), year="2015",
               title="A moment of change: facilitating children's mental health",
               container="International Journal of Educational Development", volume="41",
               issue="3", pages="255-261") == (
        "Fazel, M 2015, ‘A moment of change: facilitating children's mental health’, "
        "International Journal of Educational Development, vol. 41, no. 3, pp. 255-261.")


def test_journal_online_five_authors():
    out = ref("journal_article",
              authors=P([("Kennedy", "G"), ("Judd", "T"), ("Churchward", "A"), ("Gray", "K"), ("Krause", "K")]),
              year="2008", title="First year students' experiences with technology",
              container="Australasian Journal of Educational Technology", volume="24", issue="1",
              pages="108–122", viewed="29 September 2021",
              url="http://www.ascilite.org.au/ajet/ajet24/kennedy")
    assert out.startswith("Kennedy, G, Judd, T, Churchward, A, Gray, K & Krause, K 2008,")
    assert out.endswith("pp. 108-122, viewed 29 September 2021 <http://www.ascilite.org.au/ajet/ajet24/kennedy>.")


def test_chapter_editor_initials_first():
    out = ref("book_chapter", authors=P([("Gregory", "J")]), year="2008",
              title="Journeying across colonial landscapes",
              editors=P([("Mayne", "A")]), container="Beyond the Black Stump",
              publisher="Wakefield Press", city="Kent Town", pages="211-237")
    assert out == ("Gregory, J 2008, ‘Journeying across colonial landscapes’, in A Mayne (ed.), "
                   "Beyond the Black Stump, Wakefield Press, Kent Town, pp. 211-237.")


def test_news_online():
    out = ref("news_article", authors=P([("Rayner", "G")]), year="2020",
              title="Boris Johnson sets out three-step plan", container="The Telegraph",
              day_month="10 May", viewed="17 August 2021", url="https://www.telegraph.co.uk/x")
    assert out == ("Rayner, G 2020, ‘Boris Johnson sets out three-step plan’, The Telegraph, "
                   "10 May, viewed 17 August 2021 <https://www.telegraph.co.uk/x>.")


def test_report_org_acronym():
    out = ref("report", authors=[{"organisation": "Department of Health and Aged Care", "acronym": "DHAC"}],
              year="2018", title="National women's health policy 2018", report_number="REP 6151",
              publisher="Australian Government", viewed="15 March 2020", url="https://health.gov.au/r")
    assert out == ("Department of Health and Aged Care [DHAC] 2018, National women's health policy 2018, "
                   "REP 6151, Australian Government, viewed 15 March 2020 <https://health.gov.au/r>.")


def test_video():
    assert ref("video", authors=P([("Freirer", "S")]), year="2017", title="The power of play",
               publisher="YouTube", viewed="16 April 2021", url="https://youtube.com/x") == (
        "Freirer, S 2017, The power of play [online video], YouTube, viewed 16 April 2021 <https://youtube.com/x>.")


def test_legal():
    assert ref("legislation", title="Bankruptcy Act", year="1966", jurisdiction="Cth") == "Bankruptcy Act 1966 (Cth)"
    assert ref("case_law", title="Polias v Ryall", year="2015", court="NSWSC") == "Polias v Ryall [2015] NSWSC"
    assert ref("treaty", title="Convention of the Rights of the Child", abbreviation="CRC",
               year="1990") == "Convention of the Rights of the Child (CRC) 1990"


def test_film():
    assert ref("film", title="Sunday too far away", year="1975", publisher="South Australian Film Corporation",
               city="Adelaide") == "Sunday too far away 1975 [film], South Australian Film Corporation, Adelaide."


def test_in_text_rules():
    f = lambda n: format_reference("journal_article", dict(
        authors=P([(f"S{k}", "A") for k in range(n)]), year="2019", title="t", container="j"))
    assert f(1)["in_text_parenthetical"] == "(S0 2019)"
    assert f(2)["in_text_parenthetical"] == "(S0 & S1 2019)"
    assert f(2)["in_text_narrative"] == "S0 and S1 (2019)"
    assert f(3)["in_text_parenthetical"] == "(S0, S1 & S2 2019)"
    assert f(4)["in_text_parenthetical"] == "(S0 et al. 2019)"


def test_in_text_page_and_org_first_use():
    r = format_reference("report", dict(authors=[{"organisation": "Department of Health and Aged Care", "acronym": "DHAC"}],
                                        year="2021", title="x", quote_page="16"))
    assert r["in_text_parenthetical"] == "(Department of Health and Aged Care [DHAC] 2021, p. 16)"
    r2 = format_reference("report", dict(authors=[{"organisation": "Department of Health and Aged Care", "acronym": "DHAC"}],
                                         year="2021", title="x"), first_use=False)
    assert r2["in_text_parenthetical"] == "(DHAC 2021)"


def test_no_author_and_no_date():
    r = format_reference("webpage", dict(title="Cretaceous", publisher="Wikipedia", viewed="1 May 2024",
                                         url="https://x.org"))
    assert r["reference_text"].startswith("Cretaceous n.d., Wikipedia, viewed 1 May 2024")
    assert r["in_text_parenthetical"] == "(Cretaceous n.d.)"
    assert any("n.d." in n for n in r["notes"]) and any("No author" in n for n in r["notes"])


def test_initials_normalised():
    r = ref("book", authors=[{"surname": "Smith", "initials": "J. K."}], year="2020", title="T", publisher="P")
    assert r.startswith("Smith, JK 2020")


def test_html_has_italics_and_escapes():
    r = format_reference("book", dict(authors=P([("A", "B")]), year="2020", title="R&D <basics>", publisher="P"))
    assert "<i>R&amp;D &lt;basics&gt;</i>" in r["reference_html"]
    assert r["reference_text"] == "A, B 2020, R&D <basics>, P."


def test_missing_title_shows_placeholder_not_empty_quotes():
    r = format_reference("journal_article", dict(
        authors=P([("Tu", "H"), ("Xia", "Y"), ("Tse", "CK"), ("Chen", "X")]), year="2020",
        container="IEEE Access", volume="8", pages="114876-114883"))
    assert "‘’" not in r["reference_text"]
    assert "[title not found]" in r["reference_text"]
    assert "title" in r["missing_fields"]
