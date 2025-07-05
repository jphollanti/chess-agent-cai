# CAI - Chess Agent

**CAI** is a chess coaching agent built with [LangChain](https://www.langchain.com/) and powered by your recent Chess.com games.  
It builds a personalized player profile with insights like:

- Most played openings (with win/loss stats)
- Tactical vs positional tendencies
- Time-trouble patterns
- Blunders and dip analysis
- Style profile: aggressive, defensive, etc.
- Representative sample games
- Natural language Q&A via a LangChain agent

## Setup

### 1. Create environment

Assuming you're using Conda and UV.

```bash
conda create --name cai python=3.11
conda activate cai
uv pip install -r pyproject.toml
```

### 2. Setup environment variables

Create a .env file:

```dotenv
OPENAI_API_KEY=your_openai_api_key
CHESSCOM_USERNAME=your_chesscom_username
PROFILE_INFO=I'm typically rated around 1500 in rapid games. I favor classical openings like the Queen's Gambit and often opt for fianchetto setups, especially with black on the kingside. I'm a sucker for diving head first into a tactic like sacrificing a knight or a bishop for two pawns in front of the opponent's king.
```

Run setup-dependencies.sh to download stockfish, ECO openings and openings book 

### 3. Other than python dependencies

Download Stockfish, ECO opening files, and the GM2001 opening book by running:

```bash
./setup-dependencies.sh
```

This will:
- Download the latest Stockfish binary (Apple Silicon)
- Fetch .json files for A–E ECO openings
- Download the gm2001.bin Polyglot opening book

## Usage

```bash
python agent.py
```

You'll be greeted with a prompt like:

```bash
Try asking things like:
   • What is my playing style?
   • Recommend openings based on my profile
   • Show some games where I played well
   • Update my player profile
```

## Developer Notes

Uses stockfish engine for move analysis and eval dips

Uses Chess.com API to fetch recent games

ECO classification uses FEN → name mapping or polyglot books

Analysis is cached in data/ files (can be rebuilt via the agent)