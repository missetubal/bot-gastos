# src/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configurações do Ollama (Llama local) - REVERTIDAS
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL") # <-- RE-ADICIONADA
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")     # <-- RE-ADICIONADA

# REMOVIDO: GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# REMOVIDO: GEMINI_MODEL = "gemini-pro"