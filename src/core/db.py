# src/core/db.py
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY
from typing import Union, List, Dict, Any
from src.utils.text_utils import to_camel_case

def get_supabase_client() -> Client:
    """Retorna uma instância do cliente Supabase."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Funções para Formas de Pagamento ---
def get_formas_pagamento(supabase_client: Client) -> list:
    """Obtém todas as formas de pagamento do Supabase."""
    try:
        response = supabase_client.table('formas_pagamento').select('id,nome').order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter formas de pagamento do Supabase: {e}")
        return []

def get_forma_pagamento_id_by_name(supabase_client: Client, nome: str) -> Union[str, None]:
    """Obtém o ID de uma forma de pagamento pelo nome (case-insensitive)."""
    try:
        nome_lower = nome.lower()
        response = supabase_client.table('formas_pagamento').select('id,nome').execute()
        
        for fp in response.data:
            if fp['nome'].lower() == nome_lower:
                return fp['id']
        return None
    except Exception as e:
        print(f"Erro ao buscar ID da forma de pagamento '{nome}': {e}")
        return None

# --- Funções para Gastos ---
def add_gasto(supabase_client: Client, valor: float, categoria_id: str, data: str, forma_pagamento_id: Union[str, None] = None, descricao: Union[str, None] = None) -> bool:
    """Adiciona um novo gasto ao Supabase, incluindo a descrição e forma de pagamento."""
    try:
        response = supabase_client.table('gastos').insert({
            "valor": valor,
            "categoria_id": categoria_id,
            "data": data,
            "forma_pagamento_id": forma_pagamento_id,
            "descricao": descricao
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar gasto ao Supabase: {e}")
        return False

def get_gastos(supabase_client: Client) -> list:
    """Obtém todos os gastos do Supabase."""
    try:
        response = supabase_client.table('gastos').select('valor,categoria_id,data,descricao,formas_pagamento(nome),categorias(nome)').order('data', desc=True).execute()
        gastos_formatados = []
        for gasto in response.data:
            gasto_copy = gasto.copy()
            # Pega o nome da categoria
            if 'categorias' in gasto_copy and gasto_copy['categorias'] and 'nome' in gasto_copy['categorias']:
                gasto_copy['categoria_nome'] = gasto_copy['categorias']['nome']
            else:
                gasto_copy['categoria_nome'] = 'Desconhecida'
            del gasto_copy['categorias']

            # Pega o nome da forma de pagamento
            if 'formas_pagamento' in gasto_copy and gasto_copy['formas_pagamento'] and 'nome' in gasto_copy['formas_pagamento']:
                gasto_copy['forma_pagamento_nome'] = gasto_copy['formas_pagamento']['nome']
            else:
                gasto_copy['forma_pagamento_nome'] = 'Não Informado'
            del gasto_copy['formas_pagamento'] # Remove o objeto aninhado
            
            gastos_formatados.append(gasto_copy)
        return gastos_formatados
    except Exception as e:
        print(f"Erro ao obter gastos do Supabase: {e}")
        return []

def get_gastos_by_category(supabase_client: Client, categoria_id: str) -> list:
    """Obtém os gastos de uma categoria específica do Supabase."""
    try:
        # ATENÇÃO AQUI: Mudado para 'formas_pagamento(nome)' (plural)
        response = supabase_client.table('gastos').select('valor,data,descricao,formas_pagamento(nome)').eq('categoria_id', categoria_id).execute()
        gastos_formatados = []
        for gasto in response.data:
            gasto_copy = gasto.copy()
            # ATENÇÃO AQUI: Mudado para 'formas_pagamento' (plural) para extrair o nome
            if 'formas_pagamento' in gasto_copy and gasto_copy['formas_pagamento'] and 'nome' in gasto_copy['formas_pagamento']:
                gasto_copy['forma_pagamento_nome'] = gasto_copy['formas_pagamento']['nome']
            else:
                gasto_copy['forma_pagamento_nome'] = 'Não Informado'
            del gasto_copy['formas_pagamento']
            gastos_formatados.append(gasto_copy)
        return gastos_formatados
    except Exception as e:
        print(f"Erro ao obter gastos da categoria {categoria_id} do Supabase: {e}")
        return []

# --- Funções para Ganhos ---
def add_ganho(supabase_client: Client, valor: float, descricao: str, data: str) -> bool:
    """Adiciona um novo ganho ao Supabase."""
    try:
        response = supabase_client.table('ganhos').insert({
            "valor": valor,
            "descricao": descricao,
            "data": data
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar ganho ao Supabase: {e}")
        return False

def get_ganhos(supabase_client: Client) -> list:
    """Obtém todos os ganhos do Supabase."""
    try:
        response = supabase_client.table('ganhos').select('valor,descricao,data').order('data', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter ganhos do Supabase: {e}")
        return []

# --- Funções para Categorias ---
def add_categoria(supabase_client: Client, nome: str, limite_mensal: Union[float, None] = None, aliases: Union[List[str], None] = None) -> bool:
    """Adiciona uma nova categoria ao Supabase."""
    nome_camel_case = to_camel_case(nome)

    try:
        existing_category = supabase_client.table('categorias').select('id').eq('nome', nome_camel_case).execute().data
        if existing_category:
            print(f"Categoria '{nome_camel_case}' já existe.")
            return False

        response = supabase_client.table('categorias').insert({
            "nome": nome_camel_case,
            "limite_mensal": limite_mensal,
            "aliases": aliases
        }).execute()
        return True
    except Exception as e:
        print(f"Erro ao adicionar categoria ao Supabase: {e}")
        return False

def get_categorias(supabase_client: Client) -> list:
    """Obtém todas as categorias do Supabase."""
    try:
        response = supabase_client.table('categorias').select('id,nome,limite_mensal,aliases').order('nome').execute()
        return response.data
    except Exception as e:
        print(f"Erro ao obter categorias do Supabase: {e}")
        return []

def get_categoria_id_by_text(supabase_client: Client, text_from_llama: str) -> Union[str, None]:
    """
    Tenta encontrar o ID da categoria com base no texto extraído pelo Llama.
    Prioriza correspondência exata, depois busca em aliases.
    """
    nome_normalizado_llama = to_camel_case(text_from_llama)
    
    categorias = get_categorias(supabase_client)
    text_lower = text_from_llama.lower()

    for cat in categorias:
        if cat['nome'].lower() == text_lower or cat['nome'] == nome_normalizado_llama:
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
    
    categorias_do_banco = get_categorias(supabase_client)
    existing_category_names = [cat['nome'] for cat in categorias_do_banco]
    
    llama_suggestion_name = suggest_category_from_llama(text, existing_category_names, supabase_client)
    
    if llama_suggestion_name:
        for cat in categorias_do_banco:
            if cat['nome'] == llama_suggestion_name:
                return [{'id': cat['id'], 'nome': cat['nome']}]
    
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
            if cat['nome'] in suggested_names:
                similar_cats.append({'id': cat['id'], 'nome': cat['nome']})
        unique_similar_cats = []
        seen_ids = set()
        for cat_info in similar_cats:
            if cat_info['id'] not in seen_ids:
                unique_similar_cats.append(cat_info)
                seen_ids.add(cat_info['id'])
        if unique_similar_cats:
            return unique_similar_cats

    for cat in categorias_do_banco:
        if text_lower in cat['nome'].lower() or cat['nome'].lower() in text_lower or \
           text_camel_case in cat['nome'] or cat['nome'] in text_camel_case:
            similar_cats.append({'id': cat['id'], 'nome': cat['nome']})
        
        if cat['aliases'] and isinstance(cat['aliases'], list):
            for alias in cat['aliases']:
                if text_lower in alias.lower():
                    similar_cats.append({'id': cat['id'], 'nome': cat['nome']})
    
    unique_similar_cats = []
    seen_ids = set()
    for cat_info in similar_cats:
        if cat_info['id'] not in seen_ids:
            unique_similar_cats.append(cat_info)
            seen_ids.add(cat_info['id'])
    
    return unique_similar_cats

def update_categoria_limite(supabase_client: Client, categoria_id: str, novo_limite: Union[float, None]) -> bool:
    """Atualiza o limite mensal de uma categoria."""
    try:
        response = supabase_client.table('categorias').update({'limite_mensal': novo_limite}).eq('id', categoria_id).execute()
        return True
    except Exception as e:
        print(f"Erro ao atualizar limite da categoria: {e}")
        return False

def update_categoria_aliases(supabase_client: Client, categoria_id: str, new_aliases: List[str]) -> bool:
    """Atualiza os aliases de uma categoria."""
    try:
        response = supabase_client.table('categorias').update({'aliases': new_aliases}).eq('id', categoria_id).execute()
        return True
    except Exception as e:
        print(f"Erro ao atualizar aliases da categoria: {e}")
        return False