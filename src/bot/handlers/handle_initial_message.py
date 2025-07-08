from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import datetime
from typing import Union, Dict, Any

from src.bot.handlers import ASKING_CATEGORY_CLARIFICATION, ASKING_CONFIRMATION, ASKING_PAYMENT_METHOD
from src.bot.handlers.aux import send_confirmation_message
from src.core.ai import extract_transaction_info 
from src.core import db
from src.utils.text_utils import to_camel_case
from src.core import charts

async def handle_initial_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Union[int, None]:
    supabase_client = context.bot_data['supabase_client']
    user_message = update.message.text
    chat_id = update.message.chat_id

    print(f"Mensagem recebida de {chat_id}: {user_message}")

    if not user_message:
        return ConversationHandler.END # Não faz nada se a mensagem for vazia

    parsed_info: Union[Dict[str, Any], None] = extract_transaction_info(user_message, supabase_client)

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
        monthly_limit = parsed_info.get('monthly_limit')

        if not categoria_nome_input:
            await update.message.reply_text("🤔 Não consegui identificar o nome da categoria que você quer adicionar.")
            return ConversationHandler.END

        if db.add_category(supabase_client, categoria_nome_input, monthly_limit=monthly_limit):
            nome_exibicao = to_camel_case(categoria_nome_input)
            limite_msg = f" com limite de R${monthly_limit:.2f}" if monthly_limit is not None and monthly_limit > 0 else ""
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
            valor = float(parsed_info['value'])
            data = parsed_info.get('date', str(datetime.date.today()))
            categoria_texto_llama = parsed_info.get('categoria', 'Outros') or 'Outros' 
            forma_pagamento_text = parsed_info.get('forma_pagamento')
            descricao_gasto = parsed_info.get('descricao_gasto', user_message)

            context.user_data['pending_transaction'].update({
                'value': valor,
                'date': data,
                'original_category_text': categoria_texto_llama,
                'forma_pagamento_text': forma_pagamento_text,
                'descricao_gasto': descricao_gasto,
                'transaction_type': 'gasto'
            })
            
            category_id = db.get_category_id_by_text(supabase_client, categoria_texto_llama)
            if category_id:
                context.user_data['pending_transaction']['category_id'] = category_id
                context.user_data['pending_transaction']['categoria_nome_db'] = next((cat['name'] for cat in db.get_categories(supabase_client) if cat['id'] == category_id), categoria_texto_llama)
            else:
                similar_categories = db.find_similar_categories(supabase_client, categoria_texto_llama)
                context.user_data['pending_transaction']['suggestions'] = similar_categories
                
                keyboard_options = [[cat['name']] for cat in similar_categories]
                keyboard_options.append(["Criar nova categoria ➕", "Não se aplica / Outra 🤷‍♀️"])
                reply_markup = ReplyKeyboardMarkup(keyboard_options, one_time_keyboard=True, resize_keyboard=True)
                await update.message.reply_text(
                    f"🧐 Não encontrei uma categoria exata para '{categoria_texto_llama}'. "
                    f"Seria uma destas? Se sim, clique ou digite o nome. "
                    f"Ou você pode 'Criar nova categoria ➕' ou 'Não se aplica / Outra 🤷‍♀️'.",
                    reply_markup=reply_markup
                )
                return ASKING_CATEGORY_CLARIFICATION
            
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
            
            context.user_data['pending_transaction']['forma_pagamento_id'] = forma_pagamento_id
            context.user_data['pending_transaction']['forma_pagamento_nome_real'] = forma_pagamento_nome_real
            
        elif intencao == 'ganho':
            valor = float(parsed_info['value'])
            data = parsed_info.get('date', str(datetime.date.today()))
            descricao = parsed_info.get('description', 'Diversos')
            context.user_data['pending_transaction'].update({
                'value': valor,
                'date': data,
                'description': descricao,
                'transaction_type': 'ganho'
            })
            
        await send_confirmation_message(update, context, context.user_data['pending_transaction'])
        return ASKING_CONFIRMATION

    elif intencao in ['mostrar_balanco', 'mostrar_grafico_gastos_categoria', 'mostrar_grafico_gastos_por_pagamento', 'mostrar_grafico_mensal_combinado']:
        data_inicio = parsed_info.get('data_inicio')
        data_fim = parsed_info.get('data_fim')
        
        forma_pagamento_id = None
        category_id = None
        
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
                category_id = db.get_category_id_by_text(supabase_client, categoria_texto_llama)
                if not category_id:
                    await update.message.reply_text(f"⚠️ Categoria '{categoria_texto_llama}' não reconhecida. Gerando gráfico sem este filtro. 📊")
            chart_buffer = charts.generate_payment_method_spending_chart(supabase_client, category_id=category_id, data_inicio=data_inicio, data_fim=data_fim)
            title = "Gastos por Forma de Pagamento"
        
        elif intencao == 'mostrar_balanco':
            chart_buffer = charts.generate_balance_chart(supabase_client, data_inicio=data_inicio, data_fim=data_fim)
            title = "Balanço Mensal"
        
        elif intencao == 'mostrar_grafico_mensal_combinado':
            chart_buffer = charts.generate_monthly_category_payment_chart(supabase_client, data_inicio=data_inicio, data_fim=data_fim)
            title = "Gastos Mensais Combinados"

        else:
            await update.message.reply_text("🤔 Não consegui identificar o tipo de gráfico. Use `/help` para ver as opções. 💡")
            return ConversationHandler.END

        if chart_buffer:
            await update.message.reply_photo(photo=chart_buffer, caption=f"📊 Aqui está seu gráfico de {title}:")
        else:
            await update.message.reply_text(f"📉 Ainda não tenho dados suficientes para gerar este gráfico. Registre mais transações primeiro! 📝")
        
        return ConversationHandler.END
    elif intencao == 'listar_gastos_detalhados':
            categoria_texto_llama = parsed_info.get('categoria')
            data_inicio = parsed_info.get('data_inicio')
            data_fim = parsed_info.get('data_fim')

            gastos_filtrados = []
            period_title = ""

            # Lógica para filtrar por categoria, se fornecida
            category_id = None
            if categoria_texto_llama:
                category_id = db.get_category_id_by_text(supabase_client, categoria_texto_llama)
                if not category_id:
                    await update.message.reply_text(f"⚠️ Categoria '{categoria_texto_llama}' não reconhecida. Listando todos os gastos no período.")
            
            # Lógica para filtrar por data, se fornecida
            gastos_data_raw = db.get_gastos(supabase_client) # Pega todos os gastos
            gastos_filtrados = charts.filter_gastos_data(gastos_data_raw, category_id=category_id, data_inicio=data_inicio, data_fim=data_fim)
            
            # Constrói o título do período/categoria para a mensagem
            if data_inicio and data_fim:
                start_date_obj = datetime.datetime.strptime(data_inicio, '%Y-%m-%d')
                end_date_obj = datetime.datetime.strptime(data_fim, '%Y-%m-%d')
                if start_date_obj.day == 1 and end_date_obj.day == (end_date_obj + datetime.timedelta(days=1)).day - 1 and start_date_obj.month == end_date_obj.month and start_date_obj.year == end_date_obj.year:
                    period_title = f" do mês de {start_date_obj.strftime('%B/%Y').capitalize()}"
                else:
                    period_title = f" de {start_date_obj.strftime('%d/%m/%Y')} a {end_date_obj.strftime('%d/%m/%Y')}"
            
            if category_id and not period_title: # Se filtrou só por categoria
                 categoria_nome_real = next((cat['name'] for cat in db.get_categories(supabase_client) if cat['id'] == category_id), categoria_texto_llama)
                 period_title = f" da categoria {categoria_nome_real}"
            elif not category_id and not period_title: # Se não teve filtro
                 period_title = " (Todos os Gastos)"


            if gastos_filtrados:
                message = f"**Detalhes dos Gastos{period_title}:**\n\n"
                total_sum = 0.0
                gastos_filtrados_sorted = sorted(gastos_filtrados, key=lambda x: x['date'], reverse=True)
                
                for gasto in gastos_filtrados_sorted:
                    valor_fmt = f"R${gasto['value']:.2f}"
                    data_fmt = gasto['date'].strftime('%Y-%m-%d') # Formata para string
                    categoria_nome = gasto.get('categoria_nome', 'Desconhecida')
                    forma_pagamento_nome = gasto.get('forma_pagamento_nome', 'Não Informado')
                    descricao = gasto.get('description', 'Sem descrição')
                    
                    message += (
                        f"• {valor_fmt} {descricao} ({categoria_nome} - {forma_pagamento_nome}) em {data_fmt}\n"
                    )
                    total_sum += gasto['value']
                
                message += f"\n**Total: R${total_sum:.2f}**"
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"Nenhum gasto encontrado{period_title} com os critérios fornecidos. 🤷‍♀️")
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            "🤔 Não consegui entender sua intenção. Por favor, tente descrever claramente "
            "um gasto, um ganho, a adição de uma categoria ou o pedido de um gráfico. 💡"
        )
        return ConversationHandler.END
