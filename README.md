# 一方通行のローグライクRPG Bot

This is a Discord bot designed to provide a text-based roguelike RPG experience directly within Discord.

## Features

*   **Game Initiation**: Start new adventures with the `/start` command.
*   **Dungeon Exploration**: Navigate through dungeons using movement commands.
*   **Combat System**: Engage in turn-based combat with various monsters.
*   **Character Management**: View inventory, equip items, and check character status.
*   **Persistent Data**: All player progress, inventory, and game states are saved.

## Setup

To run this bot, follow these steps:

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Create a virtual environment and install dependencies**:
    ```bash
    python -m venv venv
    source venv/bin/activate # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Configure environment variables**:
    Create a `.env` file in the root directory of the project based on `.env.example`.
    ```
    DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
    PORT=8080
    ```
    Replace `YOUR_BOT_TOKEN_HERE` with your actual Discord bot token obtained from the [Discord Developer Portal](https://discord.com/developers/applications).
    `PORT` is used by the internal Flask server for health checks (e.g., for Koyeb deployment).

4.  **Run the bot**:
    ```bash
    python main.py
    ```

    The bot should now be online in your Discord server, and the Flask server will be running for health checks.

## Usage

Once the bot is running and added to your server, you can use slash commands:

*   `/start`: Begin a new game or resume an existing one.
*   `/m <direction>`: Move your character in the dungeon (e.g., `/m north`).
*   `/attack`: Initiate an attack in combat.
*   `/item <item_name>`: Use an item from your inventory.
*   `/run`: Attempt to flee from combat.
*   `/inventory`: View your character's inventory.
*   `/equip <item_name>`: Equip an item.
*   `/status`: Check your character's current stats and status.

Enjoy your roguelike adventure!
