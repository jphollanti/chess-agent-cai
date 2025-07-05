import json
import time
import io
import logging
import chess.pgn

from stockfish import Stockfish
from config import (
    STOCKFISH_PATH,
    EVAL_DROP_THRESHOLD,
    ANALYSED_GAMES_FILE,
    RAW_GAMES_FILE,
)

logging.basicConfig(level=logging.INFO)

def init_stockfish():
    return Stockfish(
        path=STOCKFISH_PATH,
        parameters={
            "Threads": 2,
            "Minimum Thinking Time": 30,
        },
    )


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


def load_pgns_from_file(path):
    with open(path, "r") as f:
        return json.load(f)


def save_analysis(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logging.info(f"Saved analysis to {path}")

def main():
    logging.info("Loading PGNs...")
    pgns = load_pgns_from_file(RAW_GAMES_FILE)
    my_stockfish = init_stockfish()

    output = []
    for i, pgn in enumerate(pgns):
        try:
            logging.info(f"Analyzing game {i + 1}/{len(pgns)}...")
            output.append(analyze_pgn(pgn, my_stockfish))
        except Exception as e:
            logging.error(f"Error analyzing game {i + 1}: {e}")

    save_analysis(output, ANALYSED_GAMES_FILE)


if __name__ == "__main__":
    main()