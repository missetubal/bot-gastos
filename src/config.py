# src/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Carrega as variáveis do arquivo .env

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configurações do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Configurações do Ollama (Llama local)
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL") # Ex: "llama3" ou "tinyllama"

# Configurações do Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") # <-- NOVA VARIÁVEL
GEMINI_MODEL = "gemini-pro"