# src/bot/commands/__init__.py

from .utils import start_command, help_command
from .balanco import balanco_command
from .category import adicionar_alias_command, add_category_command, category_command, definir_limite_command, total_category_command
from .gasto import category_spending_command, listar_gastos_command,gastos_mensal_combinado_command, total_por_pagamento_command

ALL_COMMANDS = [
    start_command, help_command,
    balanco_command, category_spending_command, total_por_pagamento_command, gastos_mensal_combinado_command,
    category_command, add_category_command, definir_limite_command, adicionar_alias_command,
     total_category_command,
    listar_gastos_command
]