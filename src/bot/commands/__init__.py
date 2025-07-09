# src/bot/commands/__init__.py

from .utils import start_command, help_command
from .balanco import balanco_command
from .category import (
    add_alias_command,
    add_category_command,
    category_command,
    set_limit_command,
    total_category_command,
)
from .gasto import (
    category_spending_command,
    list_expenses_command,
    monthly_category_payment_command,
    payment_method_spending_command,
)

ALL_COMMANDS = [
    start_command,
    help_command,
    balanco_command,
    category_spending_command,
    payment_method_spending_command,
    monthly_category_payment_command,
    category_command,
    add_category_command,
    set_limit_command,
    add_alias_command,
    total_category_command,
    list_expenses_command,
]
