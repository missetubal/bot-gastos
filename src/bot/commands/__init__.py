# src/bot/commands/__init__.py

from .utils import start_command, help_command
from .balanco import balanco_command
from .category import adicionar_alias_command, adicionar_categoria_command, category_command, definir_limite_command, total_categoria_command
from .gasto import gastos_por_categoria_command, listar_gastos_command,gastos_mensal_combinado_command, total_por_pagamento_command

ALL_COMMANDS = [
    start_command, help_command,
    balanco_command, gastos_por_categoria_command, total_por_pagamento_command, gastos_mensal_combinado_command,
    category_command, adicionar_categoria_command, definir_limite_command, adicionar_alias_command,
     total_categoria_command,
    listar_gastos_command
]