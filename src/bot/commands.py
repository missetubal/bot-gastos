# src/bot/commands.py
from telegram import Update
from telegram.ext import ContextTypes
from typing import Union, List
import datetime  # Mantenha esta importação

from src.core import db
from src.core import charts
from src.utils.text_utils import to_camel_case


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem quando o comando /start é emitido."""
    await update.message.reply_text(
        "Olá! Sou seu bot de finanças. Envie-me seus **gastos** (ex: 'gastei 50 no mercado') "
        "ou seus **ganhos** (ex: 'recebi 1000 de salário').\n\n"
        "Comandos úteis:\n"
        "- `/balanco` para ver o resumo dos seus ganhos e gastos.\n"
        "- `/gastos_por_categoria` para ver seus gastos por categoria e limites.\n"
        "- `/total_categoria [nome_da_categoria]` para ver o total gasto em uma categoria.\n"
        "- `/total_por_pagamento` para ver o total gasto por forma de pagamento.\n"
        "- `/gastos_mensal_combinado` para ver gastos por mês, categoria e forma de pagamento.\n"
        "- `/listar_gastos [mes-MM ou nome_categoria]` para listar gastos detalhados.\n"
        "- `/categorias` para listar as categorias existentes.\n"
        "- `/adicionar_categoria [nome] [limite]` para criar uma nova categoria.\n"
        "- `/definir_limite [nome_da_categoria] [valor]` para definir/alterar um limite.\n"
        "- `/adicionar_alias [categoria] [alias1,alias2,...]` para adicionar sinônimos.\n"
        "- `/help` para mais informações."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem quando o comando /help é emitido."""
    await update.message.reply_text(
        "**Como usar:**\n"
        "Para registrar um gasto, use frases como:\n"
        "- `gastei 30 no almoço`\n"
        "- `paguei 15 de gasolina`\n"
        "- `cinema 40 ontem`\n\n"
        "Para registrar um ganho, use frases como:\n"
        "- `recebi 1000 de salário`\n"
        "- `ganhei 50 de freelance`\n"
        "- `vendi algo por 200 hoje`\n\n"
        "**Para adicionar uma categoria, basta dizer:**\n"
        "- `adicione a categoria Lazer`\n"
        "- `quero adicionar uma categoria de Estudos com limite de 300`\n\n"
        "**Comandos de Gráfico e Relatório:**\n"
        "- `/start`: Mensagem de boas-vindas.\n"
        "- `/help`: Mostra esta mensagem.\n"
        "- `/balanco`: Gera um gráfico do balanço mensal (ganhos vs. gastos).\n"
        "- `/gastos_por_categoria`: Gera um gráfico dos seus gastos por categoria, comparado com limites.\n"
        "- `/total_categoria [nome_da_categoria]`: Mostra o valor total gasto em uma categoria específica.\n"
        "- `/total_por_pagamento`: Gera um gráfico do total de gastos por forma de pagamento.\n"
        "- `/gastos_mensal_combinado`: Gera um gráfico de gastos mensais por categoria e forma de pagamento.\n"
        "- `/listar_gastos [mês-MM ou nome_categoria]`: Lista todos os gastos de um mês específico (ex: `2025-07`) ou de uma categoria (ex: `Transporte`).\n"
        "**Comandos de Gerenciamento:**\n"
        "- `/categorias`: Lista todas as categorias de gastos que você definiu.\n"
        "- `/adicionar_categoria [nome] [limite_opcional]`: Adiciona uma nova categoria (ex: `/adicionar_categoria Lazer 500`). Se o limite for omitido, será `NULL`.\n"
        "- `/definir_limite [nome_da_categoria] [valor]`: Define ou altera o limite mensal para uma categoria (ex: `/definir_limite Alimentacao 800`). Use 0 para remover o limite.\n"
        "- `/adicionar_alias [categoria] [alias1,alias2,...]`: Adiciona palavras-chave para uma categoria (ex: `/adicionar_alias Alimentacao mercado,supermercado,restaurante`)."
    )


async def balanco_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gera e envia o gráfico de balanço."""
    supabase_client = context.bot_data["supabase_client"]
    await update.message.reply_text("Gerando seu balanço mensal, por favor aguarde...")
    chart_buffer = charts.generate_balance_chart(supabase_client)
    if chart_buffer:
        chart_buffer.name = "balanco_chart.png"
        await update.message.reply_photo(
            photo=chart_buffer, caption="Aqui está seu balanço mensal:"
        )
    else:
        await update.message.reply_text(
            "Ainda não tenho dados suficientes para gerar um balanço. Registre alguns gastos e ganhos primeiro!"
        )


async def gastos_por_categoria_command(
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


async def categorias_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Lista todas as categorias existentes."""
    supabase_client = context.bot_data["supabase_client"]
    categorias = db.get_categorias(supabase_client)
    if categorias:
        message = "**Categorias de Gastos:**\n\n"
        for cat in categorias:
            limite = (
                f" (Limite: R${cat['limite_mensal']:.2f})"
                if cat["limite_mensal"] is not None and cat["limite_mensal"] > 0
                else ""
            )
            aliases_str = (
                f" (Aliases: {', '.join(cat['aliases'])})"
                if cat["aliases"] and isinstance(cat["aliases"], list)
                else ""
            )
            message += f"- {cat['nome']}{limite}{aliases_str}\n"
        await update.message.reply_text(
            message, parse_mode="Markdown"
        )  # Adicionado parse_mode
    else:
        await update.message.reply_text(
            "Nenhuma categoria de gastos definida ainda. Use `/adicionar_categoria [nome] [limite_opcional]` para começar."
        )


async def total_por_pagamento_command(
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


async def gastos_mensal_combinado_command(
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


async def listar_gastos_command(
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
        categoria_id = db.get_categoria_id_by_text(
            supabase_client, categoria_nome_normalizada
        )

        if categoria_id:
            gastos_data_raw = db.get_gastos(supabase_client)
            # A data já é um objeto Timestamp do Pandas após filter_gastos_data
            gastos_filtrados = charts.filter_gastos_data(
                gastos_data_raw, categoria_id=categoria_id
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
            gastos_filtrados, key=lambda x: x["data"], reverse=True
        )  # <-- CORREÇÃO AQUI

        for gasto in gastos_filtrados_sorted:
            valor_fmt = f"R${gasto['valor']:.2f}"
            # Formata a data Timestamp para string de exibição
            data_fmt = gasto["data"].strftime(
                "%Y-%m-%d"
            )  # <-- ADICIONADO strftime para exibição
            categoria_nome = gasto.get("categoria_nome", "Desconhecida")
            forma_pagamento_nome = gasto.get("forma_pagamento_nome", "Não Informado")
            descricao = gasto.get("descricao", "Sem descrição")

            message += f"• {valor_fmt} {descricao} ({categoria_nome} - {forma_pagamento_nome}) em {data_fmt}\n"
            total_sum += gasto["valor"]

        message += f"\n**Total: R${total_sum:.2f}**"
        await update.message.reply_text(message, parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"Nenhum gasto encontrado{period_title} com o critério '{query}'."
        )


async def total_categoria_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Mostra o total de gastos para uma categoria específica."""
    supabase_client = context.bot_data["supabase_client"]
    print(f"DEBUG: Comando /total_categoria recebido com args: {context.args}")

    if not context.args:
        await update.message.reply_text(
            "Uso: `/total_categoria [nome_da_categoria]`\nEx: `/total_categoria Alimentacao`"
        )
        print("DEBUG: Sem argumentos fornecidos.")
        return

    categoria_nome_input = " ".join(context.args).strip()
    categoria_nome_normalizada = to_camel_case(categoria_nome_input)
    print(f"DEBUG: Categoria normalizada para busca: {categoria_nome_normalizada}")

    categorias_existentes = db.get_categorias(supabase_client)
    categoria_id = None
    for cat in categorias_existentes:
        print(
            f"DEBUG: Comparando '{categoria_nome_normalizada.lower()}' com '{cat['nome'].lower()}'"
        )
        if cat["nome"].lower() == categoria_nome_normalizada.lower():
            categoria_id = cat["id"]
            break

    if not categoria_id:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_input}' não encontrada. "
            "Use `/categorias` para ver as existentes ou `/adicionar_categoria` para criá-la."
        )
        print(f"DEBUG: Categoria '{categoria_nome_input}' não encontrada no DB.")
        return

    print(
        f"DEBUG: Categoria '{categoria_nome_normalizada}' encontrada com ID: {categoria_id}"
    )

    gastos_da_categoria = db.get_gastos_by_category(supabase_client, categoria_id)
    print(f"DEBUG: Gastos obtidos da categoria: {gastos_da_categoria}")

    total_gasto = sum(gasto["valor"] for gasto in gastos_da_categoria)
    print(f"DEBUG: Total gasto calculado: {total_gasto}")

    if gastos_da_categoria:
        await update.message.reply_text(
            f"O total gasto na categoria **'{categoria_nome_normalizada}'** é de **R${total_gasto:.2f}**."
        )
        print("DEBUG: Mensagem de total enviada.")
    else:
        await update.message.reply_text(
            f"Você ainda não tem gastos registrados na categoria **'{categoria_nome_normalizada}'**."
        )
        print("DEBUG: Mensagem de sem gastos enviada.")


async def adicionar_categoria_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Adiciona uma nova categoria de gastos."""
    supabase_client = context.bot_data["supabase_client"]
    if not context.args:
        await update.message.reply_text(
            "Uso: `/adicionar_categoria [nome_da_categoria] [limite_opcional]`\n"
            "Ex: `/adicionar_categoria Lazer 500`"
        )
        return

    categoria_nome_input = " ".join(context.args[0:]).strip()

    limite: Union[float, None] = None
    if len(context.args) > 1:
        try:
            potential_limit = float(context.args[-1].replace(",", "."))
            if len(context.args) > 1 and potential_limit == float(
                context.args[-1].replace(",", ".")
            ):
                limite = potential_limit
                categoria_nome_input = " ".join(context.args[:-1]).strip()
        except ValueError:
            pass

    if not categoria_nome_input:
        await update.message.reply_text("Por favor, forneça o nome da categoria.")
        return

    if db.add_categoria(supabase_client, categoria_nome_input, limite_mensal=limite):
        nome_exibicao = to_camel_case(categoria_nome_input)
        limite_msg = (
            f" com limite de R${limite:.2f}"
            if limite is not None and limite > 0
            else ""
        )
        await update.message.reply_text(
            f"Categoria '{nome_exibicao}' adicionada{limite_msg} com sucesso!"
        )
    else:
        nome_exibicao = to_camel_case(categoria_nome_input)
        await update.message.reply_text(
            f"Erro ao adicionar categoria '{nome_exibicao}'. Ela já existe ou ocorreu um problema."
        )


async def definir_limite_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Define ou altera o limite mensal para uma categoria."""
    supabase_client = context.bot_data["supabase_client"]
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/definir_limite [nome_da_categoria] [valor]`\n"
            "Ex: `/definir_limite Alimentacao 800` (Use 0 para remover o limite)"
        )
        return

    categoria_nome_input = context.args[0]
    categoria_nome_normalizada = to_camel_case(categoria_nome_input)

    try:
        novo_limite = float(context.args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Valor do limite inválido. Use um número (ex: 800 ou 800.50). Use 0 para remover o limite."
        )
        return

    categorias = db.get_categorias(supabase_client)
    categoria_id = None
    for cat in categorias:
        if cat["nome"].lower() == categoria_nome_normalizada.lower():
            categoria_id = cat["id"]
            break

    if not categoria_id:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_normalizada}' não encontrada. "
            f"Use `/categorias` para ver as existentes ou `/adicionar_categoria {categoria_nome_normalizada} {novo_limite}` para criá-la."
        )
        return

    limite_para_db: Union[float, None] = novo_limite if novo_limite > 0 else None

    if db.update_categoria_limite(supabase_client, categoria_id, limite_para_db):
        limite_msg = (
            f" com limite de R${novo_limite:.2f}"
            if novo_limite > 0
            else " (limite removido)"
        )
        await update.message.reply_text(
            f"Limite para a categoria '{categoria_nome_normalizada}' definido{limite_msg} com sucesso!"
        )
    else:
        await update.message.reply_text(
            f"Erro ao definir limite para a categoria '{categoria_nome_normalizada}'."
        )


async def adicionar_alias_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Adiciona aliases (palavras-chave) para uma categoria existente."""
    supabase_client = context.bot_data["supabase_client"]
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/adicionar_alias [nome_da_categoria] [alias1,alias2,alias3,...]`\n"
            "Ex: `/adicionar_alias Alimentacao mercado,supermercado,padaria`"
        )
        return

    categoria_nome_input = context.args[0]
    categoria_nome_normalizada = to_camel_case(categoria_nome_input)

    aliases_str = " ".join(context.args[1:])
    new_aliases = [a.strip() for a in aliases_str.split(",") if a.strip()]

    if not new_aliases:
        await update.message.reply_text(
            "Por favor, forneça pelo menos um alias válido, separado por vírgulas."
        )
        return

    categorias = db.get_categorias(supabase_client)
    categoria_encontrada = None
    for cat in categorias:
        if cat["nome"].lower() == categoria_nome_normalizada.lower():
            categoria_encontrada = cat
            break

    if not categoria_encontrada:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_normalizada}' não encontrada. "
            "Use `/categorias` para ver as existentes ou `/adicionar_categoria` para criá-la."
        )
        return

    current_aliases = set(
        categoria_encontrada["aliases"] if categoria_encontrada["aliases"] else []
    )
    for alias in new_aliases:
        current_aliases.add(alias)

    updated_aliases = list(current_aliases)

    if db.update_categoria_aliases(
        supabase_client, categoria_encontrada["id"], updated_aliases
    ):
        await update.message.reply_text(
            f"Aliases adicionados para '{categoria_encontrada['nome']}'.\nNovos aliases: {', '.join(updated_aliases)}"
        )
    else:
        await update.message.reply_text(
            f"Erro ao adicionar aliases para '{categoria_encontrada['nome']}'."
        )
