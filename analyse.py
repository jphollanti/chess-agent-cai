import json
import time
import io
import logging
import chess.pgn

from stockfish import Stockfish
from config import (
    STOCKFISH_PATH,
    EVAL_DROP_THRESHOLD,
    GAMES_ANALYSED_FILE,
    GAMES_ARCHIVE_FILE,
    ECO_OPENINGS_PATH,
)

logging.basicConfig(level=logging.INFO)

eco_db = {}


def init_stockfish():
    return Stockfish(
        path=STOCKFISH_PATH,
        parameters={
            "Threads": 2,
            "Minimum Thinking Time": 30,
        },
    )

def init_eco_db():
    # Load ECO opening map based on FEN → name/ECO
    global eco_db
    for fname in [
        "ecoA.json", "ecoB.json", "ecoC.json",
        "ecoD.json", "ecoE.json", "eco_interpolated.json"
    ]:
        with open(f"{ECO_OPENINGS_PATH}/{fname}") as f:
            eco_db.update(json.load(f))

def get_opening_from_eco(pgn_str):
    try:
        global eco_db
        if len(eco_db) == 0:
            init_eco_db()

        game = chess.pgn.read_game(io.StringIO(pgn_str))
        board = game.board()
        opening = None

        for move in game.mainline_moves():
            board.push(move)
            fen_key = board.fen()  # now using all 6 fields
            if fen_key in eco_db:
                rec = eco_db[fen_key]
                opening = f"{rec['eco']} - {rec['name']}"

        return opening or "Unknown"
    except Exception as e:
        return f"Error: {e}"

def evaluate_game(pgn, stockfish):
    """Evaluate each move of a game using Stockfish and track evaluations."""
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Invalid PGN: failed to parse")

    board = game.board()
    evaluations = {"white": [], "black": []}

    for idx, move in enumerate(game.mainline_moves()):
        board.push(move)
        side_just_moved = "black" if board.turn == chess.WHITE else "white"

        stockfish.set_fen_position(board.fen())
        evaluation = stockfish.get_evaluation()
        if not evaluation:
            raise RuntimeError(f"Stockfish returned no evaluation at move {idx+1}")

        evaluations[side_just_moved].append({
            "move_number": idx + 1,
            "evaluation": evaluation
        })

    return evaluations


def find_significant_dips(evals, threshold=EVAL_DROP_THRESHOLD):
    """Detect large drops in evaluation scores."""
    dips = []

    for i in range(1, len(evals)):
        prev = evals[i - 1]["evaluation"]
        curr = evals[i]["evaluation"]

        if prev["type"] == "cp" and curr["type"] == "cp":
            delta = curr["value"] - prev["value"]
            if abs(delta) >= threshold:
                dips.append({
                    "move_number": evals[i]["move_number"],
                    "score_before": prev["value"],
                    "score_after": curr["value"],
                    "delta": delta
                })
        elif prev["type"] == "mate" or curr["type"] == "mate":
            dips.append({
                "move_number": evals[i]["move_number"],
                "score_before": prev,
                "score_after": curr,
                "delta": "mate involved"
            })

    return dips


def analyze_pgn(pgn, stockfish):
    """Process a single PGN game into structured analysis."""
    evals = evaluate_game(pgn, stockfish)
    white_dips = find_significant_dips(evals["white"])
    black_dips = find_significant_dips(evals["black"])

    game = chess.pgn.read_game(io.StringIO(pgn))
    headers = game.headers

    return {
        "pgn": pgn.strip(),
        "result": headers.get("Result", "*"),
        "time_control": headers.get("TimeControl", ""),
        "white": headers.get("White", ""),
        "white_elo": int(headers.get("WhiteElo", 0)),
        "black": headers.get("Black", ""),
        "black_elo": int(headers.get("BlackElo", 0)),
        "termination": headers.get("Termination", ""),
        "white_dips": white_dips,
        "black_dips": black_dips
    }


def load_from_file(path):
    with open(path, "r") as f:
        return json.load(f)


def save_analysis(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"\nSaved analysis to {path}")

def main():
    print("\nLoading PGNs...")
    pgns = load_from_file(GAMES_ARCHIVE_FILE)
    my_stockfish = init_stockfish()

    output = []
    for i, pgn in enumerate(pgns):
        try:
            print(f"\nAnalyzing game {i + 1}/{len(pgns)}...")
            output.append(analyze_pgn(pgn, my_stockfish))
        except Exception as e:
            logging.error(f"Error analyzing game {i + 1}: {e}")

    save_analysis(output, GAMES_ANALYSED_FILE)


if __name__ == "__main__":
    main()