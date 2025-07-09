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

# Configurações do Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # <-- Carrega a chave Gemini
GEMINI_MODEL = "gemini-1.5-flash"  # <-- Define o modelo Gemini a ser usado
