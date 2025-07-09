# src/core/models.py
from typing import Optional
from datetime import date

# Estes são apenas modelos conceituais para organização.
# No código, você geralmente trabalhará com dicionários Python vindos do Supabase.


class Gasto:
    def __init__(self, id: str, valor: float, category_id: str, data: date):
        self.id = id
        self.valor = valor
        self.category_id = category_id
        self.data = data


class Ganho:
    def __init__(self, id: str, valor: float, descricao: str, data: date):
        self.id = id
        self.valor = valor
        self.descricao = descricao
        self.data = data


class Categoria:
    def __init__(self, id: str, nome: str, monthly_limit: Optional[float] = 0.0):
        self.id = id
        self.nome = nome
        self.monthly_limit = monthly_limit


# Estes modelos servem para documentar a estrutura esperada dos dados.
# No código real de db.py, você pode continuar usando dicionários,
# mas ter essa definição ajuda na clareza.
