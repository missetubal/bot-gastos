# src/utils/text_utils.py

def to_camel_case(s: str) -> str:
    """Converte uma string para CamelCase.
    Ex: "minha nova categoria" -> "MinhaNovaCategoria"
    Ex: "alimentacao" -> "Alimentacao"
    """
    if not s:
        return ""
    
    # Divide a string por espaços, hifens, underscores, etc.
    words = s.replace('-', ' ').replace('_', ' ').split()
    
    if not words:
        return ""

    # Capitaliza a primeira letra de cada palavra e junta
    camel_cased_words = [word.capitalize() for word in words]
    
    return "".join(camel_cased_words)