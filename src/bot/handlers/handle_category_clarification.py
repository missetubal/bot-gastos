from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from src.bot.handlers import ASKING_CATEGORY_CLARIFICATION, ASKING_CONFIRMATION, ASKING_NEW_CATEGORY_NAME, ASKING_PAYMENT_METHOD
from src.bot.handlers.aux import send_confirmation_message
from src.core import db
from src.utils.text_utils import to_camel_case
async def handle_category_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a resposta do usuário à clarificação da categoria."""
    supabase_client = context.bot_data['supabase_client']
    user_response = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    valor = pending_transaction['valor']
    data = pending_transaction['data']
    original_category_text = pending_transaction['original_category_text']
    suggestions = pending_transaction['suggestions']
    forma_pagamento_text = pending_transaction['forma_pagamento_text']
    descricao_gasto = pending_transaction['descricao_gasto']

    chosen_category_id = None
    chosen_category_name = None

    user_response_camel_case = to_camel_case(user_response)

    for suggestion in suggestions:
        if user_response_camel_case == suggestion['nome']:
            chosen_category_id = suggestion['id']
            chosen_category_name = suggestion['nome']
            break
    
    if not chosen_category_id:
        all_categorias = db.get_categorias(supabase_client)
        for cat in all_categorias:
            if user_response_camel_case == cat['nome']:
                chosen_category_id = cat['id']
                chosen_category_name = cat['nome']
                break

    if chosen_category_id:
        context.user_data['pending_transaction']['categoria_id'] = chosen_category_id
        context.user_data['pending_transaction']['categoria_nome_db'] = chosen_category_name
        
        # Categoria resolvida. Agora verifica a forma de pagamento.
        forma_pagamento_id = None
        forma_pagamento_nome_real = None
        if forma_pagamento_text:
            forma_pagamento_normalizada = to_camel_case(forma_pagamento_text)
            formas_pagamento_db_info = db.get_formas_pagamento(supabase_client)
            for fp in formas_pagamento_db_info:
                if fp['nome'] == forma_pagamento_normalizada:
                    forma_pagamento_id = fp['id']
                    forma_pagamento_nome_real = fp['nome']
                    break
        
        if not forma_pagamento_id:
            formas_pagamento_disponiveis = db.get_formas_pagamento(supabase_client)
            keyboard_options = [[fp['nome']] for fp in formas_pagamento_disponiveis]
            keyboard_options.append(["Outro / Não sei ❓"])
            reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "💳 Qual foi a forma de pagamento?",
                reply_markup=reply_markup
            )
            return ASKING_PAYMENT_METHOD
        else:
            # Se tudo foi resolvido, vai para a confirmação
            context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
            context.user_data['pending_transaction']['forma_pagamento_nome_real'] = forma_pagamento_nome_real
            await send_confirmation_message(update, context, context.user_data['pending_transaction'])
            return ASKING_CONFIRMATION

    elif user_response.lower() == "criar nova categoria ➕":
        await update.message.reply_text("📝 Ok, qual o nome da nova categoria para este gasto?", reply_markup=ReplyKeyboardRemove())
        return ASKING_NEW_CATEGORY_NAME

    elif user_response.lower() == "não se aplica / outra 🤷‍♀️":
        await update.message.reply_text("✍️ Entendi. Por favor, digite o nome da categoria correta para este gasto.", reply_markup=ReplyKeyboardRemove())
        return ASKING_NEW_CATEGORY_NAME

    else:
        await update.message.reply_text(
            f"🤔 Não entendi sua resposta. Por favor, digite o nome exato de uma das sugestões, "
            f"ou 'Criar nova categoria ➕' ou 'Não se aplica / Outra 🤷‍♀️'.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASKING_CATEGORY_CLARIFICATION
