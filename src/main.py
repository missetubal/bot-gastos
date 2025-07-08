# src/main.py
from dotenv import load_dotenv
import os
import sys

from src.bot.bot_setup import setup_and_run_bot # This function is called once
from src.core.db import get_supabase_client

from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application # Import Application for type hinting
import asyncio # Importar asyncio

print("DEBUG: Iniciando src/main.py (Execução Global)") # DEBUG: Para indicar que é o escopo global

# --- Setup da Aplicação no Escopo Global (Executado apenas uma vez ao carregar o módulo) ---
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

    # ptb_application é configurada e fica disponível globalmente
    ptb_application = setup_and_run_bot(config)
    print("DEBUG: Aplicação do bot (python-telegram-bot) configurada.")

    # CRUCIAL: Inicializar a aplicação PTB uma única vez no startup.
    # Esta linha executa a corrotina initialize() em um contexto síncrono.
    # Gunicorn executa main.py uma vez no startup.
    try:
        asyncio.run(ptb_application.initialize())
        print("DEBUG: python-telegram-bot Application inicializada com sucesso!")
    except RuntimeError as e:
        if "cannot run an event loop while another loop is running" in str(e):
            print("DEBUG: Event loop já em execução, pulando asyncio.run(initialize()).")
            # Isso pode acontecer se o ambiente (Gunicorn) já iniciou seu próprio loop.
            # Se esse for o caso, ptb_application deve ser inicializada de outra forma
            # ou ser robusta o suficiente para funcionar sem uma chamada explícita aqui.
            # No entanto, a documentação PTB 20.x requer initialize().
            # Se isso falhar, a alternativa é ter um background task que inicialize.
            pass
        else:
            raise e


    # --- Setup da Aplicação Web Flask (também no escopo global) ---
    flask_app = Flask(__name__)

    WEBHOOK_PATH_SUFFIX = "/webhook"
    
    # Esta é a rota que o Gunicorn vai servir
    @flask_app.route(WEBHOOK_PATH_SUFFIX, methods=['POST'])
    async def telegram_webhook():
        # AQUI, SÓ O CÓDIGO PARA PROCESSAR UMA ÚNICA REQUISIÇÃO DE WEBHOOK
        # ptb_application JÁ DEVE ESTAR CONFIGURADA E INICIALIZADA GLOBALMENTE
        
        if not request.is_json:
            print("ERROR: Webhook received non-JSON request.")
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400

        update_json = request.get_json()
        print(f"DEBUG: Webhook received update: {update_json.keys() if update_json else 'None'}")

        try:
            update = Update.de_json(update_json, ptb_application.bot)
            await ptb_application.process_update(update) # Processa a atualização
            return jsonify({"status": "ok"}), 200
        except Exception as e:
            print(f"ERROR: Failed to process Telegram update: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return jsonify({"status": "error", "message": "Failed to process update"}), 500

    # A variável wsgi_app também deve estar no escopo global
    wsgi_app = flask_app
    print("DEBUG: Variável wsgi_app definida como a aplicação Flask. Aplicação WSGI pronta.")

except Exception as e:
    # Este bloco try/except pega erros na inicialização GLOBAL do módulo
    print(f"ERROR: Erro crítico durante a inicialização em src/main.py: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    raise # Re-levanta o erro para que o Gunicorn o veja