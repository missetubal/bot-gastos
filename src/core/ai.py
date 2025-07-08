# src/core/ai.py
import requests  # Ainda pode ser útil para outras requisições HTTP
import json
import datetime
from typing import Dict, Any, Union, List
from supabase import Client  # Para tipagem

# Importações para Gemini
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Importa as configurações do Gemini do seu config.py
from src.config import GOOGLE_API_KEY, GEMINI_MODEL

# Configura a API do Gemini com sua chave
genai.configure(api_key=GOOGLE_API_KEY)

# Ajustes de segurança para o Gemini (recomendado para bots)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}


# Função que agora se comunica com o Gemini
def ask_llama(prompt: str, model: str = GEMINI_MODEL) -> str:
    """Envia um prompt para o modelo Gemini."""
    try:
        model_instance = genai.GenerativeModel(
            model_name=model, safety_settings=safety_settings
        )
        response = model_instance.generate_content(prompt)

        # O Gemini pode retornar um erro se a resposta for bloqueada ou vazia
        if not response.parts:  # Verifica se há partes na resposta
            print(f"DEBUG Gemini: Resposta vazia ou bloqueada. Raw: {response}")
            return "Modelo de IA retornou uma resposta vazia ou bloqueada."

        return response.text.strip()
    except Exception as e:
        print(f"Erro ao conectar com Gemini: {e}")
        # Se for um erro 404 de modelo, pode sugerir verificar o nome do modelo
        if "404" in str(e):
            return "Desculpe, o modelo de IA especificado não foi encontrado ou está indisponível. Verifique o nome do modelo."
        return "Desculpe, não consegui processar sua requisição agora. O modelo de IA está offline ou indisponível."


def extract_transaction_info(
    text: str, supabase_client: Client
) -> Union[Dict[str, Any], None]:
    """
    Extrai informações da mensagem do usuário (gasto, ganho, add_categoria, gráficos, ou edição de gasto).
    """
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    two_days_ago_str = (datetime.date.today() - datetime.timedelta(days=2)).strftime(
        "%Y-%m-%d"
    )
    last_week_day_str = (datetime.date.today() - datetime.timedelta(days=7)).strftime(
        "%Y-%m-%d"
    )
    current_month_start_str = datetime.date.today().replace(day=1).strftime("%Y-%m-%d")
    current_month_end_date = (
        datetime.date.today().replace(day=1) + datetime.timedelta(days=32)
    ).replace(day=1) - datetime.timedelta(days=1)
    current_month_end_str = current_month_end_date.strftime("%Y-%m-%d")
    last_month_end_date = datetime.date.today().replace(day=1) - datetime.timedelta(
        days=1
    )
    last_month_start_date = last_month_end_date.replace(day=1)
    last_month_start_str = last_month_start_date.strftime("%Y-%m-%d")
    last_month_end_str = last_month_end_date.strftime("%Y-%m-%d")

    # Pega as categorias existentes para passar ao Gemini
    try:
        from src.core.db import get_categorias  # Importação local para evitar ciclo

        existing_categories_data = get_categorias(supabase_client)
        existing_category_names = [cat["nome"] for cat in existing_categories_data]
    except Exception as e:
        print(f"Erro ao obter categorias para o prompt do Gemini: {e}")
        existing_category_names = [
            "Alimentacao",
            "Transporte",
            "Moradia",
            "Lazer",
            "Saude",
            "Educacao",
            "Outros",
        ]  # Fallback

    categories_list_str = ", ".join(existing_category_names)

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
    - Editar um gasto existente

    Formato JSON:
    - Para "gasto": {{"intencao": "gasto", "valor": float, "categoria": "...", "data": "AAAA-MM-DD", "forma_pagamento": "..." (ou null), "descricao_gasto": "..."}}
    - Para "ganho": {{"intencao": "ganho", "valor": float, "descricao": "...", "data": "AAAA-MM-DD"}}
    - Para "adicionar_categoria": {{"intencao": "adicionar_categoria", "categoria_nome": "...", "limite_mensal": float ou null}}
    - Para mostrar gráficos:
        - {{"intencao": "mostrar_balanco", "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_gastos_categoria", "forma_pagamento": "..." (ou null), "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_gastos_por_pagamento", "categoria": "..." (ou null), "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
        - {{"intencao": "mostrar_grafico_mensal_combinado", "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}}
    - Para "edicao_gasto": {{"intencao": "edicao_gasto", "valor": float (ou null), "categoria": "..." (ou null), "data": "AAAA-MM-DD" (ou null), "descricao_gasto": "..." (ou null)}}
        (Extraia o máximo de informações para identificar o gasto a ser editado)
    - Para "listar_gastos_detalhados": {{"intencao": "listar_gastos_detalhados", "categoria": "..." (ou null), "data_inicio": "AAAA-MM-DD" (ou null), "data_fim": "AAAA-MM-DD" (ou null)}} 


    Detalhes de extração:
    - A **data** e **data_inicio/data_fim** devem estar sempre no formato **AAAA-MM-DD**. Se não for mencionada, use a data de **hoje**.
    - Para períodos como "este mês", "mês passado", "julho", "agosto", etc., calcule a data_inicio e data_fim corretas. Se for "julho", "agosto", etc., use o mês do ano corrente.
    - O valor e limite_mensal devem ser números float. Se limite_mensal não for especificado, use null.
    - A forma_pagamento deve ser uma string como "crédito", "débito", "pix", "dinheiro" ou null.
    - **descricao_gasto** deve ser uma string curta e clara que descreve o item ou a atividade do gasto.
    - Para gastos, a **categoria** deve ser **OBRIGATORIAMENTE** uma das seguintes, ou a mais próxima delas: {categories_list_str}. Se nenhuma se encaixar bem, use "Outros".

    ---
    Exemplos de Gasto:
    Usuário: gastei 50 reais no mercado
    Resposta: {{"intencao": "gasto", "valor": 50.0, "categoria": "Alimentacao", "data": "{today_str}", "forma_pagamento": null, "descricao_gasto": "Compras no mercado"}}

    Exemplos de Edição de Gasto:
    Usuário: edite o gasto de 15 reais no Uber de ontem
    Resposta: {{"intencao": "edicao_gasto", "valor": 15.0, "categoria": "Transporte", "data": "{yesterday_str}", "descricao_gasto": "Uber"}}

    Usuário: corrigir o gasto de 10/07 na Avatim
    Resposta: {{"intencao": "edicao_gasto", "data": "{datetime.date(2025, 7, 10).strftime("%Y-%m-%d")}", "descricao_gasto": "Avatim", "categoria": null, "valor": null}}
    Usuário: 35 de passagem de ônibus no débito ontem
    Resposta: {{"intencao": "gasto", "valor": 35.0, "categoria": "Transporte", "data": "{yesterday_str}", "forma_pagamento": "débito", "descricao_gasto": "Passagem de ônibus"}}

    Usuário: gastei 18,10 com 99 no crédito
    Resposta: {{"intencao": "gasto", "valor": 18.10, "categoria": "Transporte", "data": "{today_str}", "forma_pagamento": "crédito", "descricao_gasto": "Corrida 99"}}

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

   Exemplos de Listar Gastos Detalhados: # <--- NOVOS EXEMPLOS
    Usuário: liste meus gastos de julho
    Resposta: {{"intencao": "listar_gastos_detalhados", "categoria": null, "data_inicio": "2025-07-01", "data_fim": "2025-07-31"}}

    Usuário: listar gastos de transporte no mês passado
    Resposta: {{"intencao": "listar_gastos_detalhados", "categoria": "Transporte", "data_inicio": "{last_month_start_str}", "data_fim": "{last_month_end_str}"}}

    Usuário: quais foram meus gastos com alimentação
    Resposta: {{"intencao": "listar_gastos_detalhados", "categoria": "Alimentacao", "data_inicio": null, "data_fim": null}}

    ---
    Mensagem do Usuário: {text}
    ---
    JSON de Saída:
    """
    response_text = ask_llama(prompt)  # ask_llama chama Gemini agora
    print(f"DEBUG Gemini response raw: {response_text}")

    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}")

        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start : json_end + 1]
            json_str = "\n".join(
                [
                    line
                    for line in json_str.split("\n")
                    if not line.strip().startswith("//")
                ]
            )

            data = json.loads(json_str)
            for key in ["valor", "limite_mensal"]:
                if key in data and isinstance(data[key], str):
                    try:
                        data[key] = float(data[key].replace(",", "."))
                    except ValueError:
                        data[key] = None
            return data
    except (json.JSONDecodeError, ValueError) as e:
        print(
            f"Erro ao decodificar JSON ou converter valor do Gemini: {e}. Resposta bruta: {response_text}"
        )
    return None


def suggest_category_from_llama(
    text_from_llama: str, existing_categories: List[str], supabase_client: Client
) -> Union[str, None]:
    """
    Pede ao Gemini para mapear um termo de categoria para uma das categorias existentes.
    existing_categories deve ser uma lista de nomes de categorias em CamelCase.
    """
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
    response = ask_llama(prompt)  # ask_llama chama Gemini
    print(f"DEBUG Gemini suggestion response raw: {response}")
    cleaned_response = response.strip()

    if cleaned_response != "NENHUMA" and cleaned_response in existing_categories:
        return cleaned_response

    return None


def extract_correction_from_llama(text: str) -> Union[Dict[str, Any], None]:
    """
    Pede ao Gemini para extrair o campo e o novo valor de uma mensagem de correção.
    """
    prompt = f"""
    Sua única tarefa é extrair o campo a ser corrigido e o novo valor da mensagem do usuário.
    Retorne APENAS um objeto JSON. Não adicione nenhum texto explicativo ou formatação extra.

    Campos válidos: "Valor", "Data", "Categoria", "Forma", "Descricao", "Tipo".
    Para o campo "Forma", o valor pode ser "Pix", "Crédito", "Débito", "Dinheiro".
    Para o campo "Tipo", o valor pode ser "Gasto" ou "Ganho".
    A data deve estar no formato AAAA-MM-DD.

    Exemplos:
    Usuário: Categoria Lazer
    Resposta: {{"campo": "categoria", "novo_valor": "Lazer"}}

    Usuário: Valor 60.50
    Resposta: {{"campo": "valor", "novo_valor": 60.50}}

    Usuário: Data 2025-07-01
    Resposta: {{"campo": "data", "novo_valor": "2025-07-01"}}

    Usuário: Forma Pix
    Resposta: {{"campo": "forma", "novo_valor": "Pix"}}

    Usuário: Tipo Ganho
    Resposta: {{"campo": "tipo", "novo_valor": "Ganho"}}
    
    ---
    Mensagem do Usuário: {text}
    ---
    JSON de Saída:
    """
    response_text = ask_llama(prompt)  # ask_llama chama Gemini
    print(f"DEBUG Gemini correction raw: {response_text}")

    try:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}")
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start : json_end + 1]
            json_str = "\n".join(
                [
                    line
                    for line in json_str.split("\n")
                    if not line.strip().startswith("//")
                ]
            )
            data = json.loads(json_str)
            if data.get("campo", "").lower() == "valor" and isinstance(
                data.get("novo_valor"), str
            ):
                try:
                    data["novo_valor"] = float(data["novo_valor"].replace(",", "."))
                except ValueError:
                    pass
            return data
    except (json.JSONDecodeError, ValueError) as e:
        print(
            f"Erro ao decodificar JSON de correção do Gemini: {e}. Resposta bruta: {response_text}"
        )
    return None
