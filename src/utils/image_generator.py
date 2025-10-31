import os
import traceback
from PIL import Image, ImageDraw, ImageFont
import config
from src.utils.latex_parser import extract_latex_blocks
from src.services.codecogs_client import render_latex_via_codecogs


def convert_formula_to_rgba(img):
    """
    Конвертирует изображение формулы в RGBA для безопасной вставки.
    Решает проблему с палитрой и прозрачностью от CodeCogs.
    """
    try:
        # Если изображение в режиме Palette с прозрачностью
        if img.mode == 'P':
            img = img.convert('RGBA')
        # Если изображение в режиме Grayscale + Alpha
        elif img.mode == 'LA':
            img = img.convert('RGBA')
        # Если изображение уже в RGB без альфа-канала
        elif img.mode == 'RGB':
            img = img.convert('RGBA')
        # Любой другой режим
        elif img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        return img
    except Exception as e:
        print(f"⚠️ Ошибка конвертации формулы: {e}")
        return img


def paste_formula_with_background(base_img, formula_img, position, bg_color='white'):
    """
    Вставляет формулу на фон с учётом прозрачности.
    
    Args:
        base_img: Основное изображение (PIL.Image)
        formula_img: Изображение формулы (PIL.Image)
        position: Кортеж (x, y) для позиции
        bg_color: Цвет фона для непрозрачных пикселей

        Конвертируем формулу в RGBA
        Создаём временный слой с белым фоном
        Накладываем формулу на белый фон
        Конвертируем обратно в RGB для вставки
        Вставляем на основное изображение
    """
    try:
        formula_rgba = convert_formula_to_rgba(formula_img)

        temp = Image.new('RGBA', formula_rgba.size, bg_color)
        
        temp.paste(formula_rgba, (0, 0), formula_rgba)
        
        temp_rgb = temp.convert('RGB')
        
        base_img.paste(temp_rgb, position)
        
    except Exception as e:
        print(f"⚠️ Ошибка вставки формулы: {e}")
        # Fallback: вставляем как есть
        try:
            base_img.paste(formula_img, position)
        except:
            print(f"❌ Не удалось вставить формулу даже с fallback")


def create_full_answer_image(text, output_path):
    """Создание большого изображения с полным ответом и формулами"""
    try:
        # Параметры изображения
        width = 1200
        padding = 40
        line_height = 35
        font_size = 20
        
        font_path = os.path.join(config.ASSETS_DIR, 'arial.ttf')
        font_bold_path = os.path.join(config.ASSETS_DIR, 'arialbd.ttf')

        try:
            font = ImageFont.truetype(font_path, font_size)
            font_bold = ImageFont.truetype(font_bold_path, font_size + 2)
        except IOError:
            print("⚠️ Шрифты Arial не найдены, используется шрифт по умолчанию.")
            font = ImageFont.load_default()
            font_bold = font
        
        latex_blocks = extract_latex_blocks(text)
        
        # Подготовка рендерим все формулы
        rendered_formulas = {}
        for block in latex_blocks:
            img = render_latex_via_codecogs(block['latex'], dpi=200)
            if img:
                # Сразу конвертируем в RGBA
                img_converted = convert_formula_to_rgba(img)
                rendered_formulas[block['start']] = img_converted
                # Закрываем оригинальное изображение
                if img != img_converted:
                    img.close()
        
        lines = []
        current_pos = 0
        
        # Разбиваем текст на строки и формулы
        for block in latex_blocks:
            # Текст до формулы
            before = text[current_pos:block['start']]
            for line in before.split('\n'):
                if line.strip():
                    lines.append(('text', line.strip()))
            
            # Формула
            if block['start'] in rendered_formulas:
                lines.append(('formula', rendered_formulas[block['start']]))
            
            current_pos = block['end']
        
        # Остаток текста
        remaining = text[current_pos:]
        for line in remaining.split('\n'):
            if line.strip():
                lines.append(('text', line.strip()))
        
        # Если нет блоков просто весь текст
        if not lines:
            lines = [('text', line.strip()) for line in text.split('\n') if line.strip()]
        
        # Вычисляем высоту
        height = padding * 2
        for item_type, content in lines:
            if item_type == 'text':
                # Перенос длинных строк
                max_width = width - padding * 2
                words = content.split()
                current_line = ""
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    bbox = font.getbbox(test_line)
                    if bbox[2] - bbox[0] <= max_width:
                        current_line = test_line
                    else:
                        height += line_height
                        current_line = word
                height += line_height
            else:
                height += content.height + 20
        
        height = max(height, 400)
        
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        y = padding
        
        # Рендерим содержимое
        for item_type, content in lines:
            if item_type == 'text':
                current_font = font_bold if content.startswith('**') or content.startswith('#') else font
                text_content = content.strip('*#').strip()
                
                max_width = width - padding * 2
                words = text_content.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    bbox = current_font.getbbox(test_line)
                    
                    if bbox[2] - bbox[0] <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            draw.text((padding, y), current_line, fill='black', font=current_font)
                            y += line_height
                        current_line = word
                
                if current_line:
                    draw.text((padding, y), current_line, fill='black', font=current_font)
                    y += line_height
                    
            else:  # formula
                formula_img = content
                x_offset = (width - formula_img.width) // 2
                
                # Севй вставка с фоном
                paste_formula_with_background(img, formula_img, (x_offset, y), bg_color='white')
                
                y += formula_img.height + 20
        
        # Сохраняем результат
        img.save(output_path, 'PNG', quality=95)
        
        # Закрываем все изображения формул
        for formula_img in rendered_formulas.values():
            try:
                formula_img.close()
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания изображения: {e}")
        traceback.print_exc()
        return False


def create_formula_preview(latex_text, output_path, size=(800, 200)):
    """
    Создаёт превью одной формулы (для отладки).
    
    Args:
        latex_text: LaTeX формула
        output_path: Путь для сохранения
        size: Размер изображения (ширина, высота)
    """
    try:
        img = render_latex_via_codecogs(latex_text, dpi=300)
        if not img:
            print("❌ Не удалось отрендерить формулу")
            return False
        
        # Конвертируем
        img_rgba = convert_formula_to_rgba(img)
        
        # Создаём фон
        bg = Image.new('RGB', size, 'white')
        
        # Центрируем формулу
        x = (size[0] - img_rgba.width) // 2
        y = (size[1] - img_rgba.height) // 2
        
        paste_formula_with_background(bg, img_rgba, (x, y))
        
        bg.save(output_path, 'PNG', quality=95)
        
        img.close()
        img_rgba.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка создания превью: {e}")
        traceback.print_exc()
        return False


# Тестовая функция
if __name__ == "__main__":
    test_text = r"""
    Решение задачи:
    
    Формула: $\frac{5!}{2! \cdot 2! \cdot 1!} = \frac{120}{4} = 30$
    
    Ответ: 30 способов.
    """
    
    print("🧪 Тестируем генерацию изображения...")
    success = create_full_answer_image(test_text, "test_output.png")
    
    if success:
        print("✅ Изображение создано: test_output.png")
    else:
        print("❌ Не удалось создать изображение")