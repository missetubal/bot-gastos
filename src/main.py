# src/main.py
from dotenv import load_dotenv
import os
import sys

from src.bot.bot_setup import setup_and_run_bot
from src.core.db import get_supabase_client

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application # Import Application for type hinting

print("DEBUG: Iniciando src/main.py")

try:
    load_dotenv()
    print("DEBUG: Variáveis de ambiente carregadas.")

    supabase_client = get_supabase_client()
    print("DEBUG: Cliente Supabase inicializado.")

    config = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "SUPABASE_CLIENT": supabase_client,
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    }
    print(f"DEBUG: Configurações do bot criadas: {config.keys()}")

    # --- Setup the python-telegram-bot Application ---
    ptb_application = setup_and_run_bot(config)
    print("DEBUG: Aplicação do bot (python-telegram-bot) configurada.")

    # CRUCIAL: Initialize the application for webhook handling
    # This must be awaited, so it needs to be inside an async context.
    # We will call it when the webhook is received, or ensure it's called once.
    # The best place is often *within* the webhook endpoint itself if it's not
    # initialized globally before the server starts.
    # Let's ensure it's called once in the app setup, potentially when the Flask app starts.
    # However, since Flask doesn't have a direct 'on_startup' for async without more setup,
    # let's try calling it when the first update comes in if needed, but that's less clean.

    # Simpler solution: ptb_application.run_webhook() internally handles this
    # but since we are not using that, we need to call .initialize()
    # Let's call it just before the Flask app starts listening, if possible in Gunicorn context.
    # Or, the easiest way is to add it inside the webhook handler with a check.

    # Let's add a global flag to ensure initialize() is called only once
    _application_initialized = False

    # --- Setup the Flask web application ---
    flask_app = Flask(__name__)

    WEBHOOK_PATH_SUFFIX = "/webhook" 
    
    @flask_app.route(WEBHOOK_PATH_SUFFIX, methods=['POST'])
    async def telegram_webhook():
        nonlocal _application_initialized # Access the global flag

        # Initialize the PTB application if it hasn't been already
        if not _application_initialized:
            print("DEBUG: Initializing python-telegram-bot Application for webhook...")
            await ptb_application.initialize()
            _application_initialized = True
            print("DEBUG: python-telegram-bot Application initialized.")
            
        if not request.is_json:
            print("ERROR: Webhook received non-JSON request.")
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400

        update_json = request.get_json()
        print(f"DEBUG: Webhook received update: {update_json.keys() if update_json else 'None'}")

        try:
            update = Update.de_json(update_json, ptb_application.bot)
            await ptb_application.process_update(update)
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            print(f"ERROR: Failed to process Telegram update: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return jsonify({"status": "error", "message": "Failed to process update"}), 500

    wsgi_app = flask_app
    print("DEBUG: Variável wsgi_app definida como a aplicação Flask. Aplicação WSGI pronta.")

except Exception as e:
    print(f"ERROR: Erro crítico durante a inicialização em src/main.py: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise