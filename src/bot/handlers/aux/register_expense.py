from typing import Any, Dict
from src.core import db
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

async def register_expense(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]) -> None:
    """Registra um gasto no banco de dados e envia a confirmação."""
    supabase_client = context.bot_data['supabase_client']
    valor = transaction_info['valor']
    categoria_id = transaction_info['categoria_id']
    data = transaction_info['data']
    forma_pagamento_id = transaction_info.get('forma_pagamento_id')
    descricao_gasto = transaction_info.get('descricao_gasto')
    categoria_nome_db = transaction_info.get('categoria_nome_db')
    final_payment_method_name = transaction_info.get('forma_pagamento_nome_real') or transaction_info.get('forma_pagamento_text')

    if db.add_gasto(supabase_client, valor, categoria_id, data, forma_pagamento_id, descricao_gasto):
        await update.message.reply_text(
            f"✅ Gasto de R${valor:.2f} ({descricao_gasto}) em '{categoria_nome_db}' via '{final_payment_method_name}' registrado com sucesso! 🎉",
            reply_markup=ReplyKeyboardRemove()
        )
        original_category_text = transaction_info.get('original_category_text')
        if original_category_text and original_category_text.lower() != categoria_nome_db.lower():
            current_aliases = set()
            for cat in db.get_categorias(supabase_client):
                if cat['id'] == categoria_id:
                    if cat['aliases'] and isinstance(cat['aliases'], list):
                        current_aliases.update(cat['aliases'])
                    break
            if original_category_text.lower() not in [a.lower() for a in current_aliases]:
                current_aliases.add(original_category_text)
                db.update_categoria_aliases(supabase_client, categoria_id, list(current_aliases))
                await update.message.reply_text(f"✨ '{original_category_text}' foi adicionado como um atalho para '{categoria_nome_db}'. O bot aprenderá com isso! 🧠", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde. 😟", reply_markup=ReplyKeyboardRemove())
