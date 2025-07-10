from typing import Any, Dict
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
from src.core import db


async def register_expense(
    update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]
) -> None:
    """Registra um gasto no banco de dados e envia a confirmação."""
    supabase_client = context.bot_data["supabase_client"]
    valor = transaction_info["value"]
    category_id = transaction_info["category_id"]
    data = transaction_info["date"]
    forma_pagamento_id = transaction_info.get("forma_pagamento_id")
    descricao_gasto = transaction_info.get("descricao_gasto")
    categoria_nome_db = transaction_info.get("categoria_nome_db")
    final_payment_method_name = transaction_info.get(
        "forma_pagamento_nome_real"
    ) or transaction_info.get("forma_pagamento_text")

    if db.add_expense(
        supabase_client, valor, category_id, data, forma_pagamento_id, descricao_gasto
    ):
        await update.message.reply_text(
            f"✅ Gasto de R${valor:.2f} ({descricao_gasto}) em '{categoria_nome_db}' via '{final_payment_method_name}' registrado com sucesso! 🎉",
            reply_markup=ReplyKeyboardRemove(),
        )
        original_category_text = transaction_info.get("original_category_text")
        if (
            original_category_text
            and original_category_text.lower() != categoria_nome_db.lower()
        ):
            current_aliases = set()
            for cat in db.get_categories(supabase_client):
                if cat["id"] == category_id:
                    if cat["aliases"] and isinstance(cat["aliases"], list):
                        current_aliases.update(cat["aliases"])
                    break
            if original_category_text.lower() not in [
                a.lower() for a in current_aliases
            ]:
                current_aliases.add(original_category_text)
                db.update_category_aliases(
                    supabase_client, category_id, list(current_aliases)
                )
                await update.message.reply_text(
                    f"✨ '{original_category_text}' foi adicionado como um atalho para '{categoria_nome_db}'. O bot aprenderá com isso! 🧠",
                    reply_markup=ReplyKeyboardRemove(),
                )
    else:
        await update.message.reply_text(
            "❌ Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde. 😟",
            reply_markup=ReplyKeyboardRemove(),
        )
