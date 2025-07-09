from telegram import Update
from telegram.ext import ContextTypes
from src.core import charts
from src.core import db
from typing import Union
import datetime
from src.utils.text_utils import to_camel_case


async def category_spending_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Gera e envia o gráfico de gastos por categoria."""
    supabase_client = context.bot_data["supabase_client"]
    await update.message.reply_text(
        "Gerando o gráfico de gastos por categoria, por favor aguarde..."
    )
    chart_buffer = charts.generate_category_spending_chart(supabase_client)
    if chart_buffer:
        chart_buffer.name = "gastos_por_categoria_chart.png"
        await update.message.reply_photo(
            photo=chart_buffer, caption="Aqui estão seus gastos por categoria:"
        )
    else:
        await update.message.reply_text(
            "Ainda não tenho dados suficientes para gerar um gráfico de categorias. Registre alguns gastos primeiro!"
        )


async def list_expenses_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lista todos os gastos de um mês específico ou de uma categoria."""
    supabase_client = context.bot_data["supabase_client"]

    if not context.args:
        await update.message.reply_text(
            "Uso: `/listar_gastos [mês-MM]` ou `/listar_gastos [nome_categoria]`\n"
            "Exemplos: `/listar_gastos 2025-07` ou `/listar_gastos Transporte`"
        )
        return

    query = " ".join(context.args).strip()
    gastos_filtrados = []
    period_title = ""  # Initialize period_title

    # Tenta como mês (YYYY-MM)
    if (
        len(query) == 7
        and query[4] == "-"
        and query[0:4].isdigit()
        and query[5:7].isdigit()
    ):
        try:
            year_month_obj = datetime.datetime.strptime(query, "%Y-%m")
            start_date = year_month_obj.strftime("%Y-%m-%d")
            next_month = year_month_obj + datetime.timedelta(days=32)
            end_date = next_month.replace(day=1) - datetime.timedelta(days=1)
            end_date_str = end_date.strftime("%Y-%m-%d")

            gastos_data_raw = db.get_gastos(supabase_client)
            # A data já é um objeto Timestamp do Pandas após filter_gastos_data
            gastos_filtrados = charts.filter_gastos_data(
                gastos_data_raw, data_inicio=start_date, data_fim=end_date_str
            )
            period_title = f" no mês de {year_month_obj.strftime('%B/%Y').capitalize()}"

        except ValueError:
            pass  # Não é um formato de mês válido, tenta como categoria

    # Tenta como categoria
    if not gastos_filtrados:  # Se não filtrou por mês, tenta por categoria
        categoria_nome_normalizada = to_camel_case(query)
        category_id = db.get_category_id_by_text(
            supabase_client, categoria_nome_normalizada
        )

        if category_id:
            gastos_data_raw = db.get_gastos(supabase_client)
            # A data já é um objeto Timestamp do Pandas após filter_gastos_data
            gastos_filtrados = charts.filter_gastos_data(
                gastos_data_raw, category_id=category_id
            )
            period_title = f" da categoria {categoria_nome_normalizada}"
        else:
            await update.message.reply_text(
                f"Não entendi se '{query}' é um mês (formato AAAA-MM) ou uma categoria existente. "
                "Use `/help` para ver os exemplos ou `/categorias` para listar as categorias."
            )
            return

    if gastos_filtrados:
        message = f"**Detalhes dos Gastos{period_title}:**\n\n"
        total_sum = 0.0
        # AQUI ESTÁ A MUDANÇA: Use a data diretamente para ordenação, ela já é um objeto datetime/Timestamp
        gastos_filtrados_sorted = sorted(
            gastos_filtrados, key=lambda x: x["date"], reverse=True
        )  # <-- CORREÇÃO AQUI

        for gasto in gastos_filtrados_sorted:
            valor_fmt = f"R${gasto['value']:.2f}"
            # Formata a data Timestamp para string de exibição
            data_fmt = gasto["date"].strftime(
                "%Y-%m-%d"
            )  # <-- ADICIONADO strftime para exibição
            categoria_nome = gasto.get("categoria_nome", "Desconhecida")
            forma_pagamento_nome = gasto.get("forma_pagamento_nome", "Não Informado")
            descricao = gasto.get("description", "Sem descrição")

            message += f"• {valor_fmt} {descricao} ({categoria_nome} - {forma_pagamento_nome}) em {data_fmt}\n"
            total_sum += gasto["value"]

        message += f"\n**Total: R${total_sum:.2f}**"
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"Nenhum gasto encontrado{period_title} com o critério '{query}'."
        )


async def payment_method_spending_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Gera e envia o gráfico de gastos por forma de pagamento."""
    supabase_client = context.bot_data["supabase_client"]
    await update.message.reply_text(
        "Gerando o gráfico de gastos por forma de pagamento, por favor aguarde..."
    )
    chart_buffer = charts.generate_payment_method_spending_chart(supabase_client)
    if chart_buffer:
        chart_buffer.name = "gastos_por_pagamento_chart.png"
        await update.message.reply_photo(
            photo=chart_buffer, caption="Aqui estão seus gastos por forma de pagamento:"
        )
    else:
        await update.message.reply_text(
            "Ainda não tenho dados suficientes para gerar um gráfico de formas de pagamento. Registre alguns gastos primeiro!"
        )


async def monthly_category_payment_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Gera e envia o gráfico de gastos mensais por categoria e forma de pagamento."""
    supabase_client = context.bot_data["supabase_client"]
    await update.message.reply_text(
        "Gerando o gráfico de gastos mensais combinado, por favor aguarde..."
    )
    chart_buffer = charts.generate_monthly_category_payment_chart(supabase_client)
    if chart_buffer:
        chart_buffer.name = "gastos_mensal_combinado_chart.png"
        await update.message.reply_photo(
            photo=chart_buffer,
            caption="Aqui está seu gráfico mensal por categoria e forma de pagamento:",
        )
    else:
        await update.message.reply_text(
            "Ainda não tenho dados suficientes para gerar este gráfico combinado. Registre alguns gastos primeiro!"
        )
