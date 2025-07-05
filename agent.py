import os
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
    PROFILE_ANALYSED_GAMES_FILE,
    PROFILE_RAW_GAMES_FILE,
)
from get_games import get_games_for_profile_analysis
from build_profile import build_player_profile_from_file

# Optional: ensure logging
logging.basicConfig(level=logging.INFO)

class DummyInput(BaseModel):
    input: str

def ensure_profile_data():
    if not os.path.exists(PROFILE_RAW_GAMES_FILE):
        print("Profile raw games not found, fetching...")
        get_games_for_profile_analysis()
    else:
        print("Profile raw games already available.")

    if not os.path.exists(PROFILE_ANALYSED_GAMES_FILE):
        print("Profile not yet analyzed — analyzing now. This may take a while depending on the amount of games available...")
        build_player_profile_from_file()
    else:
        print("Profile already analyzed.")


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
            profile_data = json.load(f)
    except Exception as e:
        return f"Error loading profile: {e}"

    context = json.dumps(profile_data, indent=2)

    llm = ChatOpenAI(temperature=0, model=OPENAI_MODEL)

    prompt = f"""
You are a helpful chess coach assistant for a human player. 

Use the JSON data below to answer the question.

PROFILE DATA:
{context}

QUESTION:
{query}
"""

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
        get_games_for_profile_analysis()
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
    print("-" * 60)
    print("If you update your games or want a fresh analysis, say:")
    print("   → 'update my player profile'")
    print("=" * 60)
    print()

    tools = [
        update_player_profile,
        query_chess_profile,
        rebuild_player_profile,
    ]
    
    if LLM_PROVIDER == "openai":
        logging.info(f"Loading llm from: Open AI")
        llm = ChatOpenAI(
            openai_api_key = OPENAI_API_KEY,
            model = OPENAI_MODEL,
            temperature = LLM_TEMPERATURE,
        )
    else:  # Local LLM via LM Studio
        logging.info(f"Loading llm from: {LOCAL_API_BASE}")
        llm = ChatOpenAI(
            openai_api_key = "lm-studio",  # Dummy key
            openai_api_base = LOCAL_API_BASE,
            model = LOCAL_MODEL_NAME,
            temperature = LLM_TEMPERATURE,
        )

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
        query = input(" % ")
        if query.lower() in ("exit", "quit"):
            break
        response = agent.run(query)
        print("Agent:", response)


if __name__ == "__main__":
    main()
