import requests
import io
from PIL import Image

def render_latex_via_codecogs(latex_text, dpi=300):
    """Рендеринг через CodeCogs"""
    try:
        # \frac -> \displaystyle\frac для работы в CodeCogs
        if r'\frac' in latex_text and r'\displaystyle' not in latex_text:
             latex_text = r'\displaystyle ' + latex_text
             
        latex_clean = latex_text.strip().strip('$').strip()
        latex_encoded = requests.utils.quote(latex_clean)
        
        url = f"https://latex.codecogs.com/png.latex?\\dpi{{{dpi}}}{latex_encoded}"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            print(f"❌ CodeCogs: {response.status_code} для {latex_clean}")
            return None
    except Exception as e:
        print(f"❌ CodeCogs Ошибка: {e}")
        return None