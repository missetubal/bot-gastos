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

    ptb_application = setup_and_run_bot(config)
    print("DEBUG: Aplicação do bot (python-telegram-bot) configurada.")

    # --- Setup the Flask web application ---
    flask_app = Flask(__name__)

    # Flag para garantir que ptb_application.initialize() seja chamado apenas uma vez
    _application_initialized_flag = False # Variável global

    WEBHOOK_PATH_SUFFIX = "/webhook" 
    
    @flask_app.route(WEBHOOK_PATH_SUFFIX, methods=['POST'])
    async def telegram_webhook():
        global _application_initialized_flag # <--- DECLARA COMO GLOBAL AQUI

        # Inicialize o PTB application se ele não foi inicializado ainda
        if not _application_initialized_flag:
            print("DEBUG: Inicializando python-telegram-bot Application para webhook (primeira requisição)...")
            await ptb_application.initialize() # <--- CHAMADA AQUI
            _application_initialized_flag = True
            print("DEBUG: python-telegram-bot Application inicializada.")
            
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