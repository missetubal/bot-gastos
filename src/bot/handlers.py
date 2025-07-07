# src/bot/handlers.py
import datetime
from typing import Union, Dict, Any, List
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from src.core import ai 
from src.core import db
from src.utils.text_utils import to_camel_case
from src.core import charts

# --- Estados da Conversa ---
HANDLE_INITIAL_MESSAGE = 0
ASKING_CATEGORY_CLARIFICATION = 1
ASKING_NEW_CATEGORY_NAME = 2
ASKING_PAYMENT_METHOD = 3
ASKING_CONFIRMATION = 4
ASKING_CORRECTION = 5

# --- Funções Auxiliares (para não repetir código) ---
async def _send_confirmation_message(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]) -> None:
    """Envia a mensagem de confirmação da transação ao usuário com emojis."""
    supabase_client = context.bot_data['supabase_client']
    valor_fmt = f"R${transaction_info['valor']:.2f}"
    data_fmt = transaction_info['data']
    
    # Resolva o nome real da categoria
    categoria_nome_real = transaction_info.get('categoria_nome_db') or transaction_info.get('categoria')
    if transaction_info.get('categoria_id') and not transaction_info.get('categoria_nome_db'):
        cat_info = next((c for c in db.get_categorias(supabase_client) if c['id'] == transaction_info['categoria_id']), None)
        if cat_info:
            categoria_nome_real = cat_info['nome']
    
    # Resolva o nome real da forma de pagamento
    forma_pagamento_nome_real = transaction_info.get('forma_pagamento_nome_real') or transaction_info.get('forma_pagamento_text')
    if transaction_info.get('forma_pagamento_id') and not transaction_info.get('forma_pagamento_nome_real'):
        fp_info = next((f for f in db.get_formas_pagamento(supabase_client) if f['id'] == transaction_info['forma_pagamento_id']), None)
        if fp_info:
            forma_pagamento_nome_real = fp_info['nome']

    descricao_gasto_fmt = f" ({transaction_info.get('descricao_gasto', 'sem detalhes')})" if transaction_info.get('descricao_gasto') else ""

    message_text = ""
    if transaction_info['transaction_type'] == 'gasto':
        message_text = (
            f"💸 Entendi que você teve um *gasto de {valor_fmt}{descricao_gasto_fmt}* "
            f"na categoria *{categoria_nome_real}* 🛍️, "
            f"em *{data_fmt}* 📅, via *{forma_pagamento_nome_real or 'Não Informado'}*."
        )
    elif transaction_info['transaction_type'] == 'ganho':
        message_text = (
            f"💰 Que maravilha! Você registrou um *ganho de {valor_fmt}* "
            f"referente a *{transaction_info.get('descricao')}* ✨, "
            f"em *{data_fmt}* 📅."
        )
    
    keyboard = [["Sim ✅", "Não ❌"]] # Adicionado emojis nos botões também
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(f"{message_text}\n\n*Está tudo certinho?* 🤔", reply_markup=reply_markup, parse_mode='Markdown')


async def _register_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]) -> None:
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
        # Adiciona alias para a categoria se necessário
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

async def _register_ganho(update: Update, context: ContextTypes.DEFAULT_TYPE, transaction_info: Dict[str, Any]) -> None:
    """Registra um ganho no banco de dados e envia a confirmação."""
    supabase_client = context.bot_data['supabase_client']
    valor = transaction_info['valor']
    data = transaction_info['data']
    descricao = transaction_info['descricao']

    if db.add_ganho(supabase_client, valor, descricao, data):
        await update.message.reply_text(f"✅ Ganho de R${valor:.2f} de '{descricao}' registrado com sucesso! 🥳", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("❌ Ocorreu um erro ao registrar seu ganho. Tente novamente mais tarde. 😟", reply_markup=ReplyKeyboardRemove())


# --- Handlers Principais ---
async def handle_initial_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, None]:
    supabase_client = context.bot_data['supabase_client']
    user_message = update.message.text
    chat_id = update.message.chat_id

    print(f"Mensagem recebida de {chat_id}: {user_message}")

    if not user_message:
        return ConversationHandler.END # Não faz nada se a mensagem for vazia

    parsed_info: Union[Dict[str, Any], None] = ai.extract_transaction_info(user_message, supabase_client)

    if not parsed_info:
        await update.message.reply_text(
            "😕 Desculpe, não consegui entender sua mensagem. "
            "Por favor, tente descrever claramente sua intenção (gasto, ganho, adicionar categoria, mostrar balanço/gráfico). "
            "Se precisar de ajuda, use /help. 💡"
        )
        return ConversationHandler.END

    intencao = parsed_info.get('intencao')

    # --- Lógica para Adicionar Categoria ---
    if intencao == 'adicionar_categoria':
        categoria_nome_input = parsed_info.get('categoria_nome')
        limite_mensal = parsed_info.get('limite_mensal')

        if not categoria_nome_input:
            await update.message.reply_text("🤔 Não consegui identificar o nome da categoria que você quer adicionar.")
            return ConversationHandler.END

        if db.add_categoria(supabase_client, categoria_nome_input, limite_mensal=limite_mensal):
            nome_exibicao = to_camel_case(categoria_nome_input)
            limite_msg = f" com limite de R${limite_mensal:.2f}" if limite_mensal is not None and limite_mensal > 0 else ""
            await update.message.reply_text(f"🎉 Categoria '{nome_exibicao}' adicionada{limite_msg} com sucesso!")
        else:
            nome_exibicao = to_camel_case(categoria_nome_input)
            await update.message.reply_text(f"⚠️ Erro ao adicionar categoria '{nome_exibicao}'. Ela já existe ou ocorreu um problema. Tente outro nome! 🧐")
        return ConversationHandler.END # Fim da conversa

    # --- Lógica para Registrar Gasto ou Ganho (iniciar fluxo de confirmação) ---
    elif intencao == 'gasto' or intencao == 'ganho':
        context.user_data['pending_transaction'] = parsed_info
        
        # Para gastos, prepare mais dados para o user_data
        if intencao == 'gasto':
            valor = float(parsed_info['valor'])
            data = parsed_info.get('data', str(datetime.date.today()))
            categoria_texto_llama = parsed_info.get('categoria', 'Outros') or 'Outros' 
            forma_pagamento_text = parsed_info.get('forma_pagamento')
            descricao_gasto = parsed_info.get('descricao_gasto', user_message)

            context.user_data['pending_transaction'].update({
                'valor': valor,
                'data': data,
                'original_category_text': categoria_texto_llama,
                'forma_pagamento_text': forma_pagamento_text,
                'descricao_gasto': descricao_gasto,
                'transaction_type': 'gasto'
            })
            
            # Tenta resolver categoria e forma de pagamento ANTES da confirmação
            # Lógica de Categoria
            categoria_id = db.get_categoria_id_by_text(supabase_client, categoria_texto_llama)
            if categoria_id:
                context.user_data['pending_transaction']['categoria_id'] = categoria_id
                context.user_data['pending_transaction']['categoria_nome_db'] = next((cat['nome'] for cat in db.get_categorias(supabase_client) if cat['id'] == categoria_id), categoria_texto_llama)
            else:
                # Se não encontrou, volta para o estado de clarificação de categoria
                similar_categories = db.find_similar_categories(supabase_client, categoria_texto_llama)
                context.user_data['pending_transaction']['suggestions'] = similar_categories
                
                keyboard_options = [[cat['nome']] for cat in similar_categories]
                keyboard_options.append(["Criar nova categoria ➕", "Não se aplica / Outra 🤷‍♀️"])
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    f"🧐 Não encontrei uma categoria exata para '{categoria_texto_llama}'. "
                    f"Seria uma destas? Se sim, clique ou digite o nome. "
                    f"Ou você pode 'Criar nova categoria ➕' ou 'Não se aplica / Outra 🤷‍♀️'.",
                    reply_markup=reply_markup
                )
                return ASKING_CATEGORY_CLARIFICATION # Entra no estado de clarificação
            
            # Lógica de Forma de Pagamento (somente se a categoria já foi resolvida)
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
                # Se não identificou a FP, guarda como pendente e passa para o estado de FP
                formas_pagamento_disponiveis = db.get_formas_pagamento(supabase_client)
                keyboard_options = [[fp['nome']] for fp in formas_pagamento_disponiveis]
                keyboard_options.append(["Outro / Não sei ❓"])
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "💳 Qual foi a forma de pagamento?",
                    reply_markup=reply_markup
                )
                return ASKING_PAYMENT_METHOD # Entra no estado de pedir FP

            # Se tudo foi resolvido pelo Llama, vai direto para a confirmação
            context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
            context.user_data['pending_transaction']['forma_pagamento_nome_real'] = forma_pagamento_nome_real
            
        elif intencao == 'ganho':
            # Para ganhos, as informações são mais simples, vai direto para confirmação
            valor = float(parsed_info['valor'])
            data = parsed_info.get('data', str(datetime.date.today()))
            descricao = parsed_info.get('descricao', 'Diversos')
            context.user_data['pending_transaction'].update({
                'valor': valor,
                'data': data,
                'descricao': descricao,
                'transaction_type': 'ganho'
            })
            
        # Se chegou até aqui, as informações da transação estão no user_data,
        # e não precisamos de mais clarificações (categoria ou FP)
        await _send_confirmation_message(update, context, context.user_data['pending_transaction'])
        return ASKING_CONFIRMATION # Pede confirmação

    # --- Lógica para Mostrar Gráficos ---
    elif intencao in ['mostrar_balanco', 'mostrar_grafico_gastos_categoria', 'mostrar_grafico_gastos_por_pagamento', 'mostrar_grafico_mensal_combinado']:
        data_inicio = parsed_info.get('data_inicio')
        data_fim = parsed_info.get('data_fim')
        
        # Para gráficos com filtro de FP ou Categoria, resolve os IDs
        forma_pagamento_id = None
        categoria_id = None
        
        if intencao == 'mostrar_grafico_gastos_categoria':
            forma_pagamento_text = parsed_info.get('forma_pagamento')
            if forma_pagamento_text:
                forma_pagamento_normalizada = to_camel_case(forma_pagamento_text)
                forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, forma_pagamento_normalizada)
                if not forma_pagamento_id:
                    await update.message.reply_text(f"⚠️ Forma de pagamento '{forma_pagamento_text}' não reconhecida. Gerando gráfico sem este filtro. 📊")
            chart_buffer = charts.generate_category_spending_chart(supabase_client, forma_pagamento_id=forma_pagamento_id, data_inicio=data_inicio, data_fim=data_fim)
            title = "Gastos por Categoria"
        
        elif intencao == 'mostrar_grafico_gastos_por_pagamento':
            categoria_texto_llama = parsed_info.get('categoria')
            if categoria_texto_llama:
                categoria_id = db.get_categoria_id_by_text(supabase_client, categoria_texto_llama)
                if not categoria_id:
                    await update.message.reply_text(f"⚠️ Categoria '{categoria_texto_llama}' não reconhecida. Gerando gráfico sem este filtro. 📊")
            chart_buffer = charts.generate_payment_method_spending_chart(supabase_client, categoria_id=categoria_id, data_inicio=data_inicio, data_fim=data_fim)
            title = "Gastos por Forma de Pagamento"
        
        elif intencao == 'mostrar_balanco':
            chart_buffer = charts.generate_balance_chart(supabase_client, data_inicio=data_inicio, data_fim=data_fim)
            title = "Balanço Mensal"
        
        elif intencao == 'mostrar_grafico_mensal_combinado':
            chart_buffer = charts.generate_monthly_category_payment_chart(supabase_client, data_inicio=data_inicio, data_fim=data_fim)
            title = "Gastos Mensais Combinados"

        else: # Isso não deve acontecer com a lógica do Llama
            await update.message.reply_text("🤔 Não consegui identificar o tipo de gráfico. Use `/help` para ver as opções. 💡")
            return ConversationHandler.END

        # Envia o gráfico
        if chart_buffer:
            await update.message.reply_photo(photo=chart_buffer, caption=f"📊 Aqui está seu gráfico de {title}:")
        else:
            await update.message.reply_text(f"📉 Ainda não tenho dados suficientes para gerar este gráfico. Registre mais transações primeiro! 📝")
        
        return ConversationHandler.END

    else:
        await update.message.reply_text(
            "🤔 Não consegui entender sua intenção. Por favor, tente descrever claramente "
            "um gasto, um ganho, a adição de uma categoria ou o pedido de um gráfico. 💡"
        )
        return ConversationHandler.END

# --- Handlers para os Estados da Conversa ---

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
        
        # Se a forma de pagamento NÃO foi resolvida (pelo Llama ou pela resposta do usuário)
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
            await _send_confirmation_message(update, context, context.user_data['pending_transaction'])
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


async def handle_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com o nome da nova categoria fornecido pelo usuário."""
    supabase_client = context.bot_data['supabase_client']
    new_category_name_input = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    valor = pending_transaction['valor']
    data = pending_transaction['data']
    original_category_text = pending_transaction['original_category_text']
    forma_pagamento_text = pending_transaction['forma_pagamento_text']
    descricao_gasto = pending_transaction['descricao_gasto']

    if db.add_categoria(supabase_client, new_category_name_input, limite_mensal=None):
        new_category_name_camel_case = to_camel_case(new_category_name_input)
        categoria_id = db.get_categoria_id_by_text(supabase_client, new_category_name_camel_case)
        
        if categoria_id:
            context.user_data['pending_transaction']['categoria_id'] = categoria_id
            context.user_data['pending_transaction']['categoria_nome_db'] = new_category_name_camel_case
            
            # Categoria criada e resolvida. Agora verifica a forma de pagamento.
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
                # Tudo resolvido, vai para a confirmação
                context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
                context.user_data['pending_transaction']['forma_pagamento_nome_real'] = forma_pagamento_nome_real
                await _send_confirmation_message(update, context, context.user_data['pending_transaction'])
                return ASKING_CONFIRMATION

        else:
            nome_existente_camel_case = to_camel_case(new_category_name_input)
            await update.message.reply_text(f"⚠️ Não foi possível criar a categoria '{nome_existente_camel_case}'. Ela já existe ou houve um erro. Por favor, tente novamente ou escolha uma categoria existente. 🧐", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a forma de pagamento fornecida pelo usuário."""
    supabase_client = context.bot_data['supabase_client']
    user_response_payment = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    
    valor = pending_transaction['valor']
    data = pending_transaction['data']
    categoria_id = pending_transaction['categoria_id']
    categoria_nome_db = pending_transaction['categoria_nome_db']
    original_category_text = pending_transaction['original_category_text']
    descricao_gasto = pending_transaction['descricao_gasto']

    final_payment_method_name = to_camel_case(user_response_payment)
    forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, final_payment_method_name)

    if not forma_pagamento_id:
        if user_response_payment.lower() not in ["outro / não sei ❓", "outro", "não sei", "nao sei"]:
            try:
                response_add_fp = supabase_client.table('formas_pagamento').insert({'nome': final_payment_method_name}).execute()
                if response_add_fp.data:
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
    
    await _send_confirmation_message(update, context, context.user_data['pending_transaction'])
    return ASKING_CONFIRMATION


async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a confirmação (Sim/Não) da transação."""
    user_response = update.message.text.lower()
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente para confirmar. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if user_response == 'sim ✅' or user_response == 'sim':
        if pending_transaction['transaction_type'] == 'gasto':
            await _register_gasto(update, context, pending_transaction)
        elif pending_transaction['transaction_type'] == 'ganho':
            await _register_ganho(update, context, pending_transaction)
        
        context.user_data.pop('pending_transaction', None) # Limpa a transação pendente
        return ConversationHandler.END # Fim da conversa

    elif user_response == 'não ❌' or user_response == 'não' or user_response == 'nao':
        await update.message.reply_text(
            "Entendido! 🤔 O que precisa ser alterado? "
            "Por favor, digite o campo e o novo valor. "
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰', 'Data 2025-07-01 📅', 'Forma Pix 💳', 'Descricao Jantar de Aniversário 🎂'.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASKING_CORRECTION # Entra no estado de correção

    else:
        keyboard = [["Sim ✅", "Não ❌"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            "Por favor, responda apenas 'Sim ✅' ou 'Não ❌'.",
            reply_markup=reply_markup
        )
        return ASKING_CONFIRMATION # Permanece no estado de confirmação


async def handle_correction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Lida com a correção de um campo da transação."""
    supabase_client = context.bot_data['supabase_client']
    correction_text = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Ops! 😬 Não encontrei uma transação pendente para corrigir. 🔄", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    # Extrai o campo e o novo valor da correção usando o Llama
    correction_parsed = ai.extract_correction_from_llama(correction_text)

    if not correction_parsed:
        await update.message.reply_text(
            "Não consegui entender a correção. 😕 Por favor, tente novamente no formato 'Campo Valor'. "
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰', 'Data 2025-07-01 📅', 'Forma Pix 💳', 'Descricao Jantar 🍽️'.",
            reply_markup=ReplyKeyboardRemove() # Remove keyboard se não entendeu
        )
        return ASKING_CORRECTION

    campo = correction_parsed.get('campo')
    novo_valor = correction_parsed.get('novo_valor')

    if not campo or novo_valor is None:
        await update.message.reply_text(
            "Não consegui identificar o campo e o novo valor da correção. 🤔 "
            "Exemplos: 'Categoria Lazer 🛍️', 'Valor 60.50 💰'.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASKING_CORRECTION

    # Aplica a correção na transação pendente
    if campo.lower() == 'valor':
        try:
            pending_transaction['valor'] = float(str(novo_valor).replace(',', '.'))
            await update.message.reply_text("Valor atualizado! 💰")
        except ValueError:
            await update.message.reply_text("Valor inválido para o campo 'Valor'. Tente novamente. 🔢")
            return ASKING_CORRECTION
    elif campo.lower() == 'data':
        try:
            datetime.datetime.strptime(str(novo_valor), '%Y-%m-%d') # Valida o formato
            pending_transaction['data'] = str(novo_valor)
            await update.message.reply_text("Data atualizada! 📅")
        except ValueError:
            await update.message.reply_text("Formato de data inválido. Use AAAA-MM-DD. Tente novamente. 🗓️")
            return ASKING_CORRECTION
    elif campo.lower() == 'categoria':
        nova_categoria_id = db.get_categoria_id_by_text(supabase_client, str(novo_valor))
        if nova_categoria_id:
            pending_transaction['categoria_id'] = nova_categoria_id
            pending_transaction['categoria_nome_db'] = to_camel_case(str(novo_valor))
            await update.message.reply_text("Categoria atualizada! 🏷️")
        else:
            keyboard = [["Sim ✅", "Não ❌"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            context.user_data['pending_transaction_temp_category_name'] = str(novo_valor)
            await update.message.reply_text(f"Categoria '{str(novo_valor)}' não encontrada. Deseja criá-la? ➕", reply_markup=reply_markup)
            context.user_data['correction_state'] = 'ASKING_CREATE_NEW_CATEGORY' # Estado temporário para lidar com a sub-resposta
            return ASKING_CORRECTION
    elif campo.lower() == 'forma' or campo.lower() == 'forma_pagamento':
        nova_forma_id = db.get_forma_pagamento_id_by_name(supabase_client, str(novo_valor))
        if nova_forma_id:
            pending_transaction['forma_pagamento_id'] = nova_forma_id
            pending_transaction['forma_pagamento_nome_real'] = to_camel_case(str(novo_valor))
            await update.message.reply_text("Forma de pagamento atualizada! 💳")
        else:
            await update.message.reply_text(f"Forma de pagamento '{str(novo_valor)}' não encontrada. Verifique `/categorias` ou tente outra. 🤷‍♀️", reply_markup=ReplyKeyboardRemove())
            return ASKING_CORRECTION
    elif campo.lower() == 'descricao' or campo.lower() == 'descricao_gasto':
        pending_transaction['descricao_gasto'] = str(novo_valor)
        await update.message.reply_text("Descrição atualizada! 📝")
    elif campo.lower() == 'tipo':
        if novo_valor.lower() in ['gasto', 'ganho']:
            pending_transaction['transaction_type'] = novo_valor.lower()
            # Ajusta campos específicos se mudar de tipo
            if novo_valor.lower() == 'gasto':
                pending_transaction.pop('descricao', None)
                if 'categoria_id' not in pending_transaction: pending_transaction['categoria_id'] = None
            else: # ganho
                pending_transaction.pop('categoria_id', None)
                pending_transaction.pop('forma_pagamento_id', None)
                pending_transaction.pop('descricao_gasto', None)
                if 'descricao' not in pending_transaction: pending_transaction['descricao'] = None # Garante que tem a chave para ganho
            await update.message.reply_text(f"Tipo de transação alterado para '{novo_valor.lower()}'! 🔄")
        else:
            await update.message.reply_text("Tipo de transação inválido. Use 'gasto' ou 'ganho'. Tente novamente. 🧐")
            return ASKING_CORRECTION
    else:
        await update.message.reply_text(f"Campo '{campo}' não reconhecido para correção. Tente novamente com um campo válido. 🤷‍♀️", reply_markup=ReplyKeyboardRemove())
        return ASKING_CORRECTION

    # Lógica para criar nova categoria a partir da correção se ASK_CREATE_NEW_CATEGORY
    if context.user_data.get('correction_state') == 'ASKING_CREATE_NEW_CATEGORY':
        user_response_sub = update.message.text.lower()
        if user_response_sub == 'sim ✅' or user_response_sub == 'sim':
            new_category_name_from_correction = context.user_data.get('pending_transaction_temp_category_name')
            if new_category_name_from_correction:
                if db.add_categoria(supabase_client, new_category_name_from_correction, limite_mensal=None):
                    new_category_camel_case = to_camel_case(new_category_name_from_correction)
                    new_cat_id = db.get_categoria_id_by_text(supabase_client, new_category_camel_case)
                    if new_cat_id:
                        pending_transaction['categoria_id'] = new_cat_id
                        pending_transaction['categoria_nome_db'] = new_category_camel_case
                        await update.message.reply_text(f"🎉 Categoria '{new_category_camel_case}' criada e aplicada! ✨", reply_markup=ReplyKeyboardRemove())
                    else:
                        await update.message.reply_text("⚠️ Erro ao aplicar nova categoria. Tente novamente. 😕", reply_markup=ReplyKeyboardRemove())
                else:
                    await update.message.reply_text("⚠️ Erro ao criar nova categoria. Tente novamente. 😕", reply_markup=ReplyKeyboardRemove())
            else:
                await update.message.reply_text("⚠️ Erro: Nome da nova categoria não encontrado. Tente corrigir novamente. 🧐", reply_markup=ReplyKeyboardRemove())
        else: # user_response.lower() == 'não' ou outra coisa
            await update.message.reply_text("🚫 Ok, a criação da categoria foi cancelada. Por favor, corrija a categoria para uma existente ou crie-a manualmente depois. 📝", reply_markup=ReplyKeyboardRemove())
        
        context.user_data.pop('correction_state', None)
        context.user_data.pop('pending_transaction_temp_category_name', None)


    # Se a correção foi aplicada (e não estamos em um sub-estado de criação de categoria), mostra a transação novamente para confirmação
    if context.user_data.get('correction_state') != 'ASKING_CREATE_NEW_CATEGORY':
        await _send_confirmation_message(update, context, pending_transaction)
    
    return ASKING_CONFIRMATION # Retorna para o estado de confirmação após a correção