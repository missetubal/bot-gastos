# src/core/db.py
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from typing import Union, List, Dict, Any
from src.utils.text_utils import to_camel_case

def get_supabase_client() -> Client:
    """Retorna uma instância do cliente Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funções para Formas de Pagamento ---
def get_payment_methods(supabase_client: Client) -> list:
    """Obtém todas as formas de pagamento do Supabase."""
    try:
        response = supabase_client.table('payment_methods').select('id,name').order('name').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter formas de pagamento do Supabase: {e}")
        return []

def get_payment_method_id_by_name(supabase_client: Client, name: str) -> Union[str, None]:
    """Obtém o ID de uma forma de pagamento pelo name (case-insensitive)."""
    try:
        name_lower = name.lower()
        response = supabase_client.table('payment_methods').select('id,name').execute()
        
        for fp in response.data:
            if fp['name'].lower() == name_lower:
                return fp['id']
        return None
    except Exception as e:
        print(f"Erro ao buscar ID da forma de pagamento '{name}': {e}")
        return None

# --- Funções para Gastos ---
def add_expense(supabase_client: Client, value: float, category_id: str, date: str, payment_method_id: Union[str, None] = None, description: Union[str, None] = None) -> bool:
    """Adiciona um novo gasto ao Supabase, incluindo a descrição e forma de pagamento."""
    try:
        response = supabase_client.table('expenses').insert({
            "value": value,
            "category_id": category_id,
            "date": date,
            "payment_method_id": payment_method_id,
            "description": description
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar gasto ao Supabase: {e}")
        return False

def get_gastos(supabase_client: Client) -> list:
    """Obtém todos os gastos do Supabase."""
    try:
        response = supabase_client.table('expenses').select('value,category_id,date,description,payment_methods(name),categories(name)').order('date', desc=True).execute()
        gastos_formatados = []
        for gasto in response.data:
            gasto_copy = gasto.copy()
            if 'categories' in gasto_copy and gasto_copy['categories'] and 'name' in gasto_copy['categories']:
                gasto_copy['categoria_nome'] = gasto_copy['categories']['name']
            else:
                gasto_copy['categoria_nome'] = 'Desconhecida'
            del gasto_copy['categories']

            # Pega o nome da forma de pagamento
            if 'payment_methods' in gasto_copy and gasto_copy['payment_methods'] and 'name' in gasto_copy['payment_methods']:
                gasto_copy['forma_pagamento_nome'] = gasto_copy['payment_methods']['name']
            else:
                gasto_copy['forma_pagamento_nome'] = 'Não Informado'
            del gasto_copy['payment_methods'] # Remove o objeto aninhado
            
            gastos_formatados.append(gasto_copy)
        return gastos_formatados
    except Exception as e:
        print(f"Erro ao obter gastos do Supabase: {e}")
        return []

def get_expense_by_category(supabase_client: Client, category_id: str) -> list:
    """Obtém os gastos de uma categoria específica do Supabase."""
    try:
        # ATENÇÃO AQUI: Mudado para 'payment_methods(nome)' (plural)
        response = supabase_client.table('expenses').select('value,date,description,payment_methods(name)').eq('category_id', category_id).execute()
        gastos_formatados = []
        for gasto in response.data:
            gasto_copy = gasto.copy()
            # ATENÇÃO AQUI: Mudado para 'payment_methods' (plural) para extrair o nome
            if 'payment_methods' in gasto_copy and gasto_copy['payment_methods'] and 'name' in gasto_copy['payment_methods']:
                gasto_copy['forma_pagamento_nome'] = gasto_copy['payment_methods']['name']
            else:
                gasto_copy['forma_pagamento_nome'] = 'Não Informado'
            del gasto_copy['payment_methods']
            gastos_formatados.append(gasto_copy)
        return gastos_formatados
    except Exception as e:
        print(f"Erro ao obter gastos da categoria {category_id} do Supabase: {e}")
        return []

# --- Funções para Ganhos ---
def add_ganho(supabase_client: Client, value: float, description: str, date: str) -> bool:
    """Adiciona um novo ganho ao Supabase."""
    try:
        response = supabase_client.table('ganhos').insert({
            "value": value,
            "description": description,
            "date": date
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar ganho ao Supabase: {e}")
        return False

def get_ganhos(supabase_client: Client) -> list:
    """Obtém todos os ganhos do Supabase."""
    try:
        response = supabase_client.table('ganhos').select('value,description,date').order('date', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter ganhos do Supabase: {e}")
        return []

# --- Funções para Categorias ---
def add_category(supabase_client: Client, name: str, monthly_limit: Union[float, None] = None, aliases: Union[List[str], None] = None) -> bool:
    """Adiciona uma nova categoria ao Supabase."""
    name_camel_case = to_camel_case(name)

    try:
        existing_category = supabase_client.table('categories').select('id').eq('name', name_camel_case).execute().data
        if existing_category:
            print(f"Categoria '{name_camel_case}' já existe.")
            return False

        response = supabase_client.table('categories').insert({
            "name": name_camel_case,
            "monthly_limit": monthly_limit,
            "aliases": aliases
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar categoria ao Supabase: {e}")
        return False

def get_categories(supabase_client: Client) -> list:
    """Obtém todas as categorias do Supabase."""
    try:
        response = supabase_client.table('categories').select('id,name,monthly_limit,aliases').order('name').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter categorias do Supabase: {e}")
        return []

def get_category_id_by_text(supabase_client: Client, text_from_llama: str) -> Union[str, None]:
    """
    Tenta encontrar o ID da categoria com base no texto extraído pelo Llama.
    Prioriza correspondência exata, depois busca em aliases.
    """
    nome_normalizado_llama = to_camel_case(text_from_llama)
    
    categorias = get_categories(supabase_client)
    text_lower = text_from_llama.lower()

    for cat in categorias:
        if cat['name'].lower() == text_lower or cat['name'] == nome_normalizado_llama:
            return cat['id']

    for cat in categorias:
        if cat['aliases'] and isinstance(cat['aliases'], list):
            if text_lower in [alias.lower() for alias in cat['aliases']]:
                return cat['id']
    
    return None

def find_similar_categories(supabase_client: Client, text: str) -> List[Dict[str, Any]]:
    """
    Busca categorias existentes que são similares ao texto fornecido,
    primeiro por sugestão do Llama, depois por correspondência parcial.
    Retorna uma lista de dicionários {id, nome}.
    """
    # Importação local para evitar ciclo
    from src.core.ai import suggest_category_from_llama # Importa AQUI
    
    categorias_do_banco = get_categories(supabase_client)
    existing_category_names = [cat['name'] for cat in categorias_do_banco]
    
    llama_suggestion_name = suggest_category_from_llama(text, existing_category_names, supabase_client)
    
    if llama_suggestion_name:
        for cat in categorias_do_banco:
            if cat['name'] == llama_suggestion_name:
                return [{'id': cat['id'], 'name': cat['name']}]
    
    text_lower = text.lower()
    text_camel_case = to_camel_case(text)

    similar_cats = []
    
    ambiguous_terms_map = {
        "mercado": ["Alimentacao", "Compras"],
        "farmacia": ["Saude", "Compras"],
        "transporte": ["Transporte", "Carro", "Viagem"],
        "lazer": ["Lazer", "Entretenimento"],
        "casa": ["Casa", "Moradia"],
        "contas": ["Contas", "Moradia"]
    }

    if text_lower in ambiguous_terms_map:
        suggested_names = ambiguous_terms_map[text_lower]
        for cat in categorias_do_banco:
            if cat['name'] in suggested_names:
                similar_cats.append({'id': cat['id'], 'name': cat['name']})
        unique_similar_cats = []
        seen_ids = set()
        for cat_info in similar_cats:
            if cat_info['id'] not in seen_ids:
                unique_similar_cats.append(cat_info)
                seen_ids.add(cat_info['id'])
        if unique_similar_cats:
            return unique_similar_cats

    for cat in categorias_do_banco:
        if text_lower in cat['name'].lower() or cat['name'].lower() in text_lower or \
           text_camel_case in cat['name'] or cat['name'] in text_camel_case:
            similar_cats.append({'id': cat['id'], 'name': cat['name']})
        
        if cat['aliases'] and isinstance(cat['aliases'], list):
            for alias in cat['aliases']:
                if text_lower in alias.lower():
                    similar_cats.append({'id': cat['id'], 'name': cat['name']})
    
    unique_similar_cats = []
    seen_ids = set()
    for cat_info in similar_cats:
        if cat_info['id'] not in seen_ids:
            unique_similar_cats.append(cat_info)
            seen_ids.add(cat_info['id'])
    
    return unique_similar_cats

def update_categoria_limite(supabase_client: Client, category_id: str, new_limit: Union[float, None]) -> bool:
    """Atualiza o limite mensal de uma categoria."""
    try:
        response = supabase_client.table('categories').update({'monthly_limit': new_limit}).eq('id', category_id).execute()
        return True
    except Exception as e:
        print(f"Erro ao atualizar limite da categoria: {e}")
        return False

def update_category_aliases(supabase_client: Client, category_id: str, new_aliases: List[str]) -> bool:
    """Atualiza os aliases de uma categoria."""
    try:
        response = supabase_client.table('categories').update({'aliases': new_aliases}).eq('id', category_id).execute()
        return True
    except Exception as e:
        print(f"Erro ao atualizar aliases da categoria: {e}")
        return False