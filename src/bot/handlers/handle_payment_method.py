from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.bot.handlers import  ASKING_CONFIRMATION
from src.bot.handlers.aux import send_confirmation_message
from src.core import db
from src.utils.text_utils import to_camel_case

async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a forma de pagamento fornecida pelo usuário."""
    supabase_client = context.bot_data['supabase_client']
    user_response_payment = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    valor = pending_transaction['value']
    data = pending_transaction['date']
    category_id = pending_transaction['category_id']
    categoria_nome_db = pending_transaction['categoria_nome_db']
    original_category_text = pending_transaction['original_category_text']
    descricao_gasto = pending_transaction['descricao_gasto']

    final_payment_method_name = to_camel_case(user_response_payment)
    forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, final_payment_method_name)

    if not forma_pagamento_id:
        if user_response_payment.lower() not in ["outro / não sei ❓", "outro", "não sei", "nao sei"]:
            try:
                response_add_fp = supabase_client.table('payment_methods').insert({'name': final_payment_method_name}).execute()
                if response_add_fp.data:
                    # Supabase `insert` retorna uma lista de dicionários, pegue o ID do primeiro elemento
                    forma_pagamento_id = response_add_fp.data[0]['id'] 
                    await update.message.reply_text(f"✨ Forma de pagamento '{final_payment_method_name}' adicionada para uso futuro! 💳", reply_markup=ReplyKeyboardRemove())
                else:
                    await update.message.reply_text(f"⚠️ Não foi possível adicionar a forma de pagamento '{final_payment_method_name}'. Usando 'Não Informado'. 😕", reply_markup=ReplyKeyboardRemove())
            except Exception as e:
                print(f"Erro ao adicionar nova forma de pagamento: {e}")
                await update.message.reply_text(f"⚠️ Erro ao adicionar nova forma de pagamento. Usando 'Não Informado'. 😕", reply_markup=ReplyKeyboardRemove())
        
        if not forma_pagamento_id:
            forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, 'NaoInformado')
            final_payment_method_name = 'Não Informado' if forma_pagamento_id else 'Desconhecido'
            if not forma_pagamento_id:
                await update.message.reply_text("🚨 Atenção: A forma de pagamento 'Não Informado' não existe. Gasto registrado sem forma de pagamento. ⚠️", reply_markup=ReplyKeyboardRemove())

    context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
    context.user_data['pending_transaction']['forma_pagamento_nome_real'] = final_payment_method_name
    
    await send_confirmation_message(update, context, context.user_data['pending_transaction'])
    return ASKING_CONFIRMATION
