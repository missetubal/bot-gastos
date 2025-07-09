from telegram import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime

from src.bot.handlers import ASKING_CONFIRMATION, ASKING_CORRECTION
from src.bot.handlers.aux import send_confirmation_message
from src.core.ai import extract_correction_from_llama, extract_transaction_info
from src.core import db
from src.utils.text_utils import to_camel_case


async def handle_correction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a correção de um campo da transação."""
    supabase_client = context.bot_data["supabase_client"]
    correction_text = update.message.text
    pending_transaction = context.user_data.get("pending_transaction")

    if not pending_transaction:
        await update.message.reply_text(
            "Ops! 😬 Não encontrei uma transação pendente para corrigir. 🔄",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    # Extrai o campo e o novo valor da correção usando o Llama
    correction_parsed = extract_correction_from_llama(
        correction_text
    )  # <-- CORREÇÃO AQUI

    if not correction_parsed:
        await update.message.reply_text(
            "Não consegui entender a correção. 😕 Por favor, tente novamente no formato 'Campo Valor'. \n"
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰', 'Data 2025-07-01 📅', 'Forma Pix 💳', 'Descricao Jantar 🍽️'.",
            reply_markup=ReplyKeyboardRemove(),  # Remove keyboard se não entendeu
        )
        return ASKING_CORRECTION

    campo = correction_parsed.get("campo")
    novo_valor = correction_parsed.get("novo_valor")

    if not campo or novo_valor is None:
        await update.message.reply_text(
            "Não consegui identificar o campo e o novo valor da correção. 🤔 \n"
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰'.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASKING_CORRECTION

    # Aplica a correção na transação pendente
    if campo.lower() == "value":
        try:
            pending_transaction["value"] = float(str(novo_valor).replace(",", "."))
            await update.message.reply_text("Valor atualizado! 💰")
        except ValueError:
            await update.message.reply_text(
                "Valor inválido para o campo 'Valor'. Tente novamente. 🔢"
            )
            return ASKING_CORRECTION
    elif campo.lower() == "date":
        try:
            # Valida o formato e atualiza o pending_transaction
            datetime.datetime.strptime(str(novo_valor), "%Y-%m-%d")
            pending_transaction["date"] = str(novo_valor)
            await update.message.reply_text("Data atualizada! 📅")
        except ValueError:
            await update.message.reply_text(
                "Formato de data inválido. Use AAAA-MM-DD. Tente novamente. 🗓️"
            )
            return ASKING_CORRECTION
    elif campo.lower() == "categoria":
        nova_category_id = db.get_category_id_by_text(supabase_client, str(novo_valor))
        if nova_category_id:
            pending_transaction["category_id"] = nova_category_id
            pending_transaction["categoria_nome_db"] = to_camel_case(str(novo_valor))
            await update.message.reply_text("Categoria atualizada! 🏷️")
        else:
            keyboard = [["Sim ✅", "Não ❌"]]
            reply_markup = ReplyKeyboardMarkup(
                keyboard, one_time_keyboard=True, resize_keyboard=True
            )
            context.user_data["pending_transaction_temp_category_name"] = str(
                novo_valor
            )
            await update.message.reply_text(
                f"Categoria '{str(novo_valor)}' não encontrada. Deseja criá-la? ➕",
                reply_markup=reply_markup,
            )
            context.user_data["correction_state"] = (
                "ASKING_CREATE_NEW_CATEGORY"  # Estado temporário para lidar com a sub-resposta
            )
            return ASKING_CORRECTION
    elif campo.lower() == "forma" or campo.lower() == "forma_pagamento":
        nova_forma_id = db.get_payment_method_id_by_name(
            supabase_client, str(novo_valor)
        )
        if nova_forma_id:
            pending_transaction["forma_pagamento_id"] = nova_forma_id
            pending_transaction["forma_pagamento_nome_real"] = to_camel_case(
                str(novo_valor)
            )
            await update.message.reply_text("Forma de pagamento atualizada! 💳")
        else:
            await update.message.reply_text(
                f"Forma de pagamento '{str(novo_valor)}' não encontrada. Verifique `/categorias` ou tente outra. 🤷‍♀️",
                reply_markup=ReplyKeyboardRemove(),
            )
            return ASKING_CORRECTION
    elif campo.lower() == "description" or campo.lower() == "descricao_gasto":
        pending_transaction["descricao_gasto"] = str(novo_valor)
        await update.message.reply_text("Descrição atualizada! 📝")
    elif campo.lower() == "tipo":
        if novo_valor.lower() in ["gasto", "ganho"]:
            pending_transaction["transaction_type"] = novo_valor.lower()
            # Ajusta campos específicos se mudar de tipo
            if novo_valor.lower() == "gasto":
                pending_transaction.pop(
                    "description", None
                )  # Remove 'description' de ganho
                if "category_id" not in pending_transaction:
                    pending_transaction["category_id"] = None
                pending_transaction["descricao_gasto"] = (
                    pending_transaction.get("descricao_gasto") or ""
                )  # Garante que tem a chave para gasto
            else:  # ganho
                pending_transaction.pop("category_id", None)
                pending_transaction.pop("forma_pagamento_id", None)
                pending_transaction.pop("descricao_gasto", None)
                if "description" not in pending_transaction:
                    pending_transaction["description"] = (
                        None  # Garante que tem a chave para ganho
                    )
            await update.message.reply_text(
                f"Tipo de transação alterado para '{novo_valor.lower()}'! 🔄"
            )
        else:
            await update.message.reply_text(
                "Tipo de transação inválido. Use 'gasto' ou 'ganho'. Tente novamente. 🧐"
            )
            return ASKING_CORRECTION
    else:
        await update.message.reply_text(
            f"Campo '{campo}' não reconhecido para correção. Tente novamente com um campo válido. 🤷‍♀️",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASKING_CORRECTION

    # Lógica para criar nova categoria a partir da correção se ASK_CREATE_NEW_CATEGORY
    if context.user_data.get("correction_state") == "ASKING_CREATE_NEW_CATEGORY":
        user_response_sub = update.message.text.lower()
        if user_response_sub == "sim ✅" or user_response_sub == "sim":
            new_category_name_from_correction = context.user_data.get(
                "pending_transaction_temp_category_name"
            )
            if new_category_name_from_correction:
                if db.add_category(
                    supabase_client,
                    new_category_name_from_correction,
                    monthly_limit=None,
                ):
                    new_category_camel_case = to_camel_case(
                        new_category_name_from_correction
                    )
                    new_cat_id = db.get_category_id_by_text(
                        supabase_client, new_category_camel_case
                    )
                    if new_cat_id:
                        pending_transaction["category_id"] = new_cat_id
                        pending_transaction["categoria_nome_db"] = (
                            new_category_camel_case
                        )
                        await update.message.reply_text(
                            f"🎉 Categoria '{new_category_camel_case}' criada e aplicada! ✨",
                            reply_markup=ReplyKeyboardRemove(),
                        )
                    else:
                        await update.message.reply_text(
                            "⚠️ Erro ao aplicar nova categoria. Tente novamente. 😕",
                            reply_markup=ReplyKeyboardRemove(),
                        )
                else:
                    await update.message.reply_text(
                        "⚠️ Erro ao criar nova categoria. Tente novamente. 😕",
                        reply_markup=ReplyKeyboardRemove(),
                    )
            else:
                await update.message.reply_text(
                    "⚠️ Erro: Nome da nova categoria não encontrado. Tente corrigir novamente. 🧐",
                    reply_markup=ReplyKeyboardRemove(),
                )
        else:  # user_response.lower() == 'não' ou outra coisa
            await update.message.reply_text(
                "🚫 Ok, a criação da categoria foi cancelada. Por favor, corrija a categoria para uma existente ou crie-a manualmente depois. 📝",
                reply_markup=ReplyKeyboardRemove(),
            )

        context.user_data.pop("correction_state", None)
        context.user_data.pop("pending_transaction_temp_category_name", None)

    # Se a correção foi aplicada (e não estamos em um sub-estado de criação de categoria), mostra a transação novamente para confirmação
    if context.user_data.get("correction_state") != "ASKING_CREATE_NEW_CATEGORY":
        await send_confirmation_message(update, context, pending_transaction)

    return ASKING_CONFIRMATION  # Retorna para o estado de confirmação após a correção
