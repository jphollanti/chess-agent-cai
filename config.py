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

RAW_GAMES_FILE = DATA_DIR / "raw_games.json"
ANALYSED_GAMES_FILE = DATA_DIR / "analysed_games.json"
COACH_REPORT_FILE = DATA_DIR / "coach_report.txt"

# Profile
PROFILE_RAW_GAMES_FILE = DATA_DIR / "raw_games_profile.json"
PROFILE_ANALYSED_GAMES_FILE = DATA_DIR / "profile_analysed_games.json"
PROFILE_AMOUNT_OF_MONTHS = 3
PROFILE_ANALYSE_MAX_GAMES = 7
PROFILE_FILE = DATA_DIR / "player_profile.json"

OPENAI_MODEL = "gpt-4o-2024-05-13"  # gpt-4o-2024-05-13 = o3. Or use "gpt-4o" or another like "gpt-4-turbo"

EVAL_DROP_THRESHOLD = 150  # in centipawns
STOCKFISH_PARAMS = {
    "Threads": 2,
    "Minimum Thinking Time": 30
}

# Chess profile for coaching
PROFILE_INFO = os.getenv("PROFILE_INFO")