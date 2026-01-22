from __future__ import annotations
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home() -> str:
    return "OK"

def run_flask_app() -> None:
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Flask server on port {port}...")
    app.run(host='0.0.0.0', port=port)

def start_server() -> None:
    server_thread = Thread(target=run_flask_app)
    server_thread.daemon = True # Allows the main program to exit even if the thread is still running
    server_thread.start()
