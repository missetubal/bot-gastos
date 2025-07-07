# src/bot/handlers.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from typing import Union, Dict, Any, List

from src.core.ai import extract_transaction_info
from src.core import db
from src.utils.text_utils import to_camel_case
from src.core import charts

# Estados da conversa
ASKING_CATEGORY_CLARIFICATION = 1
ASKING_NEW_CATEGORY_NAME = 2
ASKING_PAYMENT_METHOD = 3

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, None]:
    supabase_client = context.bot_data['supabase_client']
    user_message = update.message.text
    chat_id = update.message.chat_id

    print(f"Mensagem recebida de {chat_id}: {user_message}")

    if user_message:
        parsed_info: Union[Dict[str, Any], None] = extract_transaction_info(user_message)

        if not parsed_info:
            await update.message.reply_text(
                "Desculpe, não consegui entender sua mensagem. "
                "Por favor, tente descrever claramente sua intenção (gasto, ganho, adicionar categoria, mostrar balanço/gráfico)."
            )
            return ConversationHandler.END

        intencao = parsed_info.get('intencao')

        if intencao == 'adicionar_categoria':
            categoria_nome_input = parsed_info.get('categoria_nome')
            limite_mensal = parsed_info.get('limite_mensal')

            if not categoria_nome_input:
                await update.message.reply_text("Não consegui identificar o nome da categoria que você quer adicionar.")
                return ConversationHandler.END

            if db.add_categoria(supabase_client, categoria_nome_input, limite_mensal=limite_mensal):
                nome_exibicao = to_camel_case(categoria_nome_input)
                limite_msg = f" com limite de R${limite_mensal:.2f}" if limite_mensal is not None and limite_mensal > 0 else ""
                await update.message.reply_text(f"Categoria '{nome_exibicao}' adicionada{limite_msg} com sucesso!")
            else:
                nome_exibicao = to_camel_case(categoria_nome_input)
                await update.message.reply_text(f"Erro ao adicionar categoria '{nome_exibicao}'. Ela já existe ou ocorreu um problema.")
            return ConversationHandler.END

        elif intencao == 'gasto':
            valor = float(parsed_info['valor'])
            data = parsed_info.get('data', str(datetime.date.today()))
            categoria_texto_llama = parsed_info.get('categoria', 'Outros') or 'Outros' 
            forma_pagamento_text = parsed_info.get('forma_pagamento')
            descricao_gasto = parsed_info.get('descricao_gasto', user_message)

            context.user_data['pending_transaction'] = {
                'valor': valor,
                'data': data,
                'original_category_text': categoria_texto_llama,
                'forma_pagamento_text': forma_pagamento_text,
                'descricao_gasto': descricao_gasto,
                'transaction_type': 'gasto'
            }
            
            categoria_id = db.get_categoria_id_by_text(supabase_client, categoria_texto_llama)
            
            if not categoria_id:
                similar_categories = db.find_similar_categories(supabase_client, categoria_texto_llama)
                context.user_data['pending_transaction']['suggestions'] = similar_categories
                
                keyboard_options = [[cat['nome']] for cat in similar_categories]
                keyboard_options.append(["Criar nova categoria", "Não se aplica / Outra"])
                
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    f"Não encontrei uma categoria exata para '{categoria_texto_llama}'. "
                    f"Seria uma destas? Se sim, clique ou digite o nome. "
                    f"Ou você pode 'Criar nova categoria' ou 'Não se aplica / Outra'.",
                    reply_markup=reply_markup
                )
                return ASKING_CATEGORY_CLARIFICATION
            else:
                context.user_data['pending_transaction']['categoria_id'] = categoria_id
                context.user_data['pending_transaction']['categoria_nome_db'] = next((cat['nome'] for cat in db.get_categorias(supabase_client) if cat['id'] == categoria_id), categoria_texto_llama)

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
                    keyboard_options.append(["Outro / Não sei"])
                    
                    reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                    await update.message.reply_text(
                        "Qual foi a forma de pagamento?",
                        reply_markup=reply_markup
                    )
                    return ASKING_PAYMENT_METHOD
                else:
                    if db.add_gasto(supabase_client, valor, categoria_id, data, forma_pagamento_id, descricao_gasto):
                        await update.message.reply_text(f"Gasto de R${valor:.2f} ({descricao_gasto}) em '{context.user_data['pending_transaction']['categoria_nome_db']}' via '{forma_pagamento_nome_real}' registrado com sucesso!", reply_markup=ReplyKeyboardRemove())
                    else:
                        await update.message.reply_text("Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde.", reply_markup=ReplyKeyboardRemove())
                    context.user_data.pop('pending_transaction', None)
                    return ConversationHandler.END

        elif intencao == 'ganho':
            valor = float(parsed_info['valor'])
            data = parsed_info.get('data', str(datetime.date.today()))
            descricao = parsed_info.get('descricao', 'Diversos')

            if db.add_ganho(supabase_client, valor, descricao, data):
                await update.message.reply_text(f"Ganho de R${valor:.2f} de '{descricao}' registrado com sucesso!")
            else:
                await update.message.reply_text("Ocorreu um erro ao registrar seu ganho. Tente novamente mais tarde.")
            return ConversationHandler.END

        elif intencao == 'mostrar_balanco':
            data_inicio = parsed_info.get('data_inicio')
            data_fim = parsed_info.get('data_fim')
            
            await update.message.reply_text("Gerando seu balanço mensal, por favor aguarde...")
            chart_buffer = charts.generate_balance_chart(supabase_client, data_inicio=data_inicio, data_fim=data_fim)
            if chart_buffer:
                chart_buffer.name = 'balanco_chart.png'
                await update.message.reply_photo(photo=chart_buffer, caption="Aqui está seu balanço mensal:")
            else:
                await update.message.reply_text("Ainda não tenho dados suficientes para gerar um balanço. Registre alguns gastos e ganhos primeiro!")
            return ConversationHandler.END

        elif intencao == 'mostrar_grafico_gastos_categoria':
            forma_pagamento_text = parsed_info.get('forma_pagamento')
            data_inicio = parsed_info.get('data_inicio')
            data_fim = parsed_info.get('data_fim')

            forma_pagamento_id = None
            if forma_pagamento_text:
                forma_pagamento_normalizada = to_camel_case(forma_pagamento_text)
                forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, forma_pagamento_normalizada)
                if not forma_pagamento_id:
                    await update.message.reply_text(f"Forma de pagamento '{forma_pagamento_text}' não reconhecida. Gerando gráfico sem este filtro.")
            
            await update.message.reply_text("Gerando o gráfico de gastos por categoria, por favor aguarde...")
            chart_buffer = charts.generate_category_spending_chart(
                supabase_client, 
                forma_pagamento_id=forma_pagamento_id, 
                data_inicio=data_inicio, 
                data_fim=data_fim
            )
            if chart_buffer:
                chart_buffer.name = 'gastos_por_categoria_chart.png'
                await update.message.reply_photo(photo=chart_buffer, caption="Aqui estão seus gastos por categoria:")
            else:
                await update.message.reply_text("Ainda não tenho dados suficientes para gerar um gráfico de categorias. Registre alguns gastos primeiro!")
            return ConversationHandler.END

        elif intencao == 'mostrar_grafico_gastos_por_pagamento':
            categoria_texto_llama = parsed_info.get('categoria')
            data_inicio = parsed_info.get('data_inicio')
            data_fim = parsed_info.get('data_fim')

            categoria_id = None
            if categoria_texto_llama:
                categoria_id = db.get_categoria_id_by_text(supabase_client, categoria_texto_llama)
                if not categoria_id:
                    await update.message.reply_text(f"Categoria '{categoria_texto_llama}' não reconhecida. Gerando gráfico sem este filtro.")
            
            await update.message.reply_text("Gerando o gráfico de gastos por forma de pagamento, por favor aguarde...")
            chart_buffer = charts.generate_payment_method_spending_chart(
                supabase_client, 
                categoria_id=categoria_id, 
                data_inicio=data_inicio, 
                data_fim=data_fim
            )
            if chart_buffer:
                chart_buffer.name = 'gastos_por_pagamento_chart.png'
                await update.message.reply_photo(photo=chart_buffer, caption="Aqui estão seus gastos por forma de pagamento:")
            else:
                await update.message.reply_text("Ainda não tenho dados suficientes para gerar um gráfico de formas de pagamento. Registre alguns gastos primeiro!")
            return ConversationHandler.END
        
        # --- NOVA Lógica para Mostrar Gráfico Mensal Combinado ---
        elif intencao == 'mostrar_grafico_mensal_combinado':
            data_inicio = parsed_info.get('data_inicio')
            data_fim = parsed_info.get('data_fim')
            
            await update.message.reply_text("Gerando o gráfico mensal combinado, por favor aguarde...")
            chart_buffer = charts.generate_monthly_category_payment_chart(
                supabase_client, 
                data_inicio=data_inicio, 
                data_fim=data_fim
            )
            if chart_buffer:
                chart_buffer.name = 'gastos_mensal_combinado_chart.png'
                await update.message.reply_photo(photo=chart_buffer, caption="Aqui está seu gráfico mensal por categoria e forma de pagamento:")
            else:
                await update.message.reply_text("Ainda não tenho dados suficientes para gerar este gráfico combinado. Registre alguns gastos primeiro!")
            return ConversationHandler.END

        else:
            await update.message.reply_text(
                "Não consegui entender sua intenção. Por favor, tente descrever claramente "
                "um gasto, um ganho, a adição de uma categoria ou o pedido de um gráfico."
            )
            return ConversationHandler.END
    return ConversationHandler.END


async def handle_category_clarification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    supabase_client = context.bot_data['supabase_client']
    user_response = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Desculpe, não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente.", reply_markup=ReplyKeyboardRemove())
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
            keyboard_options.append(["Outro / Não sei"])
            reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text(
                "Qual foi a forma de pagamento?",
                reply_markup=reply_markup
            )
            return ASKING_PAYMENT_METHOD
        else:
            if db.add_gasto(supabase_client, valor, chosen_category_id, data, forma_pagamento_id, descricao_gasto):
                await update.message.reply_text(f"Gasto de R${valor:.2f} ({descricao_gasto}) em '{chosen_category_name}' via '{forma_pagamento_nome_real}' registrado com sucesso!", reply_markup=ReplyKeyboardRemove())
                
                if original_category_text.lower() != chosen_category_name.lower():
                    current_aliases = set()
                    for cat in db.get_categorias(supabase_client):
                        if cat['id'] == chosen_category_id:
                            if cat['aliases'] and isinstance(cat['aliases'], list):
                                current_aliases.update(cat['aliases'])
                            break
                    if original_category_text.lower() not in [a.lower() for a in current_aliases]:
                        current_aliases.add(original_category_text)
                        db.update_categoria_aliases(supabase_client, chosen_category_id, list(current_aliases))
                        await update.message.reply_text(f"'{original_category_text}' foi adicionado como um alias para '{chosen_category_name}'. O bot aprenderá com isso!", reply_markup=ReplyKeyboardRemove())
            else:
                await update.message.reply_text("Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde.", reply_markup=ReplyKeyboardRemove())
            
            context.user_data.pop('pending_transaction', None)
            return ConversationHandler.END

    elif user_response.lower() == "criar nova categoria":
        context.user_data['pending_transaction']['valor'] = valor
        context.user_data['pending_transaction']['data'] = data
        context.user_data['pending_transaction']['original_category_text'] = original_category_text

        await update.message.reply_text("Ok, qual o nome da nova categoria para este gasto?", reply_markup=ReplyKeyboardRemove())
        return ASKING_NEW_CATEGORY_NAME

    elif user_response.lower() == "não se aplica / outra":
        await update.message.reply_text("Entendi. Por favor, digite o nome da categoria correta para este gasto.", reply_markup=ReplyKeyboardRemove())
        return ASKING_NEW_CATEGORY_NAME

    else:
        await update.message.reply_text(
            f"Não entendi sua resposta. Por favor, digite o nome exato de uma das sugestões, "
            f"ou 'Criar nova categoria' ou 'Não se aplica / Outra'.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ASKING_CATEGORY_CLARIFICATION


async def handle_new_category_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    supabase_client = context.bot_data['supabase_client']
    new_category_name_input = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Desculpe, não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente.", reply_markup=ReplyKeyboardRemove())
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
                keyboard_options.append(["Outro / Não sei"])
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    "Qual foi a forma de pagamento?",
                    reply_markup=reply_markup
                )
                return ASKING_PAYMENT_METHOD
            else:
                if db.add_gasto(supabase_client, valor, categoria_id, data, forma_pagamento_id, descricao_gasto):
                    await update.message.reply_text(f"Gasto de R${valor:.2f} ({descricao_gasto}) em '{new_category_name_camel_case}' via '{forma_pagamento_nome_real}' registrado com sucesso!", reply_markup=ReplyKeyboardRemove())
                    
                    if original_category_text.lower() != new_category_name_camel_case.lower():
                        current_aliases = set()
                        for cat in db.get_categorias(supabase_client):
                            if cat['id'] == categoria_id:
                                if cat['aliases'] and isinstance(cat['aliases'], list):
                                    current_aliases.update(cat['aliases'])
                                break
                        
                        if original_category_text.lower() not in [a.lower() for a in current_aliases]:
                            current_aliases.add(original_category_text)
                            db.update_categoria_aliases(supabase_client, categoria_id, list(current_aliases))
                            await update.message.reply_text(f"'{original_category_text}' foi adicionado como um alias para '{new_category_name_camel_case}'. O bot aprenderá com isso!", reply_markup=ReplyKeyboardRemove())

                else:
                    await update.message.reply_text("Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde.", reply_markup=ReplyKeyboardRemove())
            
            context.user_data.pop('pending_transaction', None)
            return ConversationHandler.END

        else:
            nome_existente_camel_case = to_camel_case(new_category_name_input)
            await update.message.reply_text(f"Não foi possível criar a categoria '{nome_existente_camel_case}'. Ela já existe ou houve um erro. Por favor, tente novamente ou escolha uma categoria existente.", reply_markup=ReplyKeyboardRemove())
            return ConversationHandler.END
    
async def handle_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    supabase_client = context.bot_data['supabase_client']
    user_response_payment = update.message.text
    pending_transaction = context.user_data.get('pending_transaction')

    if not pending_transaction:
        await update.message.reply_text("Desculpe, não encontrei uma transação pendente. Por favor, tente registrar seu gasto novamente.", reply_markup=ReplyKeyboardRemove())
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
        if user_response_payment.lower() not in ["outro / não sei", "outro", "não sei", "nao sei"]:
            try:
                response_add_fp = supabase_client.table('formas_pagamento').insert({'nome': final_payment_method_name}).execute()
                if response_add_fp.data:
                    forma_pagamento_id = response_add_fp.data[0]['id']
                    await update.message.reply_text(f"Forma de pagamento '{final_payment_method_name}' adicionada para uso futuro.", reply_markup=ReplyKeyboardRemove())
                else:
                    await update.message.reply_text(f"Não foi possível adicionar a forma de pagamento '{final_payment_method_name}'. Usando 'Não Informado'.", reply_markup=ReplyKeyboardRemove())
            except Exception as e:
                print(f"Erro ao adicionar nova forma de pagamento: {e}")
                await update.message.reply_text(f"Erro ao adicionar nova forma de pagamento. Usando 'Não Informado'.", reply_markup=ReplyKeyboardRemove())
        
        if not forma_pagamento_id:
            forma_pagamento_id = db.get_forma_pagamento_id_by_name(supabase_client, 'NaoInformado')
            final_payment_method_name = 'Não Informado' if forma_pagamento_id else 'Desconhecido'
            if not forma_pagamento_id:
                await update.message.reply_text("Atenção: A forma de pagamento 'Não Informado' não existe. Gasto registrado sem forma de pagamento.", reply_markup=ReplyKeyboardRemove())

    if db.add_gasto(supabase_client, valor, categoria_id, data, forma_pagamento_id, descricao_gasto):
        await update.message.reply_text(f"Gasto de R${valor:.2f} ({descricao_gasto}) em '{categoria_nome_db}' via '{final_payment_method_name}' registrado com sucesso!", reply_markup=ReplyKeyboardRemove())
        
        if original_category_text.lower() != categoria_nome_db.lower():
            current_aliases = set()
            for cat in db.get_categorias(supabase_client):
                if cat['id'] == categoria_id:
                    if cat['aliases'] and isinstance(cat['aliases'], list):
                        current_aliases.update(cat['aliases'])
                    break
            if original_category_text.lower() not in [a.lower() for a in current_aliases]:
                current_aliases.add(original_category_text)
                db.update_categoria_aliases(supabase_client, categoria_id, list(current_aliases))
                await update.message.reply_text(f"'{original_category_text}' foi adicionado como um alias para '{categoria_nome_db}'. O bot aprenderá com isso!", reply_markup=ReplyKeyboardRemove())
    else:
        await update.message.reply_text("Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde.", reply_markup=ReplyKeyboardRemove())
    
    context.user_data.pop('pending_transaction', None)
    return ConversationHandler.END