import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import requests
import json
import datetime

from supabase import create_client, Client

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ContextTypes

# --- Configurações ---
TELEGRAM_BOT_TOKEN = 'SEU_TELEGRAM_BOT_TOKEN' # <-- SUBSTITUA PELO SEU TOKEN AQUI!
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3" # Use o nome do modelo que você baixou com Ollama (ex: llama3, tinyllama)

# --- Configurações do Supabase ---
SUPABASE_URL = "https://xcgkscwgfmclnoedqlgv.supabase.co" # <-- SUBSTITUA PELA SUA PROJECT URL
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhjZ2tzY3dnZm1jbG5vZWRxbGd2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTE4NDAwMTYsImV4cCI6MjA2NzQxNjAxNn0.A5JjQ7h4aAFrt211r5DAwRAsYnv0gCRphRQPyrGdKZY" # <-- SUBSTITUA PELA SUA ANON KEY

# --- Inicializa o cliente Supabase ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funções do Banco de Dados (AGORA COM SUPABASE) ---
def add_gasto(valor, categoria, data):
    try:
        response = supabase.table('gastos').insert({
            "valor": valor,
            "categoria": categoria,
            "data": data
        }).execute()
        print(f"Supabase add_gasto response: {response.data}") # Para debug
        return True
    except Exception as e:
        print(f"Erro ao adicionar gasto ao Supabase: {e}")
        return False

def get_gastos():
    try:
        response = supabase.table('gastos').select('valor,categoria,data').order('data', desc=True).execute()
        print(f"Supabase get_gastos response: {response.data}") # Para debug
        return response.data
    except Exception as e:
        print(f"Erro ao obter gastos do Supabase: {e}")
        return []

# --- NOVA FUNÇÃO: Adicionar Ganho ---
def add_ganho(valor, descricao, data):
    try:
        response = supabase.table('ganhos').insert({
            "valor": valor,
            "descricao": descricao,
            "data": data
        }).execute()
        print(f"Supabase add_ganho response: {response.data}") # Para debug
        return True
    except Exception as e:
        print(f"Erro ao adicionar ganho ao Supabase: {e}")
        return False

# --- NOVA FUNÇÃO: Obter Ganhos ---
def get_ganhos():
    try:
        response = supabase.table('ganhos').select('valor,descricao,data').order('data', desc=True).execute()
        print(f"Supabase get_ganhos response: {response.data}") # Para debug
        return response.data
    except Exception as e:
        print(f"Erro ao obter ganhos do Supabase: {e}")
        return []

# --- Função de Interação com o Ollama (Llama Local) ---
def ask_llama(prompt, model=OLLAMA_MODEL):
    headers = {"Content-Type": "application/json"}
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()['response']
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar com Ollama: {e}")
        return "Desculpe, não consegui processar sua requisição agora. O Llama está offline ou o modelo não está disponível?"

# --- FUNÇÃO ATUALIZADA: Extrair Informações de Transação (Gasto ou Ganho) com Llama ---
def extract_transaction_info(text):
    prompt = f"""
    Analise a seguinte mensagem do usuário para identificar se é um gasto ou um ganho.
    Extraia o valor, a categoria (para gastos) ou descrição (para ganhos), e a data.
    Formate a saída como um JSON com as chaves "tipo" (que pode ser "gasto" ou "ganho"), "valor", "categoria" (se for gasto) ou "descricao" (se for ganho), e "data".
    A data deve estar no formato AAAA-MM-DD. Se a data não for mencionada, use a data de hoje.
    Se a categoria/descrição não for clara, use "Outros" para gastos e "Diversos" para ganhos.

    Exemplos de Gasto:
    Usuário: gastei 50 reais no mercado
    Resposta: {{"tipo": "gasto", "valor": 50.0, "categoria": "Mercado", "data": "{datetime.date.today()}"}}

    Usuário: paguei 120 de aluguel ontem
    Resposta: {{"tipo": "gasto", "valor": 120.0, "categoria": "Aluguel", "data": "{datetime.date.today() - datetime.timedelta(days=1)}"}}

    Usuário: pizza 75
    Resposta: {{"tipo": "gasto", "valor": 75.0, "categoria": "Alimentação", "data": "{datetime.date.today()}"}}

    Exemplos de Ganho:
    Usuário: recebi meu salário de 3000
    Resposta: {{"tipo": "ganho", "valor": 3000.0, "descricao": "Salário", "data": "{datetime.date.today()}"}}

    Usuário: ganhei 100 de freelance na terça passada
    Resposta: {{"tipo": "ganho", "valor": 100.0, "descricao": "Freelance", "data": "{datetime.date.today() - datetime.timedelta(days=4)}"}}

    Usuário: vendi umas coisas por 250
    Resposta: {{"tipo": "ganho", "valor": 250.0, "descricao": "Vendas", "data": "{datetime.date.today()}"}}

    Usuário: {text}
    Resposta:
    """
    response_text = ask_llama(prompt)
    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start : json_end + 1]
            data = json.loads(json_str)
            # Tenta converter o valor para float, se for string
            if isinstance(data.get('valor'), str):
                data['valor'] = float(data['valor'].replace(',', '.'))
            return data
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Erro ao decodificar JSON ou converter valor do Llama: {e}. Resposta bruta: {response_text}")
    return None

# --- FUNÇÃO ATUALIZADA: Gerar Gráfico de Balanço (Ganhos vs Gastos) ---
def generate_balance_chart():
    gastos_data = get_gastos()
    ganhos_data = get_ganhos()

    if not gastos_data and not ganhos_data:
        return None

    # Processar Gastos
    df_gastos = pd.DataFrame(gastos_data)
    if not df_gastos.empty:
        df_gastos['data'] = pd.to_datetime(df_gastos['data'])
        df_gastos['tipo'] = 'Gasto'
    else:
        df_gastos = pd.DataFrame(columns=['valor', 'data', 'tipo'])

    # Processar Ganhos
    df_ganhos = pd.DataFrame(ganhos_data)
    if not df_ganhos.empty:
        df_ganhos['data'] = pd.to_datetime(df_ganhos['data'])
        df_ganhos['tipo'] = 'Ganho'
        # Renomear 'descricao' para 'categoria' para unificar no gráfico de balanço
        df_ganhos = df_ganhos.rename(columns={'descricao': 'categoria'})
    else:
        df_ganhos = pd.DataFrame(columns=['valor', 'data', 'tipo', 'categoria'])


    # Combinar e calcular balanço mensal
    df_all = pd.concat([df_gastos, df_ganhos], ignore_index=True)
    if df_all.empty:
        return None

    df_all['mes_ano'] = df_all['data'].dt.to_period('M')

    # Calcular total de ganhos e gastos por mês
    monthly_summary = df_all.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack(fill_value=0)
    monthly_summary['Balanço'] = monthly_summary.get('Ganho', 0) - monthly_summary.get('Gasto', 0)
    monthly_summary = monthly_summary.sort_index()

    # Gerar gráfico
    plt.figure(figsize=(12, 7))
    monthly_summary[['Ganho', 'Gasto', 'Balanço']].plot(kind='bar', figsize=(12, 7))
    plt.title('Balanço Mensal: Ganhos vs. Gastos')
    plt.ylabel('Valor (R$)')
    plt.xlabel('Mês/Ano')
    plt.xticks(rotation=45, ha='right')
    plt.legend(title='Tipo')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

# --- Handlers do Telegram Bot ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem quando o comando /start é emitido."""
    await update.message.reply_text(
        "Olá! Sou seu bot de finanças. Envie-me seus gastos (ex: 'gastei 50 no mercado') "
        "ou seus ganhos (ex: 'recebi 1000 de salário'). "
        "Digite 'balanço' para ver o resumo dos seus ganhos e gastos."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Envia uma mensagem quando o comando /help é emitido."""
    await update.message.reply_text(
        "Para registrar um gasto, use frases como:\n"
        "- `gastei 30 no almoço`\n"
        "- `paguei 15 de gasolina`\n"
        "- `cinema 40 ontem`\n\n"
        "Para registrar um ganho, use frases como:\n"
        "- `recebi 1000 de salário`\n"
        "- `ganhei 50 de freelance`\n"
        "- `vendi algo por 200 hoje`\n\n"
        "Para ver seu balanço mensal, digite `balanço`."
    )

# --- Handler ATUALIZADO: Lida com todas as mensagens de texto ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lida com todas as mensagens de texto."""
    user_message = update.message.text
    chat_id = update.message.chat_id

    print(f"Mensagem recebida de {chat_id}: {user_message}")

    if user_message:
        if "balanço" in user_message.lower() or "balanco" in user_message.lower() or "saldo" in user_message.lower():
            chart_buffer = generate_balance_chart()
            if chart_buffer:
                chart_buffer.name = 'balanco_chart.png'
                await update.message.reply_photo(photo=chart_buffer, caption="Aqui está seu balanço mensal:")
            else:
                await update.message.reply_text("Ainda não tenho dados suficientes para gerar um balanço. Registre alguns gastos e ganhos primeiro!")
        else:
            transaction_info = extract_transaction_info(user_message)
            if transaction_info and transaction_info.get('valor') is not None:
                valor = float(transaction_info['valor'])
                data = transaction_info.get('data', str(datetime.date.today()))
                
                if transaction_info.get('tipo') == 'gasto':
                    categoria = transaction_info.get('categoria', 'Outros')
                    if add_gasto(valor, categoria, data):
                        await update.message.reply_text(f"Gasto de R${valor:.2f} em '{categoria}' registrado com sucesso!")
                    else:
                        await update.message.reply_text("Ocorreu um erro ao registrar seu gasto. Tente novamente mais tarde.")
                elif transaction_info.get('tipo') == 'ganho':
                    descricao = transaction_info.get('descricao', 'Diversos')
                    if add_ganho(valor, descricao, data):
                        await update.message.reply_text(f"Ganho de R${valor:.2f} de '{descricao}' registrado com sucesso!")
                    else:
                        await update.message.reply_text("Ocorreu um erro ao registrar seu ganho. Tente novamente mais tarde.")
                else:
                    await update.message.reply_text("Não consegui identificar se é um gasto ou um ganho. Tente algo como 'gastei 30 no almoço' ou 'recebi 1000 de salário'.")
            else:
                await update.message.reply_text("Não consegui identificar uma transação válida. Tente algo como 'gastei 30 no almoço' ou 'recebi 1000 de salário'.")

# --- Função Principal ---
def main() -> None:
    """Inicia o bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"Bot Telegram iniciado! Procure por @<nome_do_seu_bot> no Telegram e comece a conversar.")
    print("Certifique-se de que o Ollama está rodando e o modelo 'llama3' (ou o que você configurou) está baixado.")
    print("Verifique também se suas credenciais do Supabase estão corretas e a tabela 'ganhos' foi criada.")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()