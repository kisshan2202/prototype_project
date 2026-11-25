"""Web server: serves the UI and a JSON endpoint that runs the ADK agent.

POST /api/reference  {"url": "https://..."}  ->  {reference_text, reference_html, in_text_*, ...}
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, HttpUrl

from referencer.agent import root_agent

APP_NAME = "kbs_referencer"
WEB = Path(__file__).parent / "web"

app = FastAPI(title="KBS Harvard Referencer")
sessions = InMemorySessionService()
runner = Runner(app_name=APP_NAME, agent=root_agent, session_service=sessions)


class Req(BaseModel):
    url: HttpUrl


@app.get("/healthz")
def healthz():
    return {"ok": True, "model": root_agent.model}


@app.post("/api/reference")
async def reference(req: Req):
    sid = uuid.uuid4().hex  # one throwaway session per request: no student data is retained
    await sessions.create_session(app_name=APP_NAME, user_id="web", session_id=sid)
    msg = types.Content(role="user", parts=[types.Part(text=f"Create a reference for this URL: {req.url}")])

    result, error, final_text = None, None, ""
    try:
        async for event in runner.run_async(user_id="web", session_id=sid, new_message=msg):
            for fr in event.get_function_responses():
                if fr.name == "format_reference" and fr.response:
                    payload = fr.response.get("result", fr.response)
                    if isinstance(payload, dict) and "error" not in payload:
                        result = payload
                    elif isinstance(payload, dict):
                        error = payload["error"]
                elif fr.name == "fetch_source" and fr.response and fr.response.get("error"):
                    error = fr.response["error"]
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(p.text or "" for p in event.content.parts)
    except Exception as exc:  # model/quota/credential problems
        raise HTTPException(502, f"The AI model call failed: {exc}") from exc
    finally:
        await sessions.delete_session(app_name=APP_NAME, user_id="web", session_id=sid)

    if result is None:
        raise HTTPException(422, error or final_text or "Could not build a reference from that URL.")
    return {**result, "url": str(req.url), "assistant_note": final_text}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
