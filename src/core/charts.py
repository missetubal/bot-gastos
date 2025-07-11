# src/core/charts.py
import datetime
import io
from typing import Union, Dict, Any, List
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from supabase import Client

# Configurações globais para os gráficos (cores, fontes, etc.)
plt.style.use("seaborn-v0_8-darkgrid")
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10
plt.rcParams["axes.labelsize"] = 12
plt.rcParams["axes.titlesize"] = 14
plt.rcParams["xtick.labelsize"] = 10
plt.rcParams["ytick.labelsize"] = 10
plt.rcParams["legend.fontsize"] = 10

# Cores personalizadas para os gráficos
COLORS = {
    "Ganho": "#28a745",
    "Gasto": "#dc3545",
    "Balanço": "#007bff",
    "Fatias_Variadas": [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ],
}


# --- Função de Ajuda para Filtrar Gastos ---
def filter_gastos_data(
    gastos_data: List[Dict[str, Any]],
    category_id: Union[str, None] = None,
    forma_pagamento_id: Union[str, None] = None,
    data_inicio: Union[str, None] = None,
    data_fim: Union[str, None] = None,
) -> List[Dict[str, Any]]:
    df = pd.DataFrame(gastos_data)
    if df.empty:
        return []

    df["date"] = pd.to_datetime(df["date"])

    if category_id:
        df = df[df["category_id"] == category_id]

    if forma_pagamento_id:
        df = df[df["forma_pagamento_id"] == forma_pagamento_id]

    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df = df[df["date"] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        # Se a data fim for o último dia do mês, garantimos que inclui o dia inteiro
        if (
            end_date.day == (end_date + pd.Timedelta(days=1)).day - 1
        ):  # Verifica se é o último dia do mês
            end_date = end_date.replace(hour=23, minute=59, second=59)
        df = df[df["date"] <= end_date]

    return df.to_dict(orient="records")


# --- Função Auxiliar para Títulos de Gráfico ---
def _get_period_title(data_inicio: Union[str, None], data_fim: Union[str, None]) -> str:
    """Retorna uma string para o período do gráfico."""
    if data_inicio and data_fim:
        start_date = datetime.datetime.strptime(data_inicio, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(data_fim, "%Y-%m-%d")

        # Se for um único mês
        if (
            start_date.day == 1
            and end_date.day == (end_date + datetime.timedelta(days=1)).day - 1
            and start_date.month == end_date.month
            and start_date.year == end_date.year
        ):
            return f" ({start_date.strftime('%B/%Y').capitalize()})"
        # Se for um período mais amplo
        return (
            f" (de {start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})"
        )
    return ""


# --- ATUALIZADO: generate_balance_chart ---
def generate_balance_chart(
    supabase_client: Client,
    data_inicio: Union[str, None] = None,
    data_fim: Union[str, None] = None,
) -> Union[io.BytesIO, None]:
    """Gera um gráfico de balanço mensal de ganhos vs. gastos, com filtros de data."""
    try:
        gastos_data_raw = (
            supabase_client.table("expenses").select("value,date").execute().data
        )
        ganhos_data_raw = (
            supabase_client.table("ganhos").select("valor,data").execute().data
        )
    except Exception as e:
        print(f"Erro ao obter dados para gráfico de balanço: {e}")
        return None

    # Aplica filtro de data aos gastos e ganhos
    gastos_data = filter_gastos_data(
        gastos_data_raw, data_inicio=data_inicio, data_fim=data_fim
    )
    ganhos_data = filter_gastos_data(
        ganhos_data_raw, data_inicio=data_inicio, data_fim=data_fim
    )

    if not gastos_data and not ganhos_data:
        return None

    df_gastos = pd.DataFrame(gastos_data)
    if not df_gastos.empty:
        df_gastos["date"] = pd.to_datetime(df_gastos["date"])
        df_gastos["tipo"] = "Gasto"
    else:
        df_gastos = pd.DataFrame(columns=["value", "date", "tipo"])

    df_ganhos = pd.DataFrame(ganhos_data)
    if not df_ganhos.empty:
        df_ganhos["date"] = pd.to_datetime(df_ganhos["date"])
        df_ganhos["tipo"] = "Ganho"
    else:
        df_ganhos = pd.DataFrame(columns=["value", "date", "tipo"])

    df_all = pd.concat([df_gastos, df_ganhos], ignore_index=True)
    if df_all.empty:
        return None

    df_all["mes_ano"] = df_all["date"].dt.to_period("M")

    monthly_summary = (
        df_all.groupby(["mes_ano", "tipo"])["value"].sum().unstack(fill_value=0)
    )
    monthly_summary["Balanço"] = monthly_summary.get("Ganho", 0) - monthly_summary.get(
        "Gasto", 0
    )
    monthly_summary = monthly_summary.sort_index()

    plt.figure(figsize=(12, 7))
    ax = monthly_summary[["Ganho", "Gasto", "Balanço"]].plot(
        kind="bar",
        figsize=(12, 7),
        color=[COLORS["Ganho"], COLORS["Gasto"], COLORS["Balanço"]],
    )

    plt.title("Balanço Mensal: Ganhos vs. Gastos", fontsize=16, fontweight="bold")
    plt.ylabel("Valor (R$)", fontsize=12)
    plt.xlabel("Mês/Ano", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(title="Tipo de Transação", fontsize=10, title_fontsize=11)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    for container in ax.containers:
        ax.bar_label(container, fmt="R$%.2f", fontsize=8, padding=3)

    formatter = mticker.FormatStrFormatter("R$%.2f")
    ax.yaxis.set_major_formatter(formatter)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close()
    return buf


# --- ATUALIZADO: generate_category_spending_chart ---
def generate_category_spending_chart(
    supabase_client: Client,
    forma_pagamento_id: Union[str, None] = None,
    data_inicio: Union[str, None] = None,
    data_fim: Union[str, None] = None,
) -> Union[io.BytesIO, None]:
    """Gera um gráfico de gastos por categoria e compara com os limites, com filtros."""
    try:
        gastos_data_raw = (
            supabase_client.table("expenses")
            .select(
                "value,category_id,date,payment_methods(name),categories(name,monthly_limit),payment_method_id"
            )
            .execute()
            .data
        )
        categorias_data_full = (
            supabase_client.table("categories")
            .select("id,name,monthly_limit")
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico de categoria: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        if (
            "categories" in gasto_copy
            and gasto_copy["categories"]
            and "name" in gasto_copy["categories"]
        ):
            gasto_copy["categoria_nome"] = gasto_copy["categories"]["name"]
            gasto_copy["limite_mensal_categoria"] = gasto_copy["categories"][
                "monthly_limit"
            ]
        else:
            gasto_copy["categoria_nome"] = "Desconhecida"
            gasto_copy["limite_mensal_categoria"] = None
        del gasto_copy["categories"]

        if (
            "payment_methods" in gasto_copy
            and gasto_copy["payment_methods"]
            and "name" in gasto_copy["payment_methods"]
        ):
            gasto_copy["forma_pagamento_nome"] = gasto_copy["payment_methods"]["name"]
        else:
            gasto_copy["forma_pagamento_nome"] = "Não Informado"
        del gasto_copy["payment_methods"]
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty:
        return None

    df_gastos["date"] = pd.to_datetime(df_gastos["date"])

    if forma_pagamento_id:
        df_gastos = df_gastos[df_gastos["forma_pagamento_id"] == forma_pagamento_id]

    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos["date"] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos["date"] <= end_date]

    if df_gastos.empty:
        return None

    gastos_por_categoria = (
        df_gastos.groupby("categoria_nome")["value"].sum().sort_values(ascending=False)
    )

    if gastos_por_categoria.empty:
        return None

    limites_por_categoria = {
        cat["name"]: cat["monthly_limit"] for cat in categorias_data_full
    }

    categorias_plot = gastos_por_categoria.index.tolist()
    valores_gastos = gastos_por_categoria.values.tolist()

    plt.figure(figsize=(12, 7))
    ax = plt.subplot(111)

    bars = ax.bar(
        categorias_plot,
        valores_gastos,
        color=COLORS["Fatias_Variadas"],
        label="Gasto Total",
    )

    payment_filter_title = ""
    if forma_pagamento_id:
        fp_info = (
            supabase_client.table("payment_methods")
            .select("name")
            .eq("id", forma_pagamento_id)
            .limit(1)
            .execute()
            .data
        )
        if fp_info:
            payment_filter_title = f" por {fp_info[0]['name']}"
    period_title = _get_period_title(data_inicio, data_fim)

    plt.title(
        f"Gastos por Categoria{payment_filter_title}{period_title} vs. Limite Mensal",
        fontsize=16,
        fontweight="bold",
    )
    plt.ylabel("Valor (R$)", fontsize=12)
    plt.xlabel("Categoria", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    ax.bar_label(bars, fmt="R$%.2f", fontsize=8, padding=3)

    for i, cat_nome in enumerate(categorias_plot):
        limite_atual = limites_por_categoria.get(cat_nome)
        if limite_atual is not None and limite_atual > 0:
            bar_x = bars[i].get_x()
            bar_width = bars[i].get_width()
            ax.hlines(
                limite_atual,
                bar_x,
                bar_x + bar_width,
                colors="darkgreen",
                linestyles="--",
                label="Limite Mensal" if i == 0 else "",
            )

            if valores_gastos[i] > limite_atual:
                ax.text(
                    bar_x + bar_width / 2,
                    max(valores_gastos[i], limite_atual) + 5,
                    "EXCEDIDO!",
                    ha="center",
                    va="bottom",
                    color="red",
                    fontsize=9,
                    weight="bold",
                )

    formatter = mticker.FormatStrFormatter("R$%.2f")
    ax.yaxis.set_major_formatter(formatter)

    handles, labels = ax.get_legend_handles_labels()
    unique_labels = dict(zip(labels, handles))
    ax.legend(unique_labels.values(), unique_labels.keys(), fontsize=10)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close()
    return buf


# --- ATUALIZADO: generate_payment_method_spending_chart ---
def generate_payment_method_spending_chart(
    supabase_client: Client,
    category_id: Union[str, None] = None,
    data_inicio: Union[str, None] = None,
    data_fim: Union[str, None] = None,
) -> Union[io.BytesIO, None]:
    """Gera um gráfico do total de gastos por forma de pagamento, com filtros."""
    try:
        gastos_data_raw = (
            supabase_client.table("expenses")
            .select("value,date,payment_methods(name),category_id")
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico de formas de pagamento: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        if (
            "payment_methods" in gasto_copy
            and gasto_copy["payment_methods"]
            and "name" in gasto_copy["payment_methods"]
        ):
            gasto_copy["forma_pagamento_nome"] = gasto_copy["payment_methods"]["name"]
        else:
            gasto_copy["forma_pagamento_nome"] = "Não Informado"
        del gasto_copy["payment_methods"]
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty:
        return None

    df_gastos["date"] = pd.to_datetime(df_gastos["date"])

    if category_id:
        df_gastos = df_gastos[df_gastos["category_id"] == category_id]

    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos["date"] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos["date"] <= end_date]

    if df_gastos.empty:
        return None

    gastos_por_forma = (
        df_gastos.groupby("forma_pagamento_nome")["value"]
        .sum()
        .sort_values(ascending=False)
    )

    if gastos_por_forma.empty:
        return None

    plt.figure(figsize=(10, 7))
    colors_for_pie = [
        COLORS["Fatias_Variadas"][i % len(COLORS["Fatias_Variadas"])]
        for i in range(len(gastos_por_forma))
    ]

    ax = gastos_por_forma.plot(
        kind="pie",
        autopct=lambda p: f"R${(p * sum(gastos_por_forma) / 100):.2f}",
        startangle=90,
        colors=colors_for_pie,  # <-- Use 'colors' em vez de 'cmap'
        pctdistance=0.85,
    )

    category_filter_title = ""
    if category_id:
        cat_info = (
            supabase_client.table("categories")
            .select("name")
            .eq("id", category_id)
            .limit(1)
            .execute()
            .data
        )
        if cat_info:
            category_filter_title = f" em {cat_info[0]['name']}"
    period_title = _get_period_title(data_inicio, data_fim)

    plt.title(
        f"Gastos por Forma de Pagamento{category_filter_title}{period_title}",
        fontsize=16,
        fontweight="bold",
    )
    plt.ylabel("")
    plt.tight_layout()
    plt.axis("equal")

    wedges = ax.pie(
        gastos_por_forma, autopct="", startangle=90, colors=colors_for_pie
    )
    labels = [f"{name}: R${value:.2f}" for name, value in gastos_por_forma.items()]
    ax.legend(
        wedges,
        labels,
        title="Forma de Pagamento",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
    )

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close()
    return buf


# --- Gerar Gráfico de Gastos Mensais por Categoria e Forma de Pagamento ---
def generate_monthly_category_payment_chart(
    supabase_client: Client,
    data_inicio: Union[str, None] = None,
    data_fim: Union[str, None] = None,
) -> Union[io.BytesIO, None]:
    """
    Gera um gráfico de barras empilhadas mostrando gastos por mês/categoria,
    com as formas de pagamento como sub-divisões.
    """
    try:
        gastos_data_raw = (
            supabase_client.table("expenses")
            .select("value,date,payment_methods(name),categories(name)")
            .execute()
            .data
        )
    except Exception as e:
        print(f"Erro ao obter gastos para gráfico mensal combinado: {e}")
        return None

    if not gastos_data_raw:
        return None

    adjusted_gastos_data = []
    for gasto in gastos_data_raw:
        gasto_copy = gasto.copy()
        if (
            "categories" in gasto_copy
            and gasto_copy["categories"]
            and "name" in gasto_copy["categories"]
        ):
            gasto_copy["categoria_nome"] = gasto_copy["categories"]["name"]
        else:
            gasto_copy["categoria_nome"] = "Desconhecida"
        del gasto_copy["categories"]

        if (
            "payment_methods" in gasto_copy
            and gasto_copy["payment_methods"]
            and "name" in gasto_copy["payment_methods"]
        ):
            gasto_copy["forma_pagamento_nome"] = gasto_copy["payment_methods"]["name"]
        else:
            gasto_copy["forma_pagamento_nome"] = "Não Informado"
        del gasto_copy["payment_methods"]
        adjusted_gastos_data.append(gasto_copy)

    df_gastos = pd.DataFrame(adjusted_gastos_data)
    if df_gastos.empty:
        return None

    df_gastos["date"] = pd.to_datetime(df_gastos["date"])

    # Aplica filtros de data
    if data_inicio:
        start_date = pd.to_datetime(data_inicio)
        df_gastos = df_gastos[df_gastos["date"] >= start_date]
    if data_fim:
        end_date = pd.to_datetime(data_fim)
        df_gastos = df_gastos[df_gastos["date"] <= end_date]

    if df_gastos.empty:
        return None

    df_gastos["mes_ano"] = df_gastos["date"].dt.to_period("M").astype(str)

    pivot_table = df_gastos.pivot_table(
        index=["mes_ano", "categoria_nome"],
        columns="forma_pagamento_nome",
        values="value",
        aggfunc="sum",
    ).fillna(0)

    if pivot_table.empty:
        return None

    plt.figure(figsize=(15, 8))

    ax = pivot_table.plot(
        kind="bar",
        stacked=True,
        colormap="viridis",  # Mantendo colormap aqui, geralmente funciona bem em barras
        ax=plt.gca(),
    )

    period_title = _get_period_title(data_inicio, data_fim)
    plt.title(
        f"Gastos Mensais por Categoria e Forma de Pagamento{period_title}",
        fontsize=16,
        fontweight="bold",
    )
    plt.ylabel("Valor Total Gasto (R$)", fontsize=12)
    plt.xlabel("Mês/Ano - Categoria", fontsize=12)
    plt.xticks(rotation=90, ha="center", fontsize=10)
    plt.yticks(fontsize=10)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    totals = pivot_table.sum(axis=1)
    for i, total in enumerate(totals):
        ax.text(
            i,
            total + 10,
            f"R${total:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="black",
        )

    formatter = mticker.FormatStrFormatter("R$%.2f")
    ax.yaxis.set_major_formatter(formatter)

    plt.legend(
        title="Forma de Pagamento",
        bbox_to_anchor=(1.05, 1),
        loc="upper left",
        fontsize=10,
    )
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=300)
    buf.seek(0)
    plt.close()
    return buf
