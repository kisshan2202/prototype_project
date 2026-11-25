"""Web server: serves the UI and a JSON endpoint that runs the ADK agent.

POST /api/reference  {"url": "https://..."}  ->  {reference_text, reference_html, in_text_*, ...}
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, HttpUrl

from referencer.agent import root_agent
from referencer.ratelimit import RateLimiter

APP_NAME = "kbs_referencer"
WEB = Path(__file__).parent / "web"

app = FastAPI(title="KBS Harvard Referencer")
sessions = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=sessions)
# Every request costs a Gemini call: cap each visitor (0 turns the cap off).
limiter = RateLimiter(int(os.getenv("RATE_LIMIT_PER_HOUR", "20")))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "90"))


class Req(BaseModel):
    url: HttpUrl


def client_ip(request: Request) -> str:
    # Cloud Run appends the real client address last; earlier entries can be forged.
    xff = request.headers.get("x-forwarded-for", "")
    return xff.split(",")[-1].strip() if xff else (request.client.host if request.client else "unknown")


@app.get("/health")  # note: Cloud Run reserves /healthz, so it never reaches the app
def health():
    return {"ok": True, "model": root_agent.model}


@app.post("/api/reference")
async def reference(req: Req, request: Request):
    if not limiter.allow(client_ip(request)):
        raise HTTPException(429, "Too many requests from your connection. Please try again later.")
    sid = uuid.uuid4().hex  # one throwaway session per request: no student data is retained
    await sessions.create_session(app_name=APP_NAME, user_id="web", session_id=sid)
    msg = types.Content(role="user", parts=[types.Part(text=f"Create a reference for this URL: {req.url}")])

    result, error, final_text, fetch_failed = None, None, "", False
    try:
        async with asyncio.timeout(REQUEST_TIMEOUT):  # never leave the page spinning
            async for event in runner.run_async(user_id="web", session_id=sid, new_message=msg):
                for fr in event.get_function_responses():
                    if fr.name == "format_reference" and fr.response:
                        payload = fr.response.get("result", fr.response)
                        if isinstance(payload, dict) and "error" not in payload:
                            result = payload
                        elif isinstance(payload, dict):
                            error = payload["error"]
                    elif fr.name == "fetch_source" and fr.response and fr.response.get("error"):
                        error, fetch_failed = fr.response["error"], True
                if event.is_final_response() and event.content and event.content.parts:
                    final_text = "".join(p.text or "" for p in event.content.parts)
    except TimeoutError as exc:
        raise HTTPException(504, "This is taking too long: the site or the AI service is slow or busy. "
                                 "Please try again in a minute, or use the article's DOI link.") from exc
    except Exception as exc:  # model/quota/credential problems
        if "RESOURCE_EXHAUSTED" in str(exc) or "429" in str(exc)[:200]:
            raise HTTPException(503, "The AI service is busy right now (quota reached). "
                                     "Please wait a minute and try again.") from exc
        raise HTTPException(502, f"The AI model call failed: {exc}") from exc
    finally:
        await sessions.delete_session(app_name=APP_NAME, user_id="web", session_id=sid)

    if fetch_failed:  # the source was unreadable: any reference would be a guess
        result = None
    if result is None:
        # Never show the model's chat-style reply here: this page has no chat to answer it.
        raise HTTPException(422, error or "I couldn't read enough from that page to build a reference. "
                                         "Try the article's DOI link (https://doi.org/...) or a direct PDF link.")
    return {**result, "url": str(req.url), "assistant_note": final_text}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
