import os
import json
import time
import logging
from pathlib import Path
from collections import defaultdict

import requests
from dotenv import load_dotenv
from groq import Groq

# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_AGENT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

BASE_URL = "https://api.whatsapp.com/agent/v1"

STATE_FILE = Path("agent_state.json")
MAX_HISTORY_MESSAGES = 20

SYSTEM_PROMPT = """
You are a helpful AI assistant communicating through WhatsApp.

Rules:
- Be friendly, helpful, and conversational.
- Keep responses concise and easy to read on a phone.
- Use plain text unless formatting is helpful.
- Ask clarifying questions when necessary.
- Never claim to have performed an action you did not perform.
- If you do not know something, say so honestly.
"""

if not WHATSAPP_TOKEN:
    raise RuntimeError("Missing WHATSAPP_AGENT_TOKEN in .env")

if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY in .env")


# ============================================================
# CLIENTS
# ============================================================

groq_client = Groq(api_key=GROQ_API_KEY)

http = requests.Session()
http.headers.update({
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
})

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("whatsapp-agent")


# ============================================================
# STATE
# ============================================================

def load_state():
    if STATE_FILE.exists():
        try:
            with STATE_FILE.open("r", encoding="utf-8") as f:
                state = json.load(f)

            state.setdefault("offset", 0)
            state.setdefault("processed_ids", [])
            return state

        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not load saved state: %s", exc)

    return {
        "offset": 0,
        "processed_ids": [],
    }


state = load_state()

# Skip old messages when starting for the first time.
# The API retains updates for up to 30 days.
START_TIME = int(time.time())

processed_ids = set(state["processed_ids"])

# Each WhatsApp user gets a separate conversation history.
conversations = defaultdict(list)


def save_state():
    state["processed_ids"] = list(processed_ids)[-2000:]

    temporary_file = STATE_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as f:
        json.dump(state, f)

    temporary_file.replace(STATE_FILE)


# ============================================================
# WHATSAPP API
# ============================================================

def get_updates():
    """Long-poll WhatsApp for incoming messages and receipts."""

    response = http.get(
        f"{BASE_URL}/updates",
        params={
            "offset": state["offset"],
            "limit": 50,
            "timeout": 25,
        },
        timeout=35,
    )

    if response.status_code == 204:
        # No updates. Keep the existing offset.
        return None

    if response.status_code == 429:
        raise RuntimeError("WhatsApp polling rate limit reached")

    response.raise_for_status()

    return response.json()


def mark_read(message_id):
    """Mark an incoming message as read and show typing."""

    try:
        response = http.post(
            f"{BASE_URL}/statuses",
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id,
                "typing_indicator": {
                    "type": "text"
                },
            },
            timeout=15,
        )

        if response.status_code not in (200, 429, 503):
            logger.warning(
                "Could not mark message as read: HTTP %s",
                response.status_code,
            )

    except requests.RequestException as exc:
        logger.warning("Read receipt failed: %s", exc)


def send_message(recipient_id, text):
    """Send a text reply through the WhatsApp Agent Platform."""

    response = http.post(
        f"{BASE_URL}/messages",
        json={
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "text",
            "text": {
                "body": text[:4096]
            },
        },
        timeout=45,
    )

    if response.status_code == 429:
        raise RuntimeError("WhatsApp sending rate limit reached")

    response.raise_for_status()

    result = response.json()

    message_id = result.get("messages", [{}])[0].get("id")

    logger.info(
        "Reply sent to %s; message ID: %s",
        recipient_id,
        message_id,
    )

    return message_id


# ============================================================
# GROQ AI
# ============================================================

def generate_reply(user_id, user_message):
    """Generate an AI reply with per-user conversation history."""

    history = conversations[user_id]

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        *history,
        {
            "role": "user",
            "content": user_message,
        },
    ]

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=600,
    )

    answer = response.choices[0].message.content

    if not answer:
        answer = "Sorry, I couldn't generate a response."

    # Update conversation memory.
    history.extend([
        {
            "role": "user",
            "content": user_message,
        },
        {
            "role": "assistant",
            "content": answer,
        },
    ])

    # Keep recent messages to control token usage.
    if len(history) > MAX_HISTORY_MESSAGES:
        del history[:-MAX_HISTORY_MESSAGES]

    return answer


# ============================================================
# MESSAGE PROCESSING
# ============================================================

def extract_messages(payload):
    """Extract messages from the documented update structure."""

    messages = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages.extend(value.get("messages", []))

    return messages


def process_message(message):
    message_id = message.get("id")

    if not message_id:
        logger.warning("Received a message without an ID.")
        return False

    if message_id in processed_ids:
        return True

    sender = message.get("from", "")
    timestamp = int(message.get("timestamp", "0"))
    message_type = message.get("type", "")

    # Only reply to WhatsApp users, not agent identifiers.
    if not sender.startswith("user:"):
        processed_ids.add(message_id)
        save_state()
        return True

    # Do not automatically answer messages from before startup.
    if timestamp and timestamp < START_TIME:
        logger.info("Skipping old message: %s", message_id)
        processed_ids.add(message_id)
        save_state()
        return True

    # Reactions are receive-only and shouldn't trigger replies.
    if message_type == "reaction":
        processed_ids.add(message_id)
        save_state()
        return True

    if message_type != "text":
        answer = (
            "Thanks for your message! I can currently process "
            "text messages only. Please send your question as text."
        )
    else:
        user_text = message.get("text", {}).get("body", "").strip()

        if not user_text:
            processed_ids.add(message_id)
            save_state()
            return True

        logger.info("Incoming message from %s", sender)

        mark_read(message_id)

        try:
            answer = generate_reply(sender, user_text)

        except Exception as exc:
            logger.error("Groq generation failed: %s", exc)

            # Don't mark the message processed; the next poll
            # can retry it.
            return False

    try:
        send_message(sender, answer)

    except Exception as exc:
        logger.error("WhatsApp reply failed: %s", exc)

        # Don't mark the message processed if sending failed.
        return False

    processed_ids.add(message_id)
    save_state()

    return True


# ============================================================
# MAIN POLLING LOOP
# ============================================================

def main():
    logger.info("WhatsApp + Groq agent starting.")
    logger.info("Model: %s", GROQ_MODEL)
    logger.info("API: %s", BASE_URL)
    logger.info("Starting offset: %s", state["offset"])

    backoff = 2

    while True:
        try:
            payload = get_updates()

            if payload is None:
                # HTTP 204: retain the existing offset.
                backoff = 2
                continue

            messages = extract_messages(payload)

            for message in messages:
                success = process_message(message)

                if not success:
                    # Retry this update later rather than
                    # advancing past an unanswered message.
                    raise RuntimeError(
                        "Message processing failed; retrying."
                    )

            # Use WhatsApp's next_offset exactly as documented.
            next_offset = payload.get("next_offset")

            if next_offset is not None:
                state["offset"] = int(next_offset)
                save_state()

            backoff = 2

        except KeyboardInterrupt:
            logger.info("Agent stopped by user.")
            break

        except Exception as exc:
            logger.error("%s", exc)
            logger.info("Retrying in %s seconds.", backoff)

            time.sleep(backoff)
            backoff = min(backoff * 2, 60)


if __name__ == "__main__":
    main()
