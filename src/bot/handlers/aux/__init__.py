from .send_confirmation_message import send_confirmation_message
from .register_expense import register_expense
from .register_income import register_income

ALL_COMANDS = {send_confirmation_message, register_income, register_expense}
