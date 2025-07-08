from typing import Any, Dict
from src.core import db
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

async def send_confirmation_message(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]) -> None:
    """Envia a mensagem de confirmação da transação ao usuário com emojis e formatação."""
    supabase_client = context.bot_data['supabase_client']
    valor_fmt = f"R${transaction_info['value']:.2f}"
    data_fmt = transaction_info['date']
    
    categoria_nome_real = transaction_info.get('categoria_nome_db') or transaction_info.get('categoria')
    if transaction_info.get('category_id') and not transaction_info.get('categoria_nome_db'):
        cat_info = next((c for c in db.get_categories(supabase_client) if c['id'] == transaction_info['category_id']), None)
        if cat_info:
            categoria_nome_real = cat_info['name']
    
    forma_pagamento_nome_real = transaction_info.get('forma_pagamento_nome_real') or transaction_info.get('forma_pagamento_text')
    if transaction_info.get('forma_pagamento_id') and not transaction_info.get('forma_pagamento_nome_real'):
        fp_info = next((f for f in db.get_formas_pagamento(supabase_client) if f['id'] == transaction_info['forma_pagamento_id']), None)
        if fp_info:
            forma_pagamento_nome_real = fp_info['name']

    descricao_gasto_fmt = f"({transaction_info.get('descricao_gasto', 'sem detalhes')})" if transaction_info.get('descricao_gasto') else ""

    emoji = ""
    # Emojis para categorias
    if categoria_nome_real and categoria_nome_real.lower() == 'alimentacao':
        emoji = "🍔"
    elif categoria_nome_real and categoria_nome_real.lower() == 'transporte':
        emoji = "🚌"
    elif categoria_nome_real and categoria_nome_real.lower() == 'moradia':
        emoji = "🏠"
    elif categoria_nome_real and categoria_nome_real.lower() == 'lazer':
        emoji = "🎉"
    elif categoria_nome_real and categoria_nome_real.lower() == 'saude':
        emoji = "💊"
    elif categoria_nome_real and categoria_nome_real.lower() == 'educacao':
        emoji = "📚"
    elif categoria_nome_real and categoria_nome_real.lower() == 'compras':
        emoji = "🛍️"
    elif categoria_nome_real and categoria_nome_real.lower() == 'outros':
        emoji = "🤷‍♀️"
    elif categoria_nome_real and categoria_nome_real.lower() == 'desconhecida':
        emoji = "❓"
    else:
        emoji = "💸" # Emoji genérico para outros gastos

    message_text = ""
    if transaction_info['transaction_type'] == 'gasto':
        message_text = (
            f"Confirma o *gasto*? {emoji}\n"
            f"💰 Valor: *{valor_fmt}* {descricao_gasto_fmt}\n"
            f"🏷️ Categoria: *{categoria_nome_real}*\n"
            f"📅 Data: *{data_fmt}*\n"
            f"💳 Pagamento: *{forma_pagamento_nome_real or 'Não Informado'}*"
        )
    elif transaction_info['transaction_type'] == 'ganho':
        emoji = "💰"
        message_text = (
            f"Confirma o *ganho*? {emoji}\n"
            f"💰 Valor: *{valor_fmt}*\n"
            f"📝 Descrição: *{transaction_info.get('description')}*\n"
            f"📅 Data: *{data_fmt}*"
        )
    
    keyboard = [["Sim ✅", "Não ❌"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"{message_text}\n\n*Tudo certo?* 🤔", reply_markup=reply_markup, parse_mode='Markdown')

