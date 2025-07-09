from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.bot.handlers import  ASKING_CONFIRMATION, ASKING_PAYMENT_METHOD
from src.bot.handlers.aux import send_confirmation_message
from src.core import db
from src.utils.text_utils import to_camel_case

async def handle_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com o nome da nova categoria fornecido pelo usuário."""
    supabase_client = context.bot_data['supabase_client']
    new_category_name_input = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    valor = pending_transaction['value']
    data = pending_transaction['date']
    original_category_text = pending_transaction['original_category_text']
    forma_pagamento_text = pending_transaction['forma_pagamento_text']
    descricao_gasto = pending_transaction['descricao_gasto']

    if db.add_category(supabase_client, new_category_name_input, monthly_limit=None):
        new_category_name_camel_case = to_camel_case(new_category_name_input)
        category_id = db.get_category_id_by_text(supabase_client, new_category_name_camel_case)
        
        if category_id:
            context.user_data['pending_transaction']['category_id'] = category_id
            context.user_data['pending_transaction']['categoria_nome_db'] = new_category_name_camel_case
            
            forma_pagamento_id = None
            forma_pagamento_nome_real = None
            if forma_pagamento_text:
                forma_pagamento_normalizada = to_camel_case(forma_pagamento_text)
                formas_pagamento_db_info = db.get_formas_pagamento(supabase_client)
                for fp in formas_pagamento_db_info:
                    if fp['name'] == forma_pagamento_normalizada:
                        forma_pagamento_id = fp['id']
                        forma_pagamento_nome_real = fp['name']
                        break

            if not forma_pagamento_id:
                formas_pagamento_disponiveis = db.get_formas_pagamento(supabase_client)
                keyboard_options = [[fp['name']] for fp in formas_pagamento_disponiveis]
                keyboard_options.append(["Outro / Não sei ❓"])
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "💳 Qual foi a forma de pagamento?",
                    reply_markup=reply_markup
                )
                return ASKING_PAYMENT_METHOD
            else:
                # Tudo resolvido, vai para a confirmação
                context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
                context.user_data['pending_transaction']['forma_pagamento_nome_real'] = forma_pagamento_nome_real
                await send_confirmation_message(update, context, context.user_data['pending_transaction'])
                return ASKING_CONFIRMATION

        else:
            nome_existente_camel_case = to_camel_case(new_category_name_input)
            await update.message.reply_text(f"⚠️ Não foi possível criar a categoria '{nome_existente_camel_case}'. Ela já existe ou houve um erro. Por favor, tente novamente ou escolha uma categoria existente. 🧐", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
  