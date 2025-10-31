# src/utils/latex_parser.py
import re

def extract_latex_blocks(text):
    """Извлечение LaTeX блоков для рендеринга"""
    blocks = []
    
    # 1. Находим все DISPLAY блоки
    patterns_display = [
        (r'\\\[(.*?)\\\]', 'display'), # \[ ... \]
        (r'\$\$(.*?)\$\$', 'display'), # $$...$$
    ]
    
    for pattern, mode in patterns_display:
        for match in re.finditer(pattern, text, re.DOTALL):
            latex = match.group(1).strip()
            latex = re.sub(r'\s*\n\s*', ' ', latex) # Очистка от \n
            
            blocks.append({
                'latex': latex,
                'mode': mode,
                'start': match.start(),
                'end': match.end(),
                'full': match.group(0)
            })
    
    # 2. Находим ВСЕ INLINE блоки
    patterns_inline = [
        (r'\\\((.*?)\\\)', 'inline'),
        (r'\$([^\$]+)\$', 'inline'),
    ]
    
    for pattern, mode in patterns_inline:
        for match in re.finditer(pattern, text, re.DOTALL):
            latex = match.group(1).strip()
            
            latex = re.sub(r'\s*\n\s*', ' ', latex) # Очистка от \n
            blocks.append({
                'latex': latex,
                'mode': mode,
                'start': match.start(),
                'end': match.end(),
                'full': match.group(0)
            })

    # 3. Сортируем все найденные блоки по их начальной позиции
    sorted_blocks = sorted(blocks, key=lambda x: x['start'])
    
    # 4. Фильтруем наложения
    if not sorted_blocks:
        return []
        
    final_blocks = []
    last_end = -1
    
    for block in sorted_blocks:
        if block['start'] >= last_end:
            final_blocks.append(block)
            last_end = block['end']
    
    return final_blocks


def latex_to_unicode(text):
    """LaTeX → Unicode (для ТЕКСТА, не PDF)"""
    
    text = re.sub(r'\\\[|\\\]|\$\$', '', text) # Display
    text = re.sub(r'\\\((.*?)\\\)', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\$([^\$]+)\$', r'\1', text, flags=re.DOTALL) # $...$
    
    text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
    
    superscripts = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
                    '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', 'n': 'ⁿ', 'x': 'ˣ',
                    'm': 'ᵐ', 'k': 'ᵏ', '+': '⁺', '-': '⁻', 'i': 'ⁱ'}
    
    subscripts = {'0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
                  '6': '₆', '7': '₇', '8': '₈', '9': '₉', 'n': 'ₙ', 'm': 'ₘ'}
    
    def replace_power(m):
        base, exp = m.groups()
        return base + ''.join(superscripts.get(c, c) for c in exp)
    
    def replace_sub(m):
        base, sub = m.groups()
        return base + ''.join(subscripts.get(c, c) for c in sub)
    
    text = re.sub(r'(\w+)\^(\w+)', replace_power, text)
    text = re.sub(r'(\w+)\^\{([^}]+)\}', replace_power, text)
    text = re.sub(r'(\w+)_(\w+)', replace_sub, text)
    text = re.sub(r'(\w+)_\{([^}]+)\}', replace_sub, text)
    
    replacements = {
        r'\times': '×', r'\cdot': '·', r'\le': '≤', r'\ge': '≥',
        r'\ne': '≠', r'\approx': '≈', r'\sum': 'Σ', r'\prod': 'Π',
        r'\infty': '∞', r'\Rightarrow': '⇒', r'\rightarrow': '→',
        r'\quad': '  ',
    }
    
    for latex, uni in replacements.items():
        text = text.replace(latex, uni)
    
    return text