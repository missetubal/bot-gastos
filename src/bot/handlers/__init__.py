from .handle_category_clarification import handle_category_clarification
from .handle_confirmation import handle_confirmation
from .handle_correction import handle_correction
from .handle_initial_message import handle_initial_message
from .handle_new_category_name import handle_new_category_name
from .handle_payment_method import handle_payment_method

# --- Estados da Conversa ---
HANDLE_INITIAL_MESSAGE = 0
ASKING_CATEGORY_CLARIFICATION = 1
ASKING_NEW_CATEGORY_NAME = 2
ASKING_PAYMENT_METHOD = 3
ASKING_CONFIRMATION = 4
ASKING_CORRECTION = 5


ALL_HANDLERS = {
    handle_new_category_name,
    handle_confirmation,
    handle_category_clarification,
    handle_correction,
    handle_initial_message,
    handle_payment_method,
}
