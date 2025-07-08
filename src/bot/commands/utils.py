from telegram import Update
from telegram.ext import ContextTypes

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
