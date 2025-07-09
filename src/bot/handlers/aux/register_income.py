from typing import Any, Dict
from src.core import db
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes


async def register_income(
    update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]
) -> None:
    """Registra um ganho no banco de dados e envia a confirmação."""
    supabase_client = context.bot_data["supabase_client"]
    valor = transaction_info["value"]
    data = transaction_info["date"]
    descricao = transaction_info["description"]

    if db.add_ganho(supabase_client, valor, descricao, data):
        await update.message.reply_text(
            f"✅ Ganho de R${valor:.2f} de '{descricao}' registrado com sucesso! 🥳",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            "❌ Ocorreu um erro ao registrar seu ganho. Tente novamente mais tarde. 😟",
            reply_markup=ReplyKeyboardRemove(),
        )
