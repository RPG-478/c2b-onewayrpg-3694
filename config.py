from __future__ import annotations
import os

# --- Bot Configuration ---
DISCORD_TOKEN_ENV_VAR: str = "DISCORD_TOKEN"

# --- Data Persistence Configuration ---
DATA_DIR: str = "data"
PLAYER_DATA_FILE: str = os.path.join(DATA_DIR, "player_data.json")
DUNGEON_DATA_FILE: str = os.path.join(DATA_DIR, "dungeon_data.json")
GAME_STATE_FILE: str = os.path.join(DATA_DIR, "game_state.json")

# --- Game Constants ---
STARTING_HEALTH: int = 100
STARTING_ATTACK: int = 10
STARTING_DEFENSE: int = 5
STARTING_GOLD: int = 0
MAX_INVENTORY_SLOTS: int = 10

# --- Flask Server Configuration (for keep_alive.py) ---
FLASK_PORT_ENV_VAR: str = "PORT"
DEFAULT_FLASK_PORT: int = 8080
