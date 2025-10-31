import os
import re
import time
import tempfile
import traceback
from PIL import Image
import config
from src.utils.latex_parser import extract_latex_blocks, latex_to_unicode
from src.services.codecogs_client import render_latex_via_codecogs

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.fonts import addMapping

    FONT_NAME = 'CustomFont'
    FONT_BOLD = 'CustomFontBold'
    
    try:
        arial_path = os.path.join(config.ASSETS_DIR, 'arial.ttf')
        arial_bold_path = os.path.join(config.ASSETS_DIR, 'arialbd.ttf')
        pdfmetrics.registerFont(TTFont(FONT_NAME, arial_path))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, arial_bold_path))
        print("✅ Шрифты Arial для PDF зарегистрированы.")
    except:
        try:
            dejavu_path = os.path.join(config.ASSETS_DIR, 'DejaVuSans.ttf')
            dejavu_bold_path = os.path.join(config.ASSETS_DIR, 'DejaVuSans-Bold.ttf')
            pdfmetrics.registerFont(TTFont(FONT_NAME, dejavu_path))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, dejavu_bold_path))
            print("✅ Шрифты DejaVu для PDF зарегистрированы.")
        except:
            FONT_NAME = 'Helvetica'
            FONT_BOLD = 'Helvetica-Bold'
            print("⚠️ Кастомные шрифты не найдены, используется Helvetica")
    
    if FONT_NAME != 'Helvetica':
        addMapping(FONT_NAME, 0, 0, FONT_NAME)
        addMapping(FONT_NAME, 1, 0, FONT_BOLD)
        addMapping(FONT_NAME, 0, 1, FONT_NAME)
        addMapping(FONT_NAME, 1, 1, FONT_BOLD)
            
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ reportlab не установлен. Функционал PDF будет недоступен.")


def create_pdf_with_formulas(text, output_path):
    """PDF с формулами"""
    if not REPORTLAB_AVAILABLE:
        print("❌ Попытка создать PDF без reportlab")
        return False
    
    temp_images = []
    
    try:
        doc = SimpleDocTemplate(
            output_path, 
            pagesize=A4,
            leftMargin=2*cm, 
            rightMargin=2*cm,
            topMargin=2*cm, 
            bottomMargin=2*cm
        )
        
        styles = getSampleStyleSheet()
        
        normal_style = ParagraphStyle(
            'CustomNormal', 
            parent=styles['Normal'],
            fontName=FONT_NAME,
            fontSize=11, 
            leading=16, 
            spaceAfter=10
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading', 
            parent=styles['Heading2'],
            fontName=FONT_BOLD,
            fontSize=14, 
            spaceAfter=12
        )
        
        story = []
        story.append(Paragraph("<b>Решение математических задач</b>", heading_style))
        story.append(Spacer(1, 0.5*cm))
        
        latex_blocks = extract_latex_blocks(text)
        rendered_formulas = {}
        
        # Рендерим все формулы и сохраняем во временные файлы
        for block in latex_blocks:
            img = render_latex_via_codecogs(block['latex'], dpi=200)
            if img:
                # Создаём временный файл
                tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                tmp_path = tmp.name
                tmp.close()
                
                # Сохраняем изображение
                img.save(tmp_path, 'PNG')
                img.close()
                
                temp_images.append(tmp_path)
                rendered_formulas[block['start']] = tmp_path
        
        # Строим документ
        if rendered_formulas:
            current_pos = 0
            
            for block in sorted(latex_blocks, key=lambda x: x['start']):
                # Текст до формулы
                before = text[current_pos:block['start']]
                if before.strip():
                    before = latex_to_unicode(before) 
                    before = before.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    
                    for para in before.split('\n\n'):
                        if para.strip():
                            para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', para.strip().replace('\n', '<br/>'))
                            story.append(Paragraph(para_html, normal_style))
                
                # Формула
                if block['start'] in rendered_formulas:
                    img_path = rendered_formulas[block['start']]
                    
                    # Открываем изображение ТОЛЬКО для получения размеров
                    with Image.open(img_path) as img_temp:
                        img_width_pt = img_temp.width * 0.75
                        img_height_pt = img_temp.height * 0.75
                    
                    # под A4
                    max_width = 16*cm
                    if img_width_pt > max_width:
                        ratio = max_width / img_width_pt
                        img_width_pt *= ratio
                        img_height_pt *= ratio
                    
                    # ReportLab сам откроет файл и закроет после build
                    story.append(RLImage(img_path, width=img_width_pt, height=img_height_pt))
                    story.append(Spacer(1, 0.3*cm))
                
                current_pos = block['end']
            
            # Остаток текста
            remaining = text[current_pos:]
            if remaining.strip():
                remaining = latex_to_unicode(remaining)
                remaining = remaining.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                for para in remaining.split('\n\n'):
                    if para.strip():
                        para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', para.strip().replace('\n', '<br/>'))
                        story.append(Paragraph(para_html, normal_style))
        else:
            # Если нет формул, просто текст
            text_clean = latex_to_unicode(text)
            text_clean = text_clean.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            for para in text_clean.split('\n\n'):
                if para.strip():
                    para_html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', para.strip().replace('\n', '<br/>'))
                    story.append(Paragraph(para_html, normal_style))
        
        # Генерируем PDF
        doc.build(story)
        
        # Ждём, пока ReportLab освободит файлы
        time.sleep(0.5)
        
        # Удаляем временные файлы
        cleanup_temp_files(temp_images)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка PDF: {e}")
        traceback.print_exc()
        
        # Пытаемся удалить временные файлы даже при ошибке
        cleanup_temp_files(temp_images)
        
        return False


def cleanup_temp_files(file_paths, max_retries=3):
    """
    Удаление временных файлов с повторными попытками.
    """
    for tmp_path in file_paths:
        if not os.path.exists(tmp_path):
            continue
            
        for attempt in range(max_retries):
            try:
                os.unlink(tmp_path)
                break  # Успешно удалено
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.2 * (attempt + 1))  # Увеличиваем задержку
                else:
                    print(f"⚠️ Не удалось удалить {os.path.basename(tmp_path)} после {max_retries} попыток")
            except Exception as e:
                print(f"⚠️ Ошибка удаления {os.path.basename(tmp_path)}: {e}")
                break