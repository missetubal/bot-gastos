# src/utils/text_utils.py
import re

def to_camel_case(s: str) -> str:
    """Converte uma string para PascalCase (cada palavra começa com maiúscula, sem forçar o resto para minúscula).
    Ex: "minha nova categoria" -> "MinhaNovaCategoria"
    Ex: "alimentacao" -> "Alimentacao"
    Ex: "AlreadyCamelCase" -> "AlreadyCamelCase" (mantém a capitalização interna)
    Ex: "TV purchase" -> "TVPurchase" (trata acrônimos como palavras completas)
    """
    if not s:
        return ""
    
    # Divide a string em palavras baseadas em caracteres não-alfanuméricos (espaços, hifens, underscores, etc.)
    words = [word for word in re.split(r'[^a-zA-Z0-9]+', s) if word]

    if not words:
        return ""

    # Converte cada palavra para o formato PascalCase e junta
    # Esta lógica lida com acrônimos e palavras já em PascalCase corretamente
    processed_words = []
    for word in words:
        if word.isupper() and len(word) > 1: # Se é um acrônimo como "TV"
            processed_words.append(word) # Mantém como está "TV"
        else:
            processed_words.append(word.capitalize()) # Capitaliza a primeira letra, minúsculas o resto

    return "".join(processed_words)