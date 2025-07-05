import os
import json
import logging
import requests
from datetime import datetime, timedelta
import calendar
from dateutil import parser

from config import (
    GAMES_ARCHIVE_FILE,
    CHESSCOM_USERNAME,
    GAMES_TO_ANALYSE,
    GAMES_ARCHIVE_GET_MONTHS,
)

HEADERS = {
    "User-Agent": "chess-analyzer-script/1.0 (+https://github.com/your-github)"
}

logging.basicConfig(level=logging.INFO)


def fetch_stats():
    url = f"https://api.chess.com/pub/player/{CHESSCOM_USERNAME}/stats"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        logging.warning(f"Failed to fetch Chess.com stats for {CHESSCOM_USERNAME} return code {response.status_code}")
        raise RuntimeError(f"Failed to fetch Chess.com stats for {CHESSCOM_USERNAME}")

    data = response.json()

    fields = [
        "fide", "lessons", "chess_daily", "chess_rapid",
        "chess_blitz", "chess_bullet", "chess960_daily"
    ]

    stats = {}
    for field in fields:
        stats[field] = data.get(field, None)

    return stats

def fetch_archives():
    """Fetch archive URLs for all past months for a given user."""
    url = f"https://api.chess.com/pub/player/{CHESSCOM_USERNAME}/games/archives"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()["archives"]

def fetch_games_from_url(url):
    """Fetch games from a specific Chess.com archive URL."""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("games", [])

def fetch_recent_games(months_back=GAMES_ARCHIVE_GET_MONTHS):
    if not CHESSCOM_USERNAME:
        raise ValueError("CHESSCOM_USERNAME is not set in config or .env")

    archives = fetch_archives()
    archives.sort(reverse=True)

    cutoff_date = datetime.now() - timedelta(days=30 * months_back)
    all_recent_games = []
    username_lower = CHESSCOM_USERNAME.lower()

    for archive_url in archives:
        try:
            games = fetch_games_from_url(archive_url)
        except Exception as e:
            logging.warning(f"Failed to fetch from {archive_url}: {e}")
            continue

        for game in games:
            pgn = game.get("pgn")
            if not pgn:
                continue

            white = game.get("white", {}).get("username", "").lower()
            black = game.get("black", {}).get("username", "").lower()
            if white != username_lower and black != username_lower:
                continue

            end_time = game.get("end_time")
            if end_time:
                game_datetime = datetime.fromtimestamp(end_time)
                if game_datetime < cutoff_date:
                    continue  # Skip older games

            all_recent_games.append(game)

    os.makedirs(os.path.dirname(GAMES_ARCHIVE_FILE), exist_ok=True)
    with open(GAMES_ARCHIVE_FILE, "w") as f:
        json.dump(all_recent_games, f, indent=2)

    print(f"\nSaved {len(all_recent_games)} games to {GAMES_ARCHIVE_FILE}")
    return all_recent_games


def main():
    if not CHESSCOM_USERNAME:
        raise ValueError("CHESSCOM_USERNAME is not set in config or .env")

    print(f"\nFetching last {GAMES_TO_ANALYSE} lost games for {CHESSCOM_USERNAME}")
    lost_pgns = extract_lost_games(GAMES_TO_ANALYSE)

    os.makedirs(os.path.dirname(GAMES_ARCHIVE_FILE), exist_ok=True)

    with open(GAMES_ARCHIVE_FILE, "w") as f:
        json.dump(lost_pgns, f, indent=2)

    print(f"\nSaved {len(lost_pgns)} lost games to {GAMES_ARCHIVE_FILE}")


if __name__ == "__main__":
    #main()
    print("\nFetching games for profile building...")
    fetch_recent_games(months_back=3)
