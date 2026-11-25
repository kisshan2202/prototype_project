# Kaplan Harvard referencing rules (condensed from the Kaplan Harvard Style Guide v4.0, Feb 2023)

Source: `Kaplan_Referencing_Harvard_Style_Guide_2024.pdf` in this folder. This file is a
condensed transcription used as the agent's instructions. The deterministic formatter in
`referencer/formatters.py` implements the same rules in code.

## General rules
- Two parts: an in-text citation and a reference-list entry. Entries are sorted alphabetically
  by first author's surname / organisation (ignore A / An / The when sorting by title).
- Reference entry format: `Surname, Initials Year, Title, details.` Initials have no full stops.
  No comma between author and year. Several authors: `A, B, C & D` – ampersand before the last.
- Titles use sentence case: capitalise only the first word, the first word after a colon is NOT
  capitalised, and proper nouns keep their capitals. (Newspaper/magazine titles use capitals
  on major words.)
- Italics: book / report / website / video / dataset / software titles, journal and newspaper
  titles, conference name. Single quotation marks: article, chapter, conference-paper titles.
- Edition only for 2nd or later editions: `3rd edn`. Volume `vol.`, issue `no.`, pages `p.` / `pp.`
- No date: `n.d.`  No author: use the title in the author position.
- Organisation as author: full name, acronym in square brackets: `Department of Health and
  Aged Care [DHAC] 2018`. If publisher = author, the acronym is used as the publisher.
- Online sources: `viewed 5 January 2021 <URL>` (day month year, URL in angle brackets).
- Private posts, emails and private blogs are personal communication: in-text only, not listed.
- PDFs and downloadable content online follow the report / journal / legal rules, not the website rule.

## In-text citation
- 1 author: (Fazel 2015) / Fazel (2015). With quote add page: (Fazel 2015, p. 260); pp. for ranges.
- 2–3 authors: (Ingram & Derdak 2019) in brackets; `Ingram and Derdak (2019)` in the sentence.
- 4 or more authors: first surname + et al.: (Haslam et al. 2013).
- Organisation: first use `(Department of Health and Aged Care [DHAC] 2021)`, afterwards `(DHAC 2021)`.
- No author: title in italics (*Cretaceous* 2011).
- Same author and year: 2015a, 2015b (by alphabetical order of title).
- Secondary source: (Donato cited in Cotterall & Cohen 2003); only the source actually read is listed.
- Legislation: (*Bankruptcy Act* 1966 (Cth) sch. 2). Case: (*R v Ramage* [2004] VSC 508).
- Video / audio: timestamp hh:mm:ss in place of page.

## Entry templates (online variant adds `viewed <date> <URL>`)
| Source type | Template |
|---|---|
| Book | `Author Year, *Title: subtitle*, edition, Publisher, City.` |
| eBook | `Author Year, *Title: subtitle*, edition, Publisher, viewed D Month YYYY <URL>.` |
| Chapter in edited book | `Author Year, 'Chapter title', in I Editor (ed.), *Book title*, edition, Publisher, City, pp. x-y.` (editor initials BEFORE surname; `ed.` one editor, `eds` several) |
| Journal article | `Author Year, 'Article title', *Journal Title*, vol. 1, no. 2, pp. 3-4[, viewed D Month YYYY <URL>].` |
| Newspaper / magazine | `Author Year, 'Article title', *Newspaper Title*, D Month, pp. x-y[, viewed ... <URL>].` |
| Report | `Author/Org [ACR] Year, *Report title*, Report number, Publisher[, viewed ... <URL>].` |
| Professional standard | `Org [ACR] Year, *Title of standard*, Standard number, Publisher, viewed ... <URL>.` |
| Conference paper | `Author Year, 'Paper title', *Conference name*, Organiser, Location, pp. x-y, viewed ... <URL>.` |
| Conference proceedings | `Author Year, *Conference name*, Organiser, Location, D Month, viewed ... <URL>.` |
| Kaplan course material | `Kaplan School [ACR] Year, 'Title of material', *COURSECODE: Course name*, Publisher, D Month.` |
| Website / webpage | `Author/Org [ACR] Year, *Webpage title*, Publisher, viewed D Month YYYY <URL>.` |
| Social media / blog | `Author Year, *Title of post*, Platform, D Month, viewed ... <URL>.` |
| Online video | `Author/username Year, *Title* [online video], Host, viewed ... <URL>.` |
| Podcast / audio | `Author Year, *Title* [podcast], Host, viewed ... <URL>.` |
| Online image / table / chart | `Author Year, *Title* [image], Publisher, viewed ... <URL>.` |
| Data | `Author Year, *Title* [electronic dataset], Publisher, viewed ... <URL>.` |
| Software / app | `Author Year, *Name* [software], version x, Publisher, viewed ... <URL>.` |
| Brochure / poster / pamphlet | `Author Year, *Title* [flyer], Publisher, City.` |
| TV / radio broadcast | `Presenter Year, *Title* [television broadcast], Broadcaster, City, D Month.` |
| Film / DVD | `*Title* Year [film], Producer, City.` |
| Legislation (list under heading `Legislation`) | `*Title of Act* Year (Cth)` – jurisdictions: Cth, ACT, NSW, NT, Qld, SA, Tas, Vic, WA |
| Case law (list under heading `Case law`) | `*Name of case* [Year] CourtIdentifier` e.g. `*Polias v Ryall* [2015] NSWSC` |
| Treaty (list under `Legislation`) | `*Treaty title (ABBR)* Year` |

## Worked examples from the guide
- Book: Robbins, SP 2016, *Management: the essentials*, 3rd edn, Pearson Australia, Melbourne.
- Chapter: Gregory, J 2008, 'Journeying across colonial landscapes: portable housing in nineteenth century Australia', in A Mayne (ed.), *Beyond the Black Stump: histories of outback Australia*, Wakefield Press, Kent Town, pp. 211-237.
- Journal: Fazel, M 2015, 'A moment of change: facilitating children's mental health', *International Journal of Educational Development*, vol. 41, no. 3, pp. 255-261.
- Online journal: Kennedy, G, Judd, T, Churchward, A, Gray, K & Krause, K 2008, 'First year students' experiences with technology: are they really digital natives?', *Australasian Journal of Educational Technology*, vol. 24, no. 1, pp. 108-122, viewed 29 September 2021 <http://www.ascilite.org.au/ajet/ajet24/kennedy>.
- Newspaper online: Rayner, G 2020, 'Boris Johnson sets out three-step plan to end lockdown on long road to freedom', *The Telegraph*, 10 May, viewed 17 August 2021 <https://www.telegraph.co.uk/politics/2020/05/10/go-back-work-boris-johnson>.
- Report: Department of Health and Aged Care [DHAC] 2018, *National women's health policy 2018*, REP 6151, Australian Government, viewed 15 March 2020 <https://health.gov.au/reports_REP6151>.
- Website: Hockey, J 2020, *Australia steps towards the next financial market*, Australian Government, viewed 5 January 2021 <https://...>.
