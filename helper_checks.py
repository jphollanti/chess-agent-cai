import json
from datetime import datetime
from config import (
    GAMES_ARCHIVE_FILE,
)

def find_oldest_and_latest_games(games):
    if not games:
        print("No games provided.")
        return None, None

    # Sort games by end_time
    sorted_games = sorted(games, key=lambda g: g.get("end_time", 0))

    oldest = sorted_games[0]
    latest = sorted_games[-1]

    print("Oldest game:")
    print(f"  URL: {oldest['url']}")
    print(f"  End time: {datetime.utcfromtimestamp(oldest['end_time'])} UTC")

    print("\nLatest game:")
    print(f"  URL: {latest['url']}")
    print(f"  End time: {datetime.utcfromtimestamp(latest['end_time'])} UTC")

    return oldest, latest
:
if __name__ == "__main__":
    with open(GAMES_ARCHIVE_FILE, "r") as f:
        game_data = json.load(f)

    find_oldest_and_latest_games(game_data)
