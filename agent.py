import os
import shutil
from pathlib import Path
import json
from langchain_openai import ChatOpenAI
from langchain_community.tools import Tool
from langchain.agents import initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_core.tools import tool
from pydantic import BaseModel
import logging
import warnings
from langchain_core._api import LangChainDeprecationWarning
import re
import markdown


# Suppress LangChainDeprecationWarnings
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)

from config import (
    CHESSCOM_USERNAME,
    LLM_PROVIDER,
    LLM_TEMPERATURE,
    LOCAL_API_BASE,
    LOCAL_MODEL_NAME,
    OPENAI_MODEL,
    OPENAI_API_KEY,
    PROFILE_FILE,
    GAMES_ANALYSED_FILE,
    GAMES_ARCHIVE_FILE,
    REVIEW_TEMPLATE_PATH,
    REVIEW_GAMES_OUTPUT_PATH,
)
from get_from_chesscom import fetch_recent_games
from build_profile import build_player_profile_from_file

# Optional: ensure logging
logging.basicConfig(level=logging.INFO)

class DummyInput(BaseModel):
    input: str

def extract_pgn_moves(pgn: str) -> str:
    """Strip metadata from PGN and keep only the move list."""
    # Remove tags like [Event "..."]
    no_metadata = re.sub(r"\[.*?\]\s*", "", pgn)

    # Remove result markers like "1-0", "0-1", "1/2-1/2" at the end
    clean = re.sub(r"\s*1-0|\s*0-1|\s*1/2-1/2\s*", "", no_metadata).strip()

    return clean

def get_llm():
    if LLM_PROVIDER == "openai":
        logging.info(f"Loading llm from: Open AI")
        return ChatOpenAI(
            openai_api_key = OPENAI_API_KEY,
            model = OPENAI_MODEL,
            temperature = LLM_TEMPERATURE,
        )
    else:  # Local LLM via LM Studio
        logging.info(f"Loading llm from: {LOCAL_API_BASE}")
        return ChatOpenAI(
            openai_api_key = "lm-studio",  # Dummy key
            openai_api_base = LOCAL_API_BASE,
            model = LOCAL_MODEL_NAME,
            temperature = LLM_TEMPERATURE,
        )

def slim_down_profile(profile):
    del profile["total_games"]
    del profile["chess_com_stats"]["fide"]
    del profile["chess_com_stats"]["lessons"]
    del profile["chess_com_stats"]["chess_daily"]
    profile["chess_com_stats"]["chess_rapid"] = {
        "rating": profile["chess_com_stats"]["chess_rapid"]["last"]["rating"]
    }
    profile["chess_com_stats"]["chess_blitz"] = {
        "rating": profile["chess_com_stats"]["chess_blitz"]["last"]["rating"]
    }
    del profile["chess_com_stats"]["chess_bullet"]
    del profile["chess_com_stats"]["chess960_daily"]
    return profile

def create_review_page(pgns: [], players: [], instructions: str, output_dir_name: str):
    template_dir = Path(REVIEW_TEMPLATE_PATH)
    output_dir = Path(REVIEW_GAMES_OUTPUT_PATH) / output_dir_name

    if os.path.exists(output_dir) and os.path.isdir(output_dir):
        shutil.rmtree(output_dir)

    # Create output dir if needed
    os.makedirs(output_dir, exist_ok=True)

    # Copy template files
    for filename in ["index.html", "dist.js"]:
        shutil.copy(template_dir / filename, output_dir / filename)

    # Load index.html and inject PGN + instructions
    index_path = output_dir / "index.html"
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    pgn_array_str = json.dumps(pgns, indent=2)
    players_array_str = json.dumps(players, indent=2)
    # Replace placeholders
    html = html.replace(
        'LLM Instructions go here',
        markdown.markdown(instructions)
    ).replace(
        "{PGN_ARRAY}",
        pgn_array_str
    ).replace(
        "{PLAYERS_ARRAY}",
        players_array_str
    )

    # Save updated HTML
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    return f"Review page created: {output_dir.resolve()}"

@tool(args_schema=DummyInput)
def analyze_recently_lost_games(input: str) -> str:
    """Analyze the last n lost games and provide coaching feedback."""

    try:
        with open(PROFILE_FILE, "r") as f:
            profile = json.load(f)
        
        # try to keep the prompt size low
        profile = slim_down_profile(profile)
        del profile["samples"]

        with open(GAMES_ANALYSED_FILE, "r") as f:
            all_games = json.load(f)
        
        lean_games = [
            {
                "pgn": extract_pgn_moves(g["pgn"]),
                "white": g.get("white"),
                "black": g.get("black"),
                "white_dips": g.get("white_dips"),
                "black_dips": g.get("black_dips"),
                "termination": g.get("termination"),
                "end_time": g.get("end_time"),
            }
            for g in all_games
        ]

        lost_games = [
            g for g in lean_games
            if not (f"{CHESSCOM_USERNAME} won" in g.get("termination"))
        ]
        lost_games.sort(key=lambda g: g.get("end_time"), reverse=True)
        # prompt length becomes an issue with local llm
        recent_losses = lost_games[:5]

        if not recent_losses:
            return "No lost games found to analyze."

        prompt = f"""
You're a chess coach AI helping me improve my play.

Below is a JSON array. Each element represents a game I lost recently. Each contains:
- "pgn": the full PGN of the game
- "eval_dips": significant drops in evaluation during the game. These dips are separated into "white" and "black" depending on which color made the mistake.

My username is {CHESSCOM_USERNAME}

Here's subset of my profile in chess.com: 
{json.dumps(profile)}

Please analyze the set of games as a whole and identify:
1. **Recurring mistakes** or themes across multiple games (e.g., hanging pieces, poor openings, tactical oversights).
2. **Phases of the game** where mistakes tend to occur (opening, middlegame, endgame).
3. **Suggestions for improvement** based on these patterns — not game-by-game advice, but overall priorities (e.g., study king safety, improve calculation in sharp positions).
4. If possible, categorize the dips (e.g., strategic, tactical, time-pressure blunders).

Here is the JSON data:
{json.dumps(recent_losses)}
"""
        
        llm = get_llm()
        response = llm.predict(prompt)

        # create review html
        pgns = []
        players = []
        for loss in recent_losses:
            pgns.append(loss["pgn"])
            players.append({
                'white': loss["white"],
                'black': loss["black"],
            })
        rp = create_review_page(pgns, players, response, "recent_losses")

        response += "\n\n" + rp

        return "Here's your coaching report:\n\n" + response
    except Exception as e:
        return f"Failed to analyze lost games: {str(e)}"

def ensure_profile_data():
    if not os.path.exists(GAMES_ARCHIVE_FILE):
        print("\nGames archive not found, fetching...")
        fetch_recent_games()
    else:
        print("Games archive already available.")

    if not os.path.exists(PROFILE_FILE):
        print("\nProfile not yet analyzed — analyzing now. This may take a while depending on the amount of games available...")
        build_player_profile_from_file()
    else:
        print("\nProfile already analyzed.")

@tool
def query_chess_profile(query: str) -> str:
    """Answer questions about your chess profile such as style, openings, or stats."""
    
    if not os.path.exists(PROFILE_FILE):
        return (
            "Your chess profile has not been built yet. "
            "Please run the 'update_player_profile' tool to generate it."
        )

    try:
        with open(PROFILE_FILE, "r") as f:
            profile = json.load(f)
    except Exception as e:
        return f"Error loading profile: {e}"
    
    # try to slim down the profile to fit in a local llm
    profile = slim_down_profile(profile)

    lean = []
    for s in profile["samples"]["win"]:
        lean.append(extract_pgn_moves(s))
    profile["samples"]["win"] = lean

    lean = []
    for s in profile["samples"]["loss"]:
        lean.append(extract_pgn_moves(s))
    profile["samples"]["loss"] = lean
    
    lean = []
    for s in profile["samples"]["draw"]:
        lean.append(extract_pgn_moves(s))
    profile["samples"]["draw"] = lean

    context = json.dumps(profile)

    prompt = f"""
You are a helpful chess coach assistant for a human player. 

Use the JSON data below to answer the question.

PROFILE DATA:
{context}

QUESTION:
{query}
"""
    
    llm = get_llm()
    return llm.predict(prompt)

@tool(args_schema=DummyInput)
def update_player_profile(input: str) -> str:
    """Checks whether a player profile needs updating. Prompts if rebuild is needed."""
    if os.path.exists(PROFILE_FILE):
        return (
            "A player profile already exists. "
            "If you'd like to regenerate it from scratch, please use the 'rebuild_player_profile' tool."
        )
    try:
        ensure_profile_data()
        return "Player profile has been created with the latest games and analysis."
    except Exception as e:
        return f"Failed to update player profile: {str(e)}"

@tool(args_schema=DummyInput)
def rebuild_player_profile(input: str) -> str:
    """Force rebuild the player profile, regardless of whether it exists."""
    try:
        fetch_recent_games()
        build_player_profile_from_file()
        return "Player profile has been rebuilt successfully."
    except Exception as e:
        return f"Failed to rebuild profile: {str(e)}"

def main():
    
    print("=" * 60)
    print("   Chess Coaching Agent")
    print("-" * 60)
    print("Data is sourced from your recent games on Chess.com.")
    print(f"Using Chess.com username: {CHESSCOM_USERNAME}")
    print()
    print("Try asking things like:")
    print("   • What is my playing style?")
    print("   • Recommend openings based on my profile")
    print("   • Update my player profile")
    print("   • Show some games where I played well")
    print("   • Analyze my recent losses")
    print("-" * 60)
    print("If you play more games or want a fresh analysis, say:")
    print("   • 'rebuild player profile'")
    print("=" * 60)
    print()

    tools = [
        update_player_profile,
        query_chess_profile,
        rebuild_player_profile,
        analyze_recently_lost_games,
    ]
    
    llm = get_llm()
    agent = initialize_agent(
        tools,
        llm,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        handle_parsing_errors=True,
        verbose=True
    )

    print("Chess Coach AI is ready.")
    print("Ask a question (or type 'exit'):")

    while True:
        print('')
        query = input(" % ")
        if query.lower() in ("exit", "quit"):
            break
        response = agent.run(query)
        print("Agent:", response)


if __name__ == "__main__":
    main()
