# src/core/ai.py
import requests
import json
import datetime
from typing import Dict, Any, Union, List

from src.config import OLLAMA_API_URL, OLLAMA_MODEL

def ask_llama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    """Envia um prompt para o modelo Llama via Ollama API local."""
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

def extract_transaction_info(text: str) -> Union[Dict[str, Any], None]:
    """
    Extrai informações de uma transação (gasto ou ganho) ou um comando de adicionar categoria/mostrar gráfico usando o Llama.
    Retorna um dicionário com 'intencao', e outros dados relevantes.
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    two_days_ago_str = (datetime.date.today() - datetime.timedelta(days=2)).strftime("%Y-%m-%d")
    last_week_day_str = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    # Para o mês atual
    current_month_start_str = datetime.date.today().replace(day=1).strftime("%Y-%m-%d")
    current_month_end_date = (datetime.date.today().replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
    current_month_end_str = current_month_end_date.strftime("%Y-%m-%d")
    # Para o mês anterior
    last_month_end_date = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
    last_month_start_date = last_month_end_date.replace(day=1)
    last_month_start_str = last_month_start_date.strftime("%Y-%m-%d")
    last_month_end_str = last_month_end_date.strftime("%Y-%m-%d")


    prompt = f"""
    Sua única tarefa é extrair informações da mensagem do usuário e retornar APENAS um objeto JSON.
    Não adicione nenhum texto explicativo, comentários ou formatação extra.

    Identifique a intenção:
    - Registrar um gasto
    - Registrar um ganho
    - Adicionar uma nova categoria de gasto
    - Mostrar o gráfico de balanço (ganhos vs. gastos)
    - Mostrar o gráfico de gastos por categoria (com ou sem filtros)
    - Mostrar o gráfico de gastos por forma de pagamento (com ou sem filtros)
    - Mostrar o gráfico de gastos mensais por categoria e forma de pagamento (combinado)

    Formato JSON:
    - Para "gasto": {{"intencao": "gasto", "valor": float, "categoria": "...", "data": "AAAA-MM-DD", "forma_pagamento": "..." (ou null), "descricao_gasto": "..."}}
    - Para "ganho": {{"intencao": "ganho", "valor": float, "descricao": "...", "data": "AAAA-MM-DD"}}
    - Para "adicionar_categoria": {{"intencao": "adicionar_categoria", "categoria_nome": "...", "limite_mensal": float ou null}}
    - Para mostrar gráficos:
        - {{"intencao": "mostrar_balanco", "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": "..." (ou null), "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_gastos_por_pagamento", "categoria": "..." (ou null), "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_mensal_combinado", "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}} # NOVO JSON PARA ESTE GRÁFICO

    Detalhes de extração:
    - A **data** e **data_inicio/data_fim** devem estar sempre no formato **AAAA-MM-DD**. Se não for mencionada, use a data de **hoje**.
    - Para períodos como "este mês", "mês passado", "julho", "agosto", etc., calcule a data_inicio e data_fim corretas. Se for "julho", "agosto", etc., use o mês do ano corrente.
    - O valor e limite_mensal devem ser números float. Se limite_mensal não for especificado, use null.
    - A forma_pagamento deve ser uma string como "crédito", "débito", "pix", "dinheiro" ou null.
    - **descricao_gasto** deve ser uma string curta e clara que descreve o item ou a atividade do gasto.
    - Se a categoria/descrição (de ganho) não for clara, use "Outros" para gastos e "Diversos" para ganhos.

    ---
    Exemplos de Mostrar Gráficos:
    Usuário: mostre meu balanço
    Resposta: {{"intencao": "mostrar_balanco", "data_inicio": null, "data_fim": null}}

    Usuário: gastos por categoria de julho
    Resposta: {{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": null, "data_inicio": "2025-07-01", "data_fim": "2025-07-31"}}

    Usuário: quero saber os gastos por categoria no credito
    Resposta: {{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": "crédito", "data_inicio": null, "data_fim": null}}

    Usuário: total por forma de pagamento
    Resposta: {{"intencao": "mostrar_grafico_gastos_por_pagamento", "categoria": null, "data_inicio": null, "data_fim": null}}
    
    Usuário: me mostre os gastos por mês, categoria e forma de pagamento
    Resposta: {{"intencao": "mostrar_grafico_mensal_combinado", "data_inicio": null, "data_fim": null}} # NOVO EXEMPLO AQUI

    Usuário: gráfico de gastos por categoria e pagamento de agosto
    Resposta: {{"intencao": "mostrar_grafico_mensal_combinado", "data_inicio": "2025-08-01", "data_fim": "2025-08-31"}} # NOVO EXEMPLO AQUI

    ---
    Mensagem do Usuário: {text}
    ---
    JSON de Saída:
    """
    response_text = ask_llama(prompt)
    print(f"DEBUG Llama response raw: {response_text}")

    try:
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start : json_end + 1]
            json_str = '\n'.join([line for line in json_str.split('\n') if not line.strip().startswith('//')])

            data = json.loads(json_str)
            for key in ['valor', 'limite_mensal']:
                if key in data and isinstance(data[key], str):
                    try:
                        data[key] = float(data[key].replace(',', '.'))
                    except ValueError:
                        data[key] = None
            return data
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Erro ao decodificar JSON ou converter valor do Llama: {e}. Resposta bruta: {response_text}")
    return None

def suggest_category_from_llama(text_from_llama: str, existing_categories: List[str]) -> Union[str, None]:
    # ... (esta função permanece inalterada) ...
    if not existing_categories:
        return None

    categories_str = ", ".join(existing_categories)
    prompt = f"""
    Sua única tarefa é, dado um termo e uma lista de categorias, responder APENAS com o nome da categoria que melhor se encaixa no termo.
    Não adicione nenhum texto explicativo, comentários ou formatação extra.

    Termo: "{text_from_llama}"
    Lista de Categorias: {categories_str}
    
    Se encaixar em mais de uma, escolha a mais provável.
    Se não encaixar em nenhuma, responda APENAS "NENHUMA".

    Exemplos:
    Termo: "mercado"
    Categorias: Alimentacao, Compras, Moradia
    Resposta: Alimentacao

    Termo: "Passagem de ônibus"
    Categorias: Transporte, Viagem, Lazer
    Resposta: Transporte

    ---
    Termo: "{text_from_llama}"
    Lista de Categorias: {categories_str}
    Resposta:
    """
    response = ask_llama(prompt)
    print(f"DEBUG Llama suggestion response raw: {response}")
    cleaned_response = response.strip()
    
    if cleaned_response != "NENHUMA" and cleaned_response in existing_categories:
        return cleaned_response
    
    return None