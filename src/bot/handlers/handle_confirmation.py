from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from src.bot.handlers import (
    ASKING_CONFIRMATION,
    ASKING_CORRECTION,
    ASKING_PAYMENT_METHOD,
)
from src.bot.handlers.aux import (
    register_expense,
    register_income,
    send_confirmation_message,
)


async def handle_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Lida com a confirmação (Sim/Não) da transação."""
    user_response = update.message.text.lower()
    pending_transaction = context.user_data.get("pending_transaction")

    if not pending_transaction:
        await update.message.reply_text(
            "Ops! 😬 Não encontrei uma transação pendente para confirmar. 🔄",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if user_response == "sim ✅" or user_response == "sim":
        if pending_transaction["transaction_type"] == "gasto":
            await register_expense(update, context, pending_transaction)
        elif pending_transaction["transaction_type"] == "ganho":
            await register_income(update, context, pending_transaction)

        context.user_data.pop("pending_transaction", None)  # Limpa a transação pendente
        return ConversationHandler.END  # Fim da conversa

    elif user_response == "não ❌" or user_response == "não" or user_response == "nao":
        await update.message.reply_text(
            "Entendido! 🤔 O que precisa ser alterado? \n"
            "Por favor, digite o campo e o novo valor. \n"
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰', 'Data 2025-07-01 📅', 'Forma Pix 💳', 'Descricao Jantar de Aniversário 🎂'.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASKING_CORRECTION  # Entra no estado de correção

    else:
        keyboard = [["Sim ✅", "Não ❌"]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        await update.message.reply_text(
            "Por favor, responda apenas 'Sim ✅' ou 'Não ❌'.",
            reply_markup=reply_markup,
        )
        return ASKING_CONFIRMATION  # Permanece no estado de confirmação
