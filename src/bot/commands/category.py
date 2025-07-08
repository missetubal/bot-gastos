from telegram import Update
from telegram.ext import ContextTypes
from src.core import charts
from src.core import db
from typing import Union
from src.utils.text_utils import to_camel_case

async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lista todas as categorias existentes."""
    supabase_client = context.bot_data['supabase_client']
    categorias = db.get_categorias(supabase_client)
    if categorias:
        message = "**Categorias de Gastos:**\n\n"
        for cat in categorias:
            limite = f" (Limite: R${cat['limite_mensal']:.2f})" if cat['limite_mensal'] is not None and cat['limite_mensal'] > 0 else ""
            aliases_str = f" (Aliases: {', '.join(cat['aliases'])})" if cat['aliases'] and isinstance(cat['aliases'], list) else ""
            message += f"- {cat['nome']}{limite}{aliases_str}\n"
        await update.message.reply_text(message, parse_mode='Markdown') # Adicionado parse_mode
    else:
        await update.message.reply_text("Nenhuma categoria de gastos definida ainda. Use `/adicionar_categoria [nome] [limite_opcional]` para começar.")

async def total_categoria_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra o total de gastos para uma categoria específica."""
    supabase_client = context.bot_data['supabase_client']
    print(f"DEBUG: Comando /total_categoria recebido com args: {context.args}")

    if not context.args:
        await update.message.reply_text("Uso: `/total_categoria [nome_da_categoria]`\nEx: `/total_categoria Alimentacao`")
        print("DEBUG: Sem argumentos fornecidos.")
        return

    categoria_nome_input = " ".join(context.args).strip()
    categoria_nome_normalizada = to_camel_case(categoria_nome_input)
    print(f"DEBUG: Categoria normalizada para busca: {categoria_nome_normalizada}")

    categorias_existentes = db.get_categorias(supabase_client)
    categoria_id = None
    for cat in categorias_existentes:
        print(f"DEBUG: Comparando '{categoria_nome_normalizada.lower()}' com '{cat['nome'].lower()}'")
        if cat['nome'].lower() == categoria_nome_normalizada.lower():
            categoria_id = cat['id']
            break

    if not categoria_id:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_input}' não encontrada. "
            "Use `/categorias` para ver as existentes ou `/adicionar_categoria` para criá-la."
        )
        print(f"DEBUG: Categoria '{categoria_nome_input}' não encontrada no DB.")
        return

    print(f"DEBUG: Categoria '{categoria_nome_normalizada}' encontrada com ID: {categoria_id}")

    gastos_da_categoria = db.get_gastos_by_category(supabase_client, categoria_id)
    print(f"DEBUG: Gastos obtidos da categoria: {gastos_da_categoria}")
    
    total_gasto = sum(gasto['valor'] for gasto in gastos_da_categoria)
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


async def adicionar_categoria_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona uma nova categoria de gastos."""
    supabase_client = context.bot_data['supabase_client']
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
            potential_limit = float(context.args[-1].replace(',', '.'))
            if len(context.args) > 1 and potential_limit == float(context.args[-1].replace(',', '.')):
                limite = potential_limit
                categoria_nome_input = " ".join(context.args[:-1]).strip()
        except ValueError:
            pass

    if not categoria_nome_input:
        await update.message.reply_text("Por favor, forneça o nome da categoria.")
        return

    if db.add_categoria(supabase_client, categoria_nome_input, limite_mensal=limite):
        nome_exibicao = to_camel_case(categoria_nome_input)
        limite_msg = f" com limite de R${limite:.2f}" if limite is not None and limite > 0 else ""
        await update.message.reply_text(f"Categoria '{nome_exibicao}' adicionada{limite_msg} com sucesso!")
    else:
        nome_exibicao = to_camel_case(categoria_nome_input)
        await update.message.reply_text(f"Erro ao adicionar categoria '{nome_exibicao}'. Ela já existe ou ocorreu um problema.")


async def definir_limite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Define ou altera o limite mensal para uma categoria."""
    supabase_client = context.bot_data['supabase_client']
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/definir_limite [nome_da_categoria] [valor]`\n"
            "Ex: `/definir_limite Alimentacao 800` (Use 0 para remover o limite)"
        )
        return

    categoria_nome_input = context.args[0]
    categoria_nome_normalizada = to_camel_case(categoria_nome_input) 

    try:
        novo_limite = float(context.args[1].replace(',', '.'))
    except ValueError:
        await update.message.reply_text("Valor do limite inválido. Use um número (ex: 800 ou 800.50). Use 0 para remover o limite.")
        return

    categorias = db.get_categorias(supabase_client)
    categoria_id = None
    for cat in categorias:
        if cat['nome'].lower() == categoria_nome_normalizada.lower():
            categoria_id = cat['id']
            break

    if not categoria_id:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_normalizada}' não encontrada. "
            f"Use `/categorias` para ver as existentes ou `/adicionar_categoria {categoria_nome_normalizada} {novo_limite}` para criá-la."
        )
        return

    limite_para_db: Union[float, None] = novo_limite if novo_limite > 0 else None

    if db.update_categoria_limite(supabase_client, categoria_id, limite_para_db):
        limite_msg = f" com limite de R${novo_limite:.2f}" if novo_limite > 0 else " (limite removido)"
        await update.message.reply_text(f"Limite para a categoria '{categoria_nome_normalizada}' definido{limite_msg} com sucesso!")
    else:
        await update.message.reply_text(f"Erro ao definir limite para a categoria '{categoria_nome_normalizada}'.")

async def adicionar_alias_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adiciona aliases (palavras-chave) para uma categoria existente."""
    supabase_client = context.bot_data['supabase_client']
    if len(context.args) < 2:
        await update.message.reply_text(
            "Uso: `/adicionar_alias [nome_da_categoria] [alias1,alias2,alias3,...]`\n"
            "Ex: `/adicionar_alias Alimentacao mercado,supermercado,padaria`"
        )
        return

    categoria_nome_input = context.args[0]
    categoria_nome_normalizada = to_camel_case(categoria_nome_input)

    aliases_str = " ".join(context.args[1:])
    new_aliases = [a.strip() for a in aliases_str.split(',') if a.strip()]

    if not new_aliases:
        await update.message.reply_text("Por favor, forneça pelo menos um alias válido, separado por vírgulas.")
        return

    categorias = db.get_categorias(supabase_client)
    categoria_encontrada = None
    for cat in categorias:
        if cat['nome'].lower() == categoria_nome_normalizada.lower():
            categoria_encontrada = cat
            break

    if not categoria_encontrada:
        await update.message.reply_text(
            f"Categoria '{categoria_nome_normalizada}' não encontrada. "
            "Use `/categorias` para ver as existentes ou `/adicionar_categoria` para criá-la."
        )
        return

    current_aliases = set(categoria_encontrada['aliases'] if categoria_encontrada['aliases'] else [])
    for alias in new_aliases:
        current_aliases.add(alias)
    
    updated_aliases = list(current_aliases)

    if db.update_categoria_aliases(supabase_client, categoria_encontrada['id'], updated_aliases):
        await update.message.reply_text(f"Aliases adicionados para '{categoria_encontrada['nome']}'.\nNovos aliases: {', '.join(updated_aliases)}")
    else:
        await update.message.reply_text(f"Erro ao adicionar aliases para '{categoria_encontrada['nome']}'.")