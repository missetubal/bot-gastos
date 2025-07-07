# src/core/charts.py
import pandas as pd
import matplotlib.pyplot as plt
import io
import matplotlib.ticker as mticker
from typing import Union, Dict, Any, List
from supabase import Client
import datetime

# Configurações globais para os gráficos (cores, fontes, etc.)
plt.style.use('seaborn-v0_8-darkgrid') # Um estilo de grade escuro e moderno
plt.rcParams['font.family'] = 'sans-serif' # Fonte padrão
plt.rcParams['font.size'] = 10 # Tamanho da fonte padrão
plt.rcParams['axes.labelsize'] = 12 # Tamanho da fonte dos rótulos dos eixos
plt.rcParams['axes.titlesize'] = 14 # Tamanho da fonte dos títulos
plt.rcParams['xtick.labelsize'] = 10 # Tamanho da fonte dos rótulos do eixo X
plt.rcParams['ytick.labelsize'] = 10 # Tamanho da fonte dos rótulos do eixo Y
plt.rcParams['legend.fontsize'] = 10 # Tamanho da fonte da legenda

# Cores personalizadas para os gráficos
COLORS = {
    'Ganho': '#28a745', # Verde vibrante
    'Gasto': '#dc3545', # Vermelho vibrante
    'Balanço': '#007bff', # Azul vibrante
    'Fatias_Variadas': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'] # Cores para gráficos de pizza/barras
}


# --- Função de Ajuda para Filtrar Gastos ---
def filter_gastos_data(gastos_data: List[Dict[str, Any]], 
                       categoria_id: Union[str, None] = None, 
                       forma_pagamento_id: Union[str, None] = None, 
                       data_inicio: Union[str, None] = None, 
                       data_fim: Union[str, None] = None) -> List[Dict[str, Any]]:
    
    df = pd.DataFrame(gastos_data)
    if df.empty:
        return []

    # Converte a coluna de data para datetime
    df['data'] = pd.to_datetime(df['data'])

    # Filtra por categoria
    if categoria_id:
        df = df[df['categoria_id'] == categoria_id]

    # Filtra por forma de pagamento
    if forma_pagamento_id:
        df = df[df['forma_pagamento_id'] == forma_pagamento_id]

    # Filtra por período de datas
    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df = df[df['data'] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        # Se a data fim for o último dia do mês, garantimos que inclui o dia inteiro
        if end_date.day == (end_date + pd.Timedelta(days=1)).day -1: # Verifica se é o último dia do mês
             end_date = end_date.replace(hour=23, minute=59, second=59)
        df = df[df['data'] <= end_date]


    return df.to_dict(orient='records')


# --- ATUALIZADO: generate_balance_chart ---
def generate_balance_chart(supabase_client: Client, 
                           data_inicio: Union[str, None] = None, 
                           data_fim: Union[str, None] = None) -> Union[io.BytesIO, None]:
    """Gera um gráfico de balanço mensal de ganhos vs. gastos, com filtros de data."""
    try:
        gastos_data_raw = supabase_client.table('gastos').select('valor,data').execute().data
        ganhos_data_raw = supabase_client.table('ganhos').select('valor,data').execute().data
    except Exception as e:
        print(f"Erro ao obter dados para gráfico de balanço: {e}")
        return None

    # Aplica filtro de data aos gastos e ganhos
    gastos_data = filter_gastos_data(gastos_data_raw, data_inicio=data_inicio, data_fim=data_fim)
    ganhos_data = filter_gastos_data(ganhos_data_raw, data_inicio=data_inicio, data_fim=data_fim)

    if not gastos_data and not ganhos_data:
        return None

    df_gastos = pd.DataFrame(gastos_data)
    if not df_gastos.empty:
        df_gastos['data'] = pd.to_datetime(df_gastos['data'])
        df_gastos['tipo'] = 'Gasto'
    else:
        df_gastos = pd.DataFrame(columns=['valor', 'data', 'tipo'])

    df_ganhos = pd.DataFrame(ganhos_data)
    if not df_ganhos.empty:
        df_ganhos['data'] = pd.to_datetime(df_ganhos['data'])
        df_ganhos['tipo'] = 'Ganho'
    else:
        df_ganhos = pd.DataFrame(columns=['valor', 'data', 'tipo'])

    df_all = pd.concat([df_gastos, df_ganhos], ignore_index=True)
    if df_all.empty:
        return None

    df_all['mes_ano'] = df_all['data'].dt.to_period('M')

    monthly_summary = df_all.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack(fill_value=0)
    monthly_summary['Balanço'] = monthly_summary.get('Ganho', 0) - monthly_summary.get('Gasto', 0)
    monthly_summary = monthly_summary.sort_index()

    plt.figure(figsize=(12, 7))
    ax = monthly_summary[['Ganho', 'Gasto', 'Balanço']].plot(
        kind='bar', 
        figsize=(12, 7),
        color=[COLORS['Ganho'], COLORS['Gasto'], COLORS['Balanço']] # Usando cores da config
    )

    plt.title('Balanço Mensal: Ganhos vs. Gastos', fontsize=16, fontweight='bold')
    plt.ylabel('Valor (R$)', fontsize=12)
    plt.xlabel('Mês/Ano', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(title='Tipo de Transação', fontsize=10, title_fontsize=11)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Adicionar rótulos de valor nas barras
    for container in ax.containers:
        ax.bar_label(container, fmt='R$%.2f', fontsize=8, padding=3)

    formatter = mticker.FormatStrFormatter('R$%.2f')
    ax.yaxis.set_major_formatter(formatter)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300) # Aumentar DPI para melhor qualidade
    buf.seek(0)
    plt.close()
    return buf

# --- ATUALIZADO: generate_category_spending_chart ---
def generate_category_spending_chart(supabase_client: Client, 
                                     forma_pagamento_id: Union[str, None] = None, 
                                     data_inicio: Union[str, None] = None, 
                                     data_fim: Union[str, None] = None) -> Union[io.BytesIO, None]:
    """Gera um gráfico de gastos por categoria e compara com os limites, com filtros."""
    try:
        gastos_data_raw = supabase_client.table('gastos').select('valor,categoria_id,data,formas_pagamento(nome),categorias(nome,limite_mensal),forma_pagamento_id').execute().data
        categorias_data_full = supabase_client.table('categorias').select('id,nome,limite_mensal').execute().data
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico de categoria: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        if 'categorias' in gasto_copy and 'nome' in gasto_copy['categorias']:
            gasto_copy['categoria_nome'] = gasto_copy['categorias']['nome']
            gasto_copy['limite_mensal_categoria'] = gasto_copy['categorias']['limite_mensal']
        else:
            gasto_copy['categoria_nome'] = 'Desconhecida'
            gasto_copy['limite_mensal_categoria'] = None
        del gasto_copy['categorias']

        if 'formas_pagamento' in gasto_copy and gasto_copy['formas_pagamento'] and 'nome' in gasto_copy['formas_pagamento']:
            gasto_copy['forma_pagamento_nome'] = gasto_copy['formas_pagamento']['nome']
        else:
            gasto_copy['forma_pagamento_nome'] = 'Não Informado'
        del gasto_copy['formas_pagamento']
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty: return None

    df_gastos['data'] = pd.to_datetime(df_gastos['data'])

    if forma_pagamento_id:
        df_gastos = df_gastos[df_gastos['forma_pagamento_id'] == forma_pagamento_id]
    
    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos['data'] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos['data'] <= end_date]

    if df_gastos.empty: return None

    gastos_por_categoria = df_gastos.groupby('categoria_nome')['valor'].sum().sort_values(ascending=False)

    if gastos_por_categoria.empty:
        return None

    limites_por_categoria = {cat['nome']: cat['limite_mensal'] for cat in categorias_data_full}

    categorias_plot = gastos_por_categoria.index.tolist()
    valores_gastos = gastos_por_categoria.values.tolist()
    
    plt.figure(figsize=(12, 7))
    ax = plt.subplot(111)

    bars = ax.bar(categorias_plot, valores_gastos, color=COLORS['Fatias_Variadas'], label='Gasto Total')

    plt.title('Gastos por Categoria vs. Limite Mensal', fontsize=16, fontweight='bold')
    plt.ylabel('Valor (R$)', fontsize=12)
    plt.xlabel('Categoria', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    ax.bar_label(bars, fmt='R$%.2f', fontsize=8, padding=3)


    for i, cat_nome in enumerate(categorias_plot):
        limite_atual = limites_por_categoria.get(cat_nome)
        if limite_atual is not None and limite_atual > 0:
            bar_x = bars[i].get_x()
            bar_width = bars[i].get_width()
            ax.hlines(limite_atual, bar_x, bar_x + bar_width,
                      colors='darkgreen', linestyles='--', label='Limite Mensal' if i == 0 else "")

            if valores_gastos[i] > limite_atual:
                ax.text(bar_x + bar_width / 2,
                        max(valores_gastos[i], limite_atual) + 5,
                        'EXCEDIDO!', ha='center', va='bottom', color='red', fontsize=9, weight='bold')

    formatter = mticker.FormatStrFormatter('R$%.2f')
    ax.yaxis.set_major_formatter(formatter)

    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    ax.legend(unique_labels.values(), unique_labels.keys(), fontsize=10)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close()
    return buf

# --- ATUALIZADO: generate_payment_method_spending_chart ---
def generate_payment_method_spending_chart(supabase_client: Client, 
                                          categoria_id: Union[str, None] = None, 
                                          data_inicio: Union[str, None] = None, 
                                          data_fim: Union[str, None] = None) -> Union[io.BytesIO, None]:
    """Gera um gráfico do total de gastos por forma de pagamento, com filtros."""
    try:
        gastos_data_raw = supabase_client.table('gastos').select('valor,data,formas_pagamento(nome),categoria_id').execute().data
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico de formas de pagamento: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        if 'formas_pagamento' in gasto_copy and gasto_copy['formas_pagamento'] and 'nome' in gasto_copy['formas_pagamento']:
            gasto_copy['forma_pagamento_nome'] = gasto_copy['formas_pagamento']['nome']
        else:
            gasto_copy['forma_pagamento_nome'] = 'Não Informado'
        del gasto_copy['formas_pagamento']
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty: return None

    df_gastos['data'] = pd.to_datetime(df_gastos['data'])

    if categoria_id:
        df_gastos = df_gastos[df_gastos['categoria_id'] == categoria_id]

    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos['data'] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos['data'] <= end_date]

    if df_gastos.empty: return None

    gastos_por_forma = df_gastos.groupby('forma_pagamento_nome')['valor'].sum().sort_values(ascending=False)

    if gastos_por_forma.empty:
        return None

    plt.figure(figsize=(10, 7))
    ax = gastos_por_forma.plot(
        kind='pie', 
        autopct=lambda p: f'R${(p*sum(gastos_por_forma)/100):.2f}', 
        startangle=90, 
        cmap='Paired',
        pctdistance=0.85
    )
    plt.title('Gastos por Forma de Pagamento', fontsize=16, fontweight='bold')
    plt.ylabel('')
    plt.tight_layout()
    plt.axis('equal')

    wedges, texts, autotexts = ax.pie(gastos_por_forma, autopct='', startangle=90, cmap='Paired')
    labels = [f"{name}: R${value:.2f}" for name, value in gastos_por_forma.items()]
    ax.legend(wedges, labels,
              title="Forma de Pagamento",
              loc="center left",
              bbox_to_anchor=(1, 0, 0.5, 1))

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close()
    return buf

# --- NOVA FUNÇÃO: Gerar Gráfico de Gastos Mensais por Categoria e Forma de Pagamento ---
def generate_monthly_category_payment_chart(supabase_client: Client, 
                                            data_inicio: Union[str, None] = None, 
                                            data_fim: Union[str, None] = None) -> Union[io.BytesIO, None]:
    """
    Gera um gráfico de barras empilhadas mostrando gastos por mês/categoria, 
    com as formas de pagamento como sub-divisões.
    """
    try:
        # Pega todos os dados necessários
        gastos_data_raw = supabase_client.table('gastos').select('valor,data,formas_pagamento(nome),categorias(nome)').execute().data
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico mensal combinado: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        # Extrai nome da categoria
        if 'categorias' in gasto_copy and gasto_copy['categorias'] and 'nome' in gasto_copy['categorias']:
            gasto_copy['categoria_nome'] = gasto_copy['categorias']['nome']
        else:
            gasto_copy['categoria_nome'] = 'Desconhecida'
        del gasto_copy['categorias']

        # Extrai nome da forma de pagamento
        if 'formas_pagamento' in gasto_copy and gasto_copy['formas_pagamento'] and 'nome' in gasto_copy['formas_pagamento']:
            gasto_copy['forma_pagamento_nome'] = gasto_copy['formas_pagamento']['nome']
        else:
            gasto_copy['forma_pagamento_nome'] = 'Não Informado'
        del gasto_copy['formas_pagamento']
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty:
        return None

    df_gastos['data'] = pd.to_datetime(df_gastos['data'])
    
    # Aplica filtros de data
    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos['data'] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos['data'] <= end_date]

    if df_gastos.empty:
        return None

    # Adiciona coluna de Mês/Ano
    df_gastos['mes_ano'] = df_gastos['data'].dt.to_period('M').astype(str) # Converte para string para groupby

    # Cria tabela pivô: índice (Mês/Ano, Categoria), colunas (Forma de Pagamento), valores (Soma do Gasto)
    pivot_table = df_gastos.pivot_table(
        index=['mes_ano', 'categoria_nome'], 
        columns='forma_pagamento_nome', 
        values='valor', 
        aggfunc='sum'
    ).fillna(0) # Preenche NaNs com 0 para categorias sem gastos em certas formas de pag.

    if pivot_table.empty:
        return None
    
    # Prepara os dados para o gráfico de barras empilhadas
    # Cada grupo principal é uma Categoria dentro de um Mês/Ano
    # E as sub-barras são as formas de pagamento

    plt.figure(figsize=(15, 8))
    ax = pivot_table.plot(
        kind='bar', 
        stacked=True, 
        colormap='viridis', # Colormap para formas de pagamento
        ax=plt.gca() # Usa o Axes atual
    )

    plt.title('Gastos Mensais por Categoria e Forma de Pagamento', fontsize=16, fontweight='bold')
    plt.ylabel('Valor Total Gasto (R$)', fontsize=12)
    plt.xlabel('Mês/Ano - Categoria', fontsize=12)
    plt.xticks(rotation=90, ha='center', fontsize=10) # Rotação para os labels do eixo X (Mês-Categoria)
    plt.yticks(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Adicionar rótulos de valor no topo das pilhas (total por categoria)
    # E opcionalmente dentro de cada segmento (para cada forma de pagamento)
    # Este é um pouco mais complexo para barras empilhadas, então vamos adicionar o total da pilha
    for c in ax.containers:
        # Pega o rótulo do container (nome da forma de pagamento)
        label = c.get_label()
        # Excluir labels da legenda para evitar duplicidade com rótulos de dados se não for o total da pilha
        # ax.bar_label(c, fmt='R$%.2f', label_type='center', fontsize=7, color='white') # Rótulos dentro dos segmentos (opcional, pode sobrecarregar)
    
    # Adicionar rótulos de valor no topo de cada pilha (total da categoria no mês)
    # Isso requer calcular a soma de cada pilha
    totals = pivot_table.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(i, total + 10, f'R${total:.2f}', ha='center', va='bottom', fontsize=8, color='black') # Ajustar o +10 para padding

    formatter = mticker.FormatStrFormatter('R$%.2f')
    ax.yaxis.set_major_formatter(formatter)

    plt.legend(title='Forma de Pagamento', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    plt.close()
    return buf