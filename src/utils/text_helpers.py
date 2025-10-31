import re
from src.utils.latex_parser import latex_to_unicode

def split_message(text, max_length=4000):
    """Разбивка сообщений"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current = ""
    
    for para in text.split('\n\n'):
        if len(para) > max_length:
            # Слишком длинный блок бьем по предложениям
            for sentence in re.split(r'(?<=[.!?])\s+', para):
                if len(current) + len(sentence) + 2 <= max_length:
                    current += sentence + ' '
                else:
                    if current:
                        parts.append(current.strip())
                    current = sentence + ' '
        else:
            if len(current) + len(para) + 2 <= max_length:
                current += para + '\n\n'
            else:
                if current:
                    parts.append(current.strip())
                current = para + '\n\n'
    
    if current:
        parts.append(current.strip())
    
    return parts

def format_math_response(text):
    """Форматирование (только для TEXT)"""
    text = latex_to_unicode(text)
    text = re.sub(r'\n\n+', '\n\n', text)
    text = re.sub(r'---+', '─' * 30, text)
    return text