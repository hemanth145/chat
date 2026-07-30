# Vendor Voice Agent

An AI phone agent that answers your Google Voice number's vendor calls, handles
routine questions, remembers vendors across calls, and escalates (transfers +
notifies) you when something needs a human. Built on Twilio ConversationRelay +
Claude.

## How it works

1. A vendor calls your Google Voice number, which forwards to a Twilio number.
2. Twilio requests `/voice/incoming`, which connects the call to ConversationRelay.
3. ConversationRelay streams the conversation as text to this server's WebSocket
   (`/voice/relay`); Twilio handles speech-to-text and text-to-speech.
4. The agent looks the caller up by phone number in a local SQLite database, answers
   from `business_info.md` plus any past-call summaries, and replies.
5. If the topic needs you, the agent ends the ConversationRelay session with a
   handoff reason, and `/voice/relay-ended` dials `OWNER_PHONE_NUMBER` to bring you
   in live.
6. After every call (escalated or not), the agent generates a short summary and
   logs it, flagged `IMPORTANT` or `routine`.

## One-time account setup (you do this — outside this repo)

1. **Twilio account**: sign up at twilio.com and buy a phone number.
2. **ConversationRelay onboarding**: in the Twilio Console, complete the
   ConversationRelay onboarding steps and agree to the Predictive/Generative AI
   addendum (required before the `<ConversationRelay>` TwiML noun will work).
3. **Google Voice forwarding**: in Google Voice → Settings → Linked numbers, add
   your new Twilio number as a forwarding destination, and turn off "press 1 to
   accept" call screening for that linked number (it will break automated
   forwarding otherwise).
4. **Anthropic API key**: get one at console.anthropic.com.
5. Point the Twilio number's "A call comes in" webhook (Console → Phone Numbers →
   your number → Voice Configuration) at `https://<your-public-url>/voice/incoming`.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` (API keys, your real phone number, public URL) and fill in
`business_info.md` with your actual hours/policies/FAQs.

For local development you need a public HTTPS URL pointing at this server — use
ngrok:

```bash
ngrok http 8000
```

Copy the `https://...ngrok-free.app` URL ngrok gives you into `PUBLIC_BASE_URL`
in `.env`, and into the Twilio number's webhook (step 5 above).

Run the server:

```bash
uvicorn server:app --reload --port 8000
```

Call your Google Voice number to test end-to-end.

## Deploying

Any host that supports long-lived WebSocket connections works (Railway, Render,
Fly.io, a VPS). Set the same environment variables from `.env` in your host's
config, and update `PUBLIC_BASE_URL` and the Twilio webhook to your real domain
once deployed.

## Current limitations / next steps

- **Notifications**: call summaries are currently logged server-side only (check
  your host's logs). Wiring an actual SMS/email alert (e.g. via Twilio SMS or
  SendGrid) is a natural next step — ask to add it once you know how you want to
  be notified.
- **Latency**: replies are generated as one full response per turn rather than
  streamed token-by-token. Fine for a first version; can be optimized later if
  responses feel slow.
- **WebSocket signature validation**: the HTTP webhooks (`/voice/incoming`,
  `/voice/relay-ended`) validate Twilio's signature; the WebSocket endpoint does
  not yet. Low risk for a personal single-number setup, but worth hardening
  before wider use.
- **TCPA**: this setup only answers inbound calls, so outbound-calling consent
  rules don't apply. If you later add the agent *placing* calls to vendors, revisit
  consent requirements first.
