# src/bot/bot_setup.py
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import Update # Import Update para a tipagem
from src.bot.commands import (
    start_command, help_command, balanco_command, gastos_por_categoria_command,
    categorias_command, adicionar_categoria_command, definir_limite_command,
    adicionar_alias_command, total_categoria_command, total_por_pagamento_command,
    gastos_mensal_combinado_command, listar_gastos_command
)
from src.bot.handlers import (
    handle_initial_message, handle_category_clarification, handle_new_category_name, 
    handle_payment_method, handle_confirmation, handle_correction, 
    HANDLE_INITIAL_MESSAGE, ASKING_CATEGORY_CLARIFICATION, ASKING_NEW_CATEGORY_NAME, 
    ASKING_PAYMENT_METHOD, ASKING_CONFIRMATION, ASKING_CORRECTION
)
from src.config import TELEGRAM_BOT_TOKEN

def setup_and_run_bot(config: dict) -> Application: # Especifica o tipo de retorno
    """
    Configura a aplicação do bot do Telegram (Handlers, Comandos, Conversas).
    Retorna o objeto Application configurado, pronto para ser usado por um servidor WSGI.
    """
    # Constrói a aplicação principal do python-telegram-bot
    application = Application.builder().token(config["TELEGRAM_BOT_TOKEN"]).build()

    # Armazena o cliente Supabase no bot_data para que handlers e comandos possam acessá-lo
    application.bot_data['supabase_client'] = config["SUPABASE_CLIENT"]

    # --- Adiciona os Handlers para Comandos ---
    # Comandos que são acionados com '/' (ex: /start, /help)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balanco", balanco_command))
    application.add_handler(CommandHandler("gastos_por_categoria", gastos_por_categoria_command))
    application.add_handler(CommandHandler("categorias", categorias_command))
    application.add_handler(CommandHandler("adicionar_categoria", adicionar_categoria_command))
    application.add_handler(CommandHandler("definir_limite", definir_limite_command))
    application.add_handler(CommandHandler("adicionar_alias", adicionar_alias_command))
    application.add_handler(CommandHandler("total_categoria", total_categoria_command))
    application.add_handler(CommandHandler("total_por_pagamento", total_por_pagamento_command))
    application.add_handler(CommandHandler("gastos_mensal_combinado", gastos_mensal_combinado_command))
    application.add_handler(CommandHandler("listar_gastos", listar_gastos_command))

    # --- Configura o ConversationHandler ---
    # Este é o manipulador principal para o fluxo de conversas em múltiplas etapas.
    # Ele é acionado por mensagens de texto que NÃO são comandos.
    conv_handler = ConversationHandler(
        # entry_points: Onde a conversa pode começar
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_initial_message)],
        
        # states: Mapeia estados a handlers específicos
        states={
            # Estado para clarificação de categoria (se o Llama não identificou)
            ASKING_CATEGORY_CLARIFICATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_category_clarification)
            ],
            # Estado para criação de nova categoria (se o usuário escolher)
            ASKING_NEW_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_category_name)
            ],
            # Estado para perguntar a forma de pagamento (se o Llama não identificou)
            ASKING_PAYMENT_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_method)
            ],
            # Estado para confirmar a transação (Sim/Não)
            ASKING_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation)
            ],
            # Estado para processar correções (se o usuário disser 'Não' à confirmação)
            ASKING_CORRECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction)
            ],
        },
        # fallbacks: O que fazer se a conversa não se encaixar em nenhum estado
        # Aqui, o comando /cancel encerra qualquer conversa em andamento.
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
    )
    # Adiciona o ConversationHandler à aplicação
    application.add_handler(conv_handler)

    # Mensagem de log para indicar que o bot foi configurado
    print(f"Bot Telegram configurado para Webhooks. Pronto para ser rodado pelo WSGI.")
    # NÃO chamamos application.run_polling() aqui!
    # A aplicação será rodada por um servidor WSGI (Gunicorn) que o Render iniciará.
    return application