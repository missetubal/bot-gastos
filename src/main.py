# src/main.py
from dotenv import load_dotenv
import os
import sys # Importe sys para depuração

print("DEBUG: Iniciando src/main.py") # DEBUG 1

from src.bot.bot_setup import setup_and_run_bot
from src.core.db import get_supabase_client
from telegram.ext import Application

print("DEBUG: Importações em src/main.py concluídas.") # DEBUG 2

try:
    # Carrega variáveis de ambiente do .env
    load_dotenv()
    print("DEBUG: Variáveis de ambiente carregadas.") # DEBUG 3

    # Inicializa o cliente Supabase uma única vez
    supabase_client = get_supabase_client()
    print("DEBUG: Cliente Supabase inicializado.") # DEBUG 4

    # Passa as configurações carregadas para o setup do bot
    config = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "SUPABASE_CLIENT": supabase_client,
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"), # Para o Gemini
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash") # Para o Gemini
    }
    print(f"DEBUG: Configurações do bot criadas: {config.keys()}") # DEBUG 5

    # Configura a aplicação do bot
    application = setup_and_run_bot(config)
    print("DEBUG: Aplicação do bot configurada.") # DEBUG 6

    # --- Variável GLOBAL para o Servidor WSGI ---
    wsgi_app = application
    print("DEBUG: Variável wsgi_app definida. Aplicação WSGI pronta.") # DEBUG 7

except Exception as e:
    print(f"ERROR: Erro crítico durante a inicialização em src/main.py: {e}", file=sys.stderr) # DEBUG ERRO
    # Importante: se houver um erro aqui, wsgi_app não será definida.
    # Em um ambiente de produção, você pode querer levantar o erro novamente
    # ou ter um tratamento de erro mais sofisticado.
    raise # Re-levanta o erro para que o Gunicorn o veja# src/main.py
from dotenv import load_dotenv
import os
import sys # Importe sys para depuração

print("DEBUG: Iniciando src/main.py") # DEBUG 1

from src.bot.bot_setup import setup_and_run_bot
from src.core.db import get_supabase_client
from telegram.ext import Application

print("DEBUG: Importações em src/main.py concluídas.") # DEBUG 2

try:
    # Carrega variáveis de ambiente do .env
    load_dotenv()
    print("DEBUG: Variáveis de ambiente carregadas.") # DEBUG 3

    # Inicializa o cliente Supabase uma única vez
    supabase_client = get_supabase_client()
    print("DEBUG: Cliente Supabase inicializado.") # DEBUG 4

    # Passa as configurações carregadas para o setup do bot
    config = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "SUPABASE_CLIENT": supabase_client,
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"), # Para o Gemini
        "GEMINI_MODEL": os.getenv("GEMINI_MODEL", "gemini-1.5-flash") # Para o Gemini
    }
    print(f"DEBUG: Configurações do bot criadas: {config.keys()}") # DEBUG 5

    # Configura a aplicação do bot
    application = setup_and_run_bot(config)
    print("DEBUG: Aplicação do bot configurada.") # DEBUG 6

    # --- Variável GLOBAL para o Servidor WSGI ---
    wsgi_app = application
    print("DEBUG: Variável wsgi_app definida. Aplicação WSGI pronta.") # DEBUG 7

except Exception as e:
    print(f"ERROR: Erro crítico durante a inicialização em src/main.py: {e}", file=sys.stderr) # DEBUG ERRO
    # Importante: se houver um erro aqui, wsgi_app não será definida.
    # Em um ambiente de produção, você pode querer levantar o erro novamente
    # ou ter um tratamento de erro mais sofisticado.
    raise # Re-levanta o erro para que o Gunicorn o veja