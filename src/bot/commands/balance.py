from telegram import Update
from telegram.ext import ContextTypes
from src.core import charts


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
