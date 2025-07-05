import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHESSCOM_USERNAME = os.getenv("CHESSCOM_USERNAME")

ROOT_DIR = Path(__file__).parent
DATA_DIR = ROOT_DIR / "data"
ENGINE_DIR = ROOT_DIR / "engine" / "stockfish"
STOCKFISH_PATH = ENGINE_DIR / "stockfish-macos-m1-apple-silicon"

BOOK_PATH = ROOT_DIR / "book" / "gm2001.bin"
ECO_OPENINGS_PATH = ROOT_DIR / "eco_openings/"

GAMES_TO_ANALYSE = 10

GAMES_ARCHIVE_FILE = DATA_DIR / "games_archive.json"
GAMES_ARCHIVE_GET_MONTHS = 3
GAMES_ANALYSED_FILE = DATA_DIR / "games_analyzed.json"
GAMES_ANALYSE_MAX = 30
COACH_REPORT_FILE = DATA_DIR / "coach_report.txt"

# Profile
PROFILE_FILE = DATA_DIR / "profile.json"

LLM_PROVIDER = "local"
LLM_TEMPERATURE = 0.2

OPENAI_MODEL = "gpt-4o-2024-05-13"  # gpt-4o-2024-05-13 = o3. Or use "gpt-4o" or another like "gpt-4-turbo"

LOCAL_MODEL_NAME = "nous-hermes-2-mistral-7b-dpo"
LOCAL_API_BASE = "http://localhost:1234/v1"

EVAL_DROP_THRESHOLD = 150  # in centipawns
STOCKFISH_PARAMS = {
    "Threads": 2,
    "Minimum Thinking Time": 30
}

# Chess profile for coaching
PROFILE_INFO = os.getenv("PROFILE_INFO")