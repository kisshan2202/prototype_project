# KBS Harvard Referencer

Paste a URL (journal article page, web page, or PDF) and get a **Kaplan Harvard** reference-list
entry plus in-text citations, ready to copy. Built with **Google ADK** and **Gemini on Vertex AI**,
served by a small FastAPI app and deployed to **Cloud Run** from GitHub Actions.

Rules come from `guide/Kaplan_Referencing_Harvard_Style_Guide_2024.pdf` (v4.0).

## How it works

```
Browser (web/index.html)  --POST /api/reference {url}-->  server.py (FastAPI + ADK Runner)
                                                              |
                                              referencer/agent.py  (Gemini, ADK Agent)
                                                |-- fetch_source   download HTML/PDF, read citation_* / JSON-LD / text
                                                |-- lookup_doi     Crossref metadata (authoritative when a DOI exists)
                                                `-- format_reference  deterministic Kaplan Harvard formatter
```

- **Gemini reads and extracts** (source type, authors, title, journal, pages...).
- **Python formats** (`referencer/formatters.py`), so punctuation, italics, `&`, `et al.`, `n.d.`,
  `[ACRONYM]`, `viewed ... <URL>` always follow the guide exactly. Missing fields are flagged, never invented.
- 23 source types: books, chapters, journals, news, reports, standards, conferences, course material,
  web, social, video, audio, images, data, software, brochures, broadcasts, film, legislation, cases, treaties.

## Run locally

```bash
cd kbs-referencer
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env        # then edit; for Vertex AI also run: gcloud auth application-default login
set -a && source .env && set +a
python -m pytest -q         # formatter tests use examples printed in the guide
python server.py            # http://localhost:8080
adk web .                   # optional: ADK developer UI for the agent
```

The model defaults to `gemini-3.5-flash`; override with `REFERENCER_MODEL`.

## Deploy (GCP + GitHub Actions)

One-time setup in your GCP project (replace the placeholders):

```bash
PROJECT=your-project-id; REGION=us-central1; REPO=kisshan2202/prototype_project
gcloud services enable run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com iam.googleapis.com

# Deploy service account (used by GitHub Actions)
gcloud iam service-accounts create referencer-deploy
DEPLOY_SA=referencer-deploy@$PROJECT.iam.gserviceaccount.com
for r in run.admin cloudbuild.builds.editor artifactregistry.writer storage.admin iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$DEPLOY_SA --role=roles/$r; done

# Image repository for source deploys (the deploy account can write to it but not create it)
gcloud artifacts repositories create cloud-run-source-deploy --repository-format=docker --location=$REGION

# Let the Cloud Run runtime identity call Gemini
RUNTIME_SA=$(gcloud projects describe $PROJECT --format='value(projectNumber)')-compute@developer.gserviceaccount.com
gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:$RUNTIME_SA --role=roles/aiplatform.user

# Workload Identity Federation: GitHub repo -> deploy service account (no keys stored)
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc repo --location=global --workload-identity-pool=github \
  --issuer-uri=https://token.actions.githubusercontent.com \
  --attribute-mapping=google.subject=assertion.sub,attribute.repository=assertion.repository \
  --attribute-condition="assertion.repository=='$REPO'"
POOL=$(gcloud iam workload-identity-pools describe github --location=global --format='value(name)')
gcloud iam service-accounts add-iam-policy-binding $DEPLOY_SA --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/$POOL/attribute.repository/$REPO"
echo "GCP_WIF_PROVIDER = $POOL/providers/repo"; echo "GCP_DEPLOY_SA = $DEPLOY_SA"
```

Then in GitHub: **Settings -> Secrets and variables -> Actions -> Variables**, add
`GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WIF_PROVIDER`, `GCP_DEPLOY_SA` (and optionally `REFERENCER_MODEL`).
Some newer Gemini models are served only from the `global` location, not regional ones. If the app returns
`404 NOT_FOUND ... publishers/google/models/...`, test the model in each location (see below) and, if only
`global` works, add a `GEMINI_LOCATION` variable set to `global`. Cloud Run itself stays in `GCP_REGION`.
Merging to `main` runs the tests (`referencer-ci.yml`) and deploys (`referencer-deploy.yml`).

The service deploys with `--no-allow-unauthenticated`, so only people you grant `roles/run.invoker` can
open it. To make it public for students, add a login layer (e.g. IAP) first, because every request
costs a Gemini call and the fetch tool visits arbitrary URLs.

## Limits to know about

- Paywalled, login-only or JavaScript-rendered pages may not expose metadata; the app says so rather than guessing.
- The page's own metadata can be wrong. Students should confirm the result against the source and the guide.
- Titles are put in sentence case by the model; proper nouns can occasionally be missed.
- Not covered: secondary sources ("cited in"), multiple works by one author in the same year (2015a/b),
  and sorting a whole list. These are list-level rules the guide describes, easy to add next.
