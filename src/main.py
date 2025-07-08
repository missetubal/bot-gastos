# src/main.py
from dotenv import load_dotenv
import os
import sys

from src.bot.bot_setup import setup_and_run_bot
from src.core.db import get_supabase_client

# Import Flask
from flask import Flask, request, jsonify # <--- NEW IMPORTS
from telegram import Update # Import Update for handling incoming webhooks

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
    # setup_and_run_bot now returns the application object.
    ptb_application = setup_and_run_bot(config) # <--- Rename to ptb_application
    print("DEBUG: Aplicação do bot (python-telegram-bot) configurada.")

    # --- Setup the Flask web application ---
    flask_app = Flask(__name__) # <--- Create Flask app instance

    # The webhook path must match the one used in set_webhook.py
    WEBHOOK_PATH_SUFFIX = "/webhook" 
    
    @flask_app.route(WEBHOOK_PATH_SUFFIX, methods=['POST'])
    async def telegram_webhook(): # <--- This is now an async Flask endpoint
        """Handle incoming Telegram webhook updates."""
        # Ensure the request is JSON
        if not request.is_json:
            print("ERROR: Webhook received non-JSON request.")
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400

        # Get the update from the request body
        update_json = request.get_json()
        print(f"DEBUG: Webhook received update: {update_json.keys() if update_json else 'None'}")

        # Process the update using ptb_application
        try:
            # Create a Telegram Update object from the JSON
            update = Update.de_json(update_json, ptb_application.bot)
            # Process the update asynchronously
            await ptb_application.process_update(update)
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            print(f"ERROR: Failed to process Telegram update: {e}", file=sys.stderr)
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc(file=sys.stderr)
            return jsonify({"status": "error", "message": "Failed to process update"}), 500

    # Define the wsgi_app for Gunicorn to find
    # This is the Flask app instance
    wsgi_app = flask_app # <--- wsgi_app IS NOW THE FLASK APP INSTANCE
    print("DEBUG: Variável wsgi_app definida como a aplicação Flask. Aplicação WSGI pronta.")

except Exception as e:
    print(f"ERROR: Erro crítico durante a inicialização em src/main.py: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr) # Print traceback for critical errors
    # Re-raise the error so Gunicorn reports it clearly
    raise