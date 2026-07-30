import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
OWNER_PHONE_NUMBER = os.environ["OWNER_PHONE_NUMBER"]
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"].rstrip("/")
DB_PATH = os.environ.get("DB_PATH", "vendor_agent.db")

BUSINESS_INFO = (BASE_DIR / "business_info.md").read_text(encoding="utf-8")
