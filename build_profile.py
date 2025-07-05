import json
import time
import io
import logging
import chess.pgn
from collections import defaultdict, Counter
import os
import chess.pgn
import requests

from stockfish import Stockfish
from config import (
    GAMES_ARCHIVE_FILE,
    PROFILE_FILE,
    PROFILE_INFO,
    CHESSCOM_USERNAME,
    GAMES_ANALYSE_MAX,
    GAMES_ANALYSED_FILE,
)

from analyse import (
    analyze_pgn,
    load_pgns_from_file,
    init_stockfish,
    save_analysis,
    get_opening_from_eco,
)

from get_from_chesscom import fetch_stats

HEADERS = {
    "User-Agent": "chess-analyzer-script/1.0 (+https://github.com/your-github)"
}


def select_representative_games(analyzed_games, max_per_category=5):
    categorized = {"win": [], "loss": [], "draw": []}

    def game_score(game):
        # More dips = worse; fewer = cleaner performance
        is_white = game["white"].lower() == CHESSCOM_USERNAME.lower()
        dips = game["white_dips"] if is_white else game["black_dips"]
        return len(dips)

    for game in analyzed_games:
        result = game.get("result")
        if result == "1/2-1/2":
            categorized["draw"].append((game, game_score(game)))
        elif result == "1-0":
            categorized["win" if game["white"].lower() == CHESSCOM_USERNAME.lower() else "loss"].append((game, game_score(game)))
        elif result == "0-1":
            categorized["loss" if game["white"].lower() == CHESSCOM_USERNAME.lower() else "win"].append((game, game_score(game)))

    # Sort each category and select top samples
    result_sample = {}
    for category, games in categorized.items():
        sorted_games = sorted(games, key=lambda x: x[1])  # sort by score
        result_sample[category] = [g[0]["pgn"] for g in sorted_games[:max_per_category]]

    return result_sample

def build_player_profile(analyzed_games):
    """Generate a player profile from analyzed games."""
    opening_stats = defaultdict(lambda: {"wins": 0, "losses": 0, "games": 0})
    won_games = []
    lost_games = []
    opening_counter = Counter()

    for game in analyzed_games:
        headers = chess.pgn.read_game(io.StringIO(game["pgn"])).headers
        opening = get_opening_from_eco(game["pgn"])
        result = game["result"]
        white = game["white"]
        black = game["black"]

        # Determine outcome from player's perspective
        is_white = white.lower() == CHESSCOM_USERNAME.lower()
        win = (result == "1-0" and is_white) or (result == "0-1" and not is_white)
        loss = (result == "0-1" and is_white) or (result == "1-0" and not is_white)

        opening_stats[opening]["games"] += 1
        if win:
            opening_stats[opening]["wins"] += 1
            won_games.append(game["pgn"])
        elif loss:
            opening_stats[opening]["losses"] += 1
            lost_games.append(game["pgn"])

        opening_counter[opening] += 1
    
    style = analyze_style(analyzed_games)

    profile = {
        "most_played_openings": opening_counter.most_common(5),
        # "opening_stats": opening_stats,
        "samples": select_representative_games(analyzed_games),
        "total_games": len(analyzed_games),
        "style": style,
        "chess_com_stats": fetch_stats(),
        "profile_in_own_words": PROFILE_INFO
    }

    os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(profile, f, indent=2)

    logging.info(f"Saved player profile to {PROFILE_FILE}")

def parse_time_control(tc):
    # Returns (base, increment)
    try:
        if "+" in tc:
            base, inc = map(int, tc.split("+"))
        else:
            base, inc = int(tc), 0
    except Exception:
        base, inc = 600, 0  # fallback default
    return base, inc

def is_time_trouble(game):
    tc = game.get("time_control", "600+0")
    base, increment = parse_time_control(tc)

    # Assume "time trouble" is only relevant if base time is short
    if base >= 900:  # e.g. 15+0 = 900 seconds
        return False

    is_white = game["white"].lower() == CHESSCOM_USERNAME.lower()
    my_dips = game["white_dips"] if is_white else game["black_dips"]

    # Look for *2 or more* major blunders after game has progressed far enough
    big_late_blunders = [
        d for d in my_dips
        if isinstance(d["delta"], int) and abs(d["delta"]) > 150 and d["move_number"] >= 60
    ]

    return len(big_late_blunders) >= 2

def analyze_style(analyzed_games):
    """Heuristically determine the player's style from evaluation patterns."""
    style_profile = {
        "aggressive": 0,
        "positional": 0,
        "tactical": 0,
        "defensive": 0,
        "time_trouble_prone": 0,
    }

    for game in analyzed_games:
        total_dips = len(game["white_dips"]) + len(game["black_dips"])
        termination = game.get("termination", "").lower()
        time_control = game.get("time_control", "")
        base, _ = parse_time_control(time_control)
        late_game_threshold = 30 if base <= 600 else 50  # adjust based on base time

        # Who is the player?
        is_white = game["white"].lower() == CHESSCOM_USERNAME.lower()
        my_dips = game["white_dips"] if is_white else game["black_dips"]

        # Evaluate number and timing of dips
        big_blunders = [d for d in my_dips if isinstance(d["delta"], int) and abs(d["delta"]) > 150]

        # Tactical style: high-risk, high-reward
        if len(big_blunders) >= 3:
            style_profile["tactical"] += 1

        # Aggressive: sharp score changes, early eval swings
        if any(d["move_number"] <= 10 for d in big_blunders):
            style_profile["aggressive"] += 1

        # Positional: low number of dips, stable evaluations
        if len(my_dips) <= 2:
            style_profile["positional"] += 1

        # Defensive: games where player loses but hangs on
        if "timeout" in termination or "abandoned" in termination:
            style_profile["defensive"] += 1

        # Time trouble: blunders in later stages
        if is_time_trouble(game):
            style_profile["time_trouble_prone"] += 1

    # Normalize style rating out of number of games
    total_games = len(analyzed_games)
    for key in style_profile:
        style_profile[key] = round(style_profile[key] / total_games, 2)

    return style_profile


def build_player_profile_from_file():
    logging.info("Building full player profile...")
    
    pgns = load_pgns_from_file(GAMES_ARCHIVE_FILE)

    if str(GAMES_ANALYSE_MAX).lower() != 'all':
        try:
            max_games = int(GAMES_ANALYSE_MAX)
            pgns = pgns[:max_games]
            logging.warning(f"[DEBUG] Limiting analysis to {max_games} games.")
        except ValueError:
            logging.error(f"[ERROR] GAMES_ANALYSE_MAX is not a valid number: {GAMES_ANALYSE_MAX}")
            raise
    my_stockfish = init_stockfish()

    analyzed = []
    for i, game in enumerate(pgns):
        try:
            # The PGN might be inside a dict (chess.com full game JSON)
            if isinstance(game, dict) and "pgn" in game:
                pgn = game["pgn"]
            elif isinstance(game, str):
                pgn = game
            else:
                raise ValueError("Unknown game format")

            logging.info(f"Analyzing profile game {i + 1}/{len(pgns)}...")
            analyzed.append(analyze_pgn(pgn, my_stockfish))
        except Exception as e:
            logging.error(f"Error analyzing profile game {i + 1}: {e}")

    save_analysis(analyzed, GAMES_ANALYSED_FILE)
    build_player_profile(analyzed)


if __name__ == "__main__":
    build_player_profile_from_file() 