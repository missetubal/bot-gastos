# src/main.py
from dotenv import load_dotenv
import os

from src.bot.bot_setup import setup_and_run_bot, WEBHOOK_URL # Importa WEBHOOK_URL também
from src.core.db import get_supabase_client
from telegram.ext import Application # Importa Application para a tipagem do WSGI

# Carrega variáveis de ambiente do .env
load_dotenv()

# Inicializa o cliente Supabase uma única vez
supabase_client = get_supabase_client()

# Passa as configurações carregadas para o setup do bot
config = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "SUPABASE_CLIENT": supabase_client
}

# Configura a aplicação do bot
application = setup_and_run_bot(config)

# --- Configuração do Webhook no Telegram (Executar uma vez) ---
# Você precisará rodar esta parte do código APENAS UMA VEZ
# Para registrar o webhook no Telegram.
# O PythonAnywhere não tem uma forma fácil de rodar isso "on deploy".
# A melhor forma é rodar o main.py uma vez via console para setar o webhook.

# print(f"Definindo webhook para: {WEBHOOK_URL}")
# try:
#     # Esta parte requer que a URL do PythonAnywhere esteja ativa e acessível.
#     # Pode ser que você precise rodar isso APÓS a primeira configuração do Web App no PA.
#     application.bot.set_webhook(url=WEBHOOK_URL)
#     print("Webhook configurado com sucesso no Telegram!")
# except Exception as e:
#     print(f"Erro ao configurar webhook no Telegram: {e}")
#     print("Certifique-se de que sua URL do PythonAnywhere está correta e ativa.")


# --- Variável GLOBAL para o Servidor WSGI ---
# O PythonAnywhere vai procurar por uma variável chamada 'application' (ou 'app')
# para rodar sua aplicação web.
# Você apontará o WSGI deles para este arquivo e esta variável.
wsgi_app = application
print("Aplicação WSGI pronta para o PythonAnywhere.")

