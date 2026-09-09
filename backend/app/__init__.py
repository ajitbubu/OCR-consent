"""Load the repository .env before any module reads its configuration."""

from pathlib import Path

from dotenv import load_dotenv

# db.ROOT and the OCR provider settings are resolved at import time, so the
# file must be loaded here rather than inside main. Real environment variables
# win, keeping the documented inline `OCR_PROVIDER=... uvicorn ...` form working.
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
