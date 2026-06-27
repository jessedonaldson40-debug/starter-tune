"""
STANDAILONE — AI Explainer module
=================================
Streams plain-English explanations of Tune Inspector findings from Claude Sonnet
4.6 via Server-Sent Events. Includes an in-memory LRU cache (max 64 entries)
keyed by finding code + engine context hash so repeat clicks replay cached
tokens instantly.

Public surface:
  - ExplainFindingRequest (pydantic)
  - register_routes(api_router)   ← attaches /inspector/findings/explain,
                                    /inspector/explain-cache/stats,
                                    /inspector/explain-cache (DELETE)

The router-attachment pattern keeps server.py thin (single include) while
allowing the explainer to evolve independently.
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections import OrderedDict
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class ExplainFindingRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    finding: dict[str, Any]
    profile_name: Optional[str] = None
    engine_metadata: Optional[dict[str, Any]] = None
    safety_envelope: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_EXPLAINER_SYSTEM = (
    "You are a senior calibration engineer working alongside a tuner using the "
    "STANDAILONE Starter Tune Engine. You will receive a single audit finding from "
    "the Tune Inspector along with engine metadata and the active safety envelope. "
    "Write a brief plain-English explanation aimed at an intermediate tuner: "
    "(1) what the finding means in 1–2 sentences, "
    "(2) why it matters mechanically (engine behaviour, risk), and "
    "(3) one concrete next step the tuner can take. "
    "Keep the entire response to 4–6 short sentences. Be precise, no hype, no emoji, "
    "no marketing language. Use plain ASCII only. Do not restate the finding verbatim."
)


def _build_prompt(req: ExplainFindingRequest) -> str:
    f = req.finding
    parts = [
        f"FINDING CODE: {f.get('code', 'UNKNOWN')}",
        f"SEVERITY: {f.get('severity', '')}",
        f"SUBSYSTEM: {f.get('subsystem', '')}",
        f"MESSAGE: {f.get('message', '')}",
        f"AUTOMATED REMEDIATION: {f.get('remediation', '')}",
    ]
    if f.get("cells"):
        parts.append(f"AFFECTED CELLS: {len(f['cells'])} cells in the 16x16 grid.")
    if req.engine_metadata:
        e = req.engine_metadata
        parts.append(
            f"ENGINE: {e.get('displacement_l')}L {e.get('cylinders')}cyl "
            f"{e.get('induction')} on {e.get('fuel_type')}, "
            f"target {e.get('target_hp')} hp, rev limit {e.get('rev_limit')} rpm, "
            f"injector {e.get('injector_cc')} cc, CR {e.get('compression_ratio')}."
        )
    if req.safety_envelope:
        s = req.safety_envelope
        parts.append(
            f"ENVELOPE: AFR {s.get('afr_min')}-{s.get('afr_max')}, "
            f"ignition ceiling {s.get('ignition_ceiling')} deg, "
            f"boost ceiling {s.get('boost_ceiling_kpa')} kPa, "
            f"knock {s.get('knock_sensitivity')}, thermal {s.get('thermal_risk')}."
        )
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# LRU cache (process-local, bounded)
# ---------------------------------------------------------------------------

_CACHE_MAX = 64
_cache: "OrderedDict[str, str]" = OrderedDict()


def _cache_key(req: ExplainFindingRequest) -> str:
    f = req.finding or {}
    ctx = {
        "code": f.get("code"),
        "message": f.get("message"),
        "remediation": f.get("remediation"),
        "engine": req.engine_metadata or {},
        "env": req.safety_envelope or {},
    }
    blob = json.dumps(ctx, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_put(key: str, value: str) -> None:
    if key in _cache:
        _cache.move_to_end(key)
    _cache[key] = value
    while len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

HEARTBEAT_EVERY = 8  # ping frame every N tokens


def register_routes(api_router: APIRouter) -> None:

    @api_router.post("/inspector/findings/explain")
    async def explain_finding(req: ExplainFindingRequest):
        """Streams the AI explanation back as Server-Sent Events.

        Includes an in-memory LRU cache keyed by finding code + engine context
        hash: repeat clicks replay cached tokens instantly without invoking the
        LLM. The cache holds up to 64 entries.
        """
        # Lazy import — keeps app import-time light and avoids loading the
        # emergentintegrations library unless an explanation is actually requested.
        from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            raise HTTPException(503, "EMERGENT_LLM_KEY not configured")

        key = _cache_key(req)
        cached = _cache.get(key)
        prompt = _build_prompt(req)

        async def event_stream():
            meta_cached = "true" if cached else "false"
            yield (
                "event: meta\n"
                f"data: {{\"model\":\"claude-sonnet-4-6\",\"cached\":{meta_cached}}}\n\n"
            )

            if cached:
                # Replay cached tokens in small chunks so the UI shows the streaming feel
                text = cached
                chunk = 32
                for i in range(0, len(text), chunk):
                    piece = text[i:i + chunk].replace("\r", "").replace("\n", "\\n")
                    yield f"event: token\ndata: {piece}\n\n"
                yield "event: done\ndata: end\n\n"
                return

            # Live LLM call — accumulate tokens for cache and emit periodic pings
            chat = LlmChat(
                api_key=api_key,
                session_id=f"finding-{req.finding.get('code', 'X')}-{uuid.uuid4().hex[:6]}",
                system_message=_EXPLAINER_SYSTEM,
            ).with_model("anthropic", "claude-sonnet-4-6")

            accumulated: list[str] = []
            token_count = 0

            try:
                async for ev in chat.stream_message(UserMessage(text=prompt)):
                    if isinstance(ev, TextDelta):
                        accumulated.append(ev.content)
                        safe = ev.content.replace("\r", "").replace("\n", "\\n")
                        yield f"event: token\ndata: {safe}\n\n"
                        token_count += 1
                        if token_count % HEARTBEAT_EVERY == 0:
                            yield "event: ping\ndata: keepalive\n\n"
                    elif isinstance(ev, StreamDone):
                        break
            except Exception as e:
                yield f"event: error\ndata: {str(e)[:200]}\n\n"

            full = "".join(accumulated).strip()
            if full:
                _cache_put(key, full)
            yield "event: done\ndata: end\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @api_router.get("/inspector/explain-cache/stats")
    async def explain_cache_stats() -> dict[str, Any]:
        return {"entries": len(_cache), "max": _CACHE_MAX}

    @api_router.delete("/inspector/explain-cache")
    async def explain_cache_clear() -> dict[str, Any]:
        n = len(_cache)
        _cache.clear()
        return {"cleared": n}
