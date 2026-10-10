"""Gemini via HTTPS. It interprets/summarises; SQLite remains the evidence authority."""
import json
import logging
import re
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from pydantic import BaseModel, Field
from ..config import get_settings
from .query_parser import ParsedQuery, parse_query

log=logging.getLogger(__name__)
OBJECTS={"dog","backpack","handbag","bag","phone","bicycle","car","bottle"}
RELATIONSHIPS={"carrying","holding","with","wearing","next_to","riding"}
ACTIONS={"walk","run","riding","wave"}
COLOURS={"black","white","red","blue","green","yellow","orange","pink","purple","brown","gray","dark_green","dark_blue"}

class GeminiConstraints(BaseModel):
    subject_class: str = "person"
    gender: str | None = None
    upper_type: str | None = None
    upper_color: str | None = None
    lower_type: str | None = None
    lower_color: str | None = None
    object_class: str | None = None
    relationship: str | None = None
    action: str | None = None
    intent: str = "find"  # find | count | describe
    explanation: str = ""

class GeminiAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=400)

def _json_response(prompt: str, schema: dict) -> dict:
    settings=get_settings()
    model=_resolve_model(settings.gemini_api_key,settings.gemini_model)
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0,"responseMimeType":"application/json","responseSchema":schema}}
    request=Request(url,data=json.dumps(payload).encode("utf-8"),headers={"Content-Type":"application/json","x-goog-api-key":settings.gemini_api_key},method="POST")
    try:
        with urlopen(request,timeout=25) as response: data=json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail=exc.read().decode("utf-8",errors="replace")
        raise RuntimeError(f"Gemini API HTTP {exc.code}: {detail[:500]}") from exc
    except URLError as exc: raise RuntimeError(f"Gemini API connection failed: {exc.reason}") from exc
    text=data["candidates"][0]["content"]["parts"][0]["text"]
    text=re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$","",text.strip(),flags=re.I)
    return json.loads(text)

@lru_cache(maxsize=4)
def _resolve_model(api_key: str, configured_model: str) -> str:
    """Use the configured model when permitted, else pick an accessible Flash model."""
    url="https://generativelanguage.googleapis.com/v1beta/models"
    request=Request(url,headers={"x-goog-api-key":api_key},method="GET")
    try:
        with urlopen(request,timeout=15) as response: data=json.loads(response.read().decode("utf-8"))
        models=data.get("models",[])
        supported=[]
        for model in models:
            methods=model.get("supportedGenerationMethods") or model.get("supportedActions") or []
            name=str(model.get("name","")).removeprefix("models/")
            if name and ("generateContent" in methods or not methods): supported.append(name)
        if configured_model in supported: return configured_model
        for preferred in ("gemini-3.5-flash-lite","gemini-3.5-flash","gemini-2.5-flash","gemini-2.0-flash"):
            if preferred in supported:
                log.warning("[GEMINI] configured model %s unavailable; using accessible model %s",configured_model,preferred)
                return preferred
        if supported: return supported[0]
        raise RuntimeError("No Gemini model with generateContent access was returned for this API key.")
    except HTTPError as exc:
        detail=exc.read().decode("utf-8",errors="replace")
        raise RuntimeError(f"Unable to list Gemini models (HTTP {exc.code}): {detail[:500]}") from exc
    except URLError as exc: raise RuntimeError(f"Unable to list Gemini models: {exc.reason}") from exc

def configured() -> bool:
    settings=get_settings()
    return settings.gemini_enabled and bool(settings.gemini_api_key)

def _fallback_info(text: str, reason: str) -> dict:
    is_count=bool(re.search(r"\b(how many|count|number of)\b",text.lower()))
    return {"provider":"rules","used":False,"intent":"count" if is_count else "find","reason":reason}

def _colour(value: str | None) -> str | None:
    value=(value or "").lower().strip().replace(" ", "_").replace("-", "_")
    return value if value in COLOURS else None

def interpret(text: str) -> tuple[ParsedQuery, dict]:
    """Translate language to constraints, or fall back safely to the local parser."""
    fallback=parse_query(text)
    if not configured(): return fallback,_fallback_info(text,"Gemini is not configured")
    try:
        prompt=("Convert this CCTV forensic search question into JSON constraints. Do not claim an event exists. "
                "Allowed objects: dog, backpack, handbag, bag, phone, bicycle, car, bottle. "
                "Allowed relationships: carrying, holding, with, wearing, next_to, riding. "
                "Allowed actions: walk, run, riding, wave. Set intent to count for questions asking how many; "
                "otherwise use find or describe. Unknown fields must be null. "
                f"Question: {text}")
        value=GeminiConstraints.model_validate(_json_response(prompt,GeminiConstraints.model_json_schema()))
        parsed=ParsedQuery(subject_class="object" if value.subject_class=="object" else "person",gender=value.gender if value.gender in {"male","female"} else None,upper_type=value.upper_type,upper_color=_colour(value.upper_color),lower_type=value.lower_type,lower_color=_colour(value.lower_color),object_class=value.object_class if value.object_class in OBJECTS else None,relationship=value.relationship if value.relationship in RELATIONSHIPS else None,action=value.action if value.action in ACTIONS else None,start_seconds=fallback.start_seconds,end_seconds=fallback.end_seconds)
        return parsed,{"provider":"gemini","used":True,"intent":value.intent if value.intent in {"find","count","describe"} else "find","explanation":value.explanation}
    except Exception as exc:
        log.warning("[GEMINI] query interpretation failed; using local parser: %s",exc)
        return fallback,_fallback_info(text,"Gemini was unavailable; local parser used")

def answer(query: str, primary: dict | None, results: list[dict], intent: str = "find") -> dict:
    """Produce a concise answer strictly from the selected indexed evidence."""
    if not primary:
        return {"text":"No verified evidence found for this query.","provider":"evidence"}
    track_ids={result["track_id"] for result in results if result.get("track_id") is not None}
    object_observations=sum(1 for result in results if result.get("track_id") is None)
    facts={"intent":intent,"event":primary.get("event"),"timestamp_seconds":primary.get("evidence_timestamp"),"evidence_start_seconds":primary.get("evidence_start"),"evidence_end_seconds":primary.get("evidence_end"),"confidence":primary.get("confidence"),"reasons":primary.get("match_reasons",[]),"verified_result_rows":len(results),"distinct_person_tracks":len(track_ids),"object_frame_observations":object_observations}
    fallback=(f"The video contains {len(track_ids)} distinct tracked person{'s' if len(track_ids)!=1 else ''} matching this question." if intent=="count" and track_ids else f"Verified evidence found for “{query}” at {primary.get('evidence_timestamp',0):.2f} seconds.")
    if not configured(): return {"text":fallback,"provider":"evidence"}
    try:
        prompt=("Answer the investigator's question in one concise sentence, using ONLY the JSON evidence below. "
                "Do not add facts, do not overstate an association as carrying/riding, and mention uncertainty if relevant. "
                "For a person-count question, report distinct_person_tracks exactly; do not count frames. "
                "For objects, object_frame_observations are observations, not a unique-object count. "
                f"Question: {query}\nEvidence: {json.dumps(facts)}")
        value=GeminiAnswer.model_validate(_json_response(prompt,GeminiAnswer.model_json_schema()))
        return {"text":value.answer,"provider":"gemini"}
    except Exception as exc:
        log.warning("[GEMINI] evidence answer failed; using deterministic answer: %s",exc)
        return {"text":fallback,"provider":"evidence"}
