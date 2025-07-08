# src/bot/bot_setup.py
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CommandHandler,
    ConversationHandler,
)
from src.bot.commands import (
    start_command,
    help_command,
    balanco_command,
    gastos_por_categoria_command,
    categorias_command,
    adicionar_categoria_command,
    definir_limite_command,
    adicionar_alias_command,
    total_categoria_command,
    total_por_pagamento_command,
    gastos_mensal_combinado_command,
    listar_gastos_command,  # <-- NOVOS COMANDOS IMPORTADOS
)
from src.bot.handlers import (
    handle_initial_message,
    handle_category_clarification,
    handle_new_category_name,
    handle_payment_method,
    handle_confirmation,
    handle_correction,
    HANDLE_INITIAL_MESSAGE,
    ASKING_CATEGORY_CLARIFICATION,
    ASKING_NEW_CATEGORY_NAME,
    ASKING_PAYMENT_METHOD,
    ASKING_CONFIRMATION,
    ASKING_CORRECTION,
)
from src.config import TELEGRAM_BOT_TOKEN


def setup_and_run_bot(config: dict):
    """Configura e inicia a aplicação do bot do Telegram."""
    application = Application.builder().token(config["TELEGRAM_BOT_TOKEN"]).build()

    application.bot_data["supabase_client"] = config["SUPABASE_CLIENT"]

    # Adiciona os handlers para comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("balanco", balanco_command))
    application.add_handler(
        CommandHandler("gastos_por_categoria", gastos_por_categoria_command)
    )
    application.add_handler(CommandHandler("categorias", categorias_command))
    application.add_handler(
        CommandHandler("adicionar_categoria", adicionar_categoria_command)
    )
    application.add_handler(CommandHandler("definir_limite", definir_limite_command))
    application.add_handler(CommandHandler("adicionar_alias", adicionar_alias_command))
    application.add_handler(CommandHandler("total_categoria", total_categoria_command))
    application.add_handler(
        CommandHandler("total_por_pagamento", total_por_pagamento_command)
    )
    application.add_handler(
        CommandHandler("gastos_mensal_combinado", gastos_mensal_combinado_command)
    )  # NOVO COMANDO REGISTRADO
    application.add_handler(
        CommandHandler("listar_gastos", listar_gastos_command)
    )  # NOVO COMANDO REGISTRADO

    # Configura o ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_initial_message)
        ],
        states={
            ASKING_CATEGORY_CLARIFICATION: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_category_clarification
                )
            ],
            ASKING_NEW_CATEGORY_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_new_category_name
                )
            ],
            ASKING_PAYMENT_METHOD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_method)
            ],
            ASKING_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_confirmation)
            ],
            ASKING_CORRECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_correction)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
    )
    application.add_handler(conv_handler)

    print(
        f"Bot Telegram iniciado! Procure por @<nome_do_seu_bot> no Telegram e comece a conversar."
    )
    print(
        "Certifique-se de que o Ollama está rodando e o modelo 'llama3' (ou o que você configurou) está baixado."
    )
    print(
        "Verifique também se suas credenciais do Supabase estão corretas e as tabelas 'gastos', 'ganhos', 'categorias' e 'formas_pagamento' foram criadas."
    )

    application.run_polling()
