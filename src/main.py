src/main.py
 from dotenv import load_dotenv
 import os

 from src.bot.bot_setup import setup_and_run_bot
 from src.core.db import get_supabase_client # Importa a função que cria o cliente

 def main():
     # Carrega variáveis de ambiente do .env
     load_dotenv()

     # Inicializa o cliente Supabase aqui, uma única vez
     supabase_client = get_supabase_client()

     # Passa o cliente Supabase para o setup do bot
     config = {
         "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
         "OLLAMA_API_URL": os.getenv("OLLAMA_API_URL"),
         "OLLAMA_MODEL": os.getenv("OLLAMA_MODEL"),
         "SUPABASE_CLIENT": supabase_client # Chave importante!
     }

     print("Iniciando bot de finanças...")
     setup_and_run_bot(config)

 if __name__ == "__main__":
     main() 