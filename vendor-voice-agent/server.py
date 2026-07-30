import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.twiml.voice_response import Connect, VoiceResponse

import llm
import memory
from config import OWNER_PHONE_NUMBER, PUBLIC_BASE_URL, TWILIO_AUTH_TOKEN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vendor_voice_agent")

validator = RequestValidator(TWILIO_AUTH_TOKEN) if TWILIO_AUTH_TOKEN else None
WS_BASE_URL = PUBLIC_BASE_URL.replace("https://", "wss://").replace("http://", "ws://")


@asynccontextmanager
async def lifespan(app: FastAPI):
    memory.init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


async def _validate_twilio_request(request: Request) -> bool:
    if not validator:
        logger.warning("TWILIO_AUTH_TOKEN not set — skipping webhook signature validation.")
        return True
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    return validator.validate(str(request.url), dict(form), signature)


@app.post("/voice/incoming")
async def voice_incoming(request: Request):
    if not await _validate_twilio_request(request):
        return Response(status_code=403)

    response = VoiceResponse()
    connect = Connect(action=f"{PUBLIC_BASE_URL}/voice/relay-ended")
    connect.conversation_relay(url=f"{WS_BASE_URL}/voice/relay")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@app.post("/voice/relay-ended")
async def voice_relay_ended(request: Request):
    if not await _validate_twilio_request(request):
        return Response(status_code=403)

    form = await request.form()
    handoff_raw = form.get("HandoffData")
    response = VoiceResponse()

    if handoff_raw:
        try:
            handoff = json.loads(handoff_raw)
        except json.JSONDecodeError:
            handoff = {}
        reason = handoff.get("reason", "a vendor call needs your attention")
        response.say(f"Connecting you now. Heads up: {reason}")
        response.dial(OWNER_PHONE_NUMBER)
    else:
        response.hangup()

    return Response(content=str(response), media_type="application/xml")


@app.websocket("/voice/relay")
async def voice_relay(websocket: WebSocket):
    await websocket.accept()

    conversation: list[dict] = []
    system_prompt = ""
    vendor_phone = None
    call_sid = None
    escalated = False
    escalation_reason = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")

            if msg_type == "setup":
                call_sid = msg["callSid"]
                vendor_phone = msg["from"]
                vendor_row = memory.get_or_create_vendor(vendor_phone)
                vendor_name = vendor_row["name"]
                history = memory.recent_calls_for_vendor(vendor_phone)
                history_summaries = [row["summary"] for row in history if row["summary"]]
                system_prompt = llm.build_system_prompt(vendor_name, history_summaries)

                greeting = (
                    f"Hi {vendor_name}, thanks for calling back."
                    if vendor_name
                    else "Hi, thanks for calling. How can I help you today?"
                )
                await _send_text(websocket, greeting)
                conversation.append({"role": "assistant", "content": greeting})

            elif msg_type == "prompt":
                if not msg.get("last", True):
                    continue
                user_text = msg.get("voicePrompt", "")
                if not user_text:
                    continue
                conversation.append({"role": "user", "content": user_text})

                reply, escalate, reason = llm.get_reply(system_prompt, conversation)
                conversation.append({"role": "assistant", "content": reply})
                await _send_text(websocket, reply)

                if escalate:
                    escalated = True
                    escalation_reason = reason
                    await _send_end(websocket, reason)
                    break

            elif msg_type == "interrupt":
                logger.info("Caller interrupted: %s", msg.get("utteranceUntilInterrupt"))

            elif msg_type == "error":
                logger.error("ConversationRelay error: %s", msg.get("description"))
                break

    except WebSocketDisconnect:
        pass
    finally:
        if vendor_phone and conversation:
            _finalize_call(vendor_phone, call_sid, conversation, escalated, escalation_reason)


async def _send_text(websocket: WebSocket, text: str):
    await websocket.send_text(json.dumps({"type": "text", "token": text, "last": True}))


async def _send_end(websocket: WebSocket, reason: str | None):
    handoff = json.dumps({"reasonCode": "live-agent-handoff", "reason": reason or "Escalation requested"})
    await websocket.send_text(json.dumps({"type": "end", "handoffData": handoff}))


def _finalize_call(vendor_phone, call_sid, conversation, escalated, escalation_reason):
    transcript_text = "\n".join(f"{turn['role']}: {turn['content']}" for turn in conversation)

    summary, important = llm.summarize_call(transcript_text)
    if escalated:
        important = True

    memory.save_call(
        vendor_phone=vendor_phone,
        call_sid=call_sid,
        transcript=transcript_text,
        summary=summary,
        important=important,
        escalated=escalated,
        escalation_reason=escalation_reason,
    )

    flag = "IMPORTANT" if important else "routine"
    logger.info("Call finished [%s] from %s: %s", flag, vendor_phone, summary)
