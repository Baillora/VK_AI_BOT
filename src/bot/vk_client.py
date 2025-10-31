import vk_api
from vk_api.bot_longpoll import VkBotLongPoll
from threading import Thread, Event
import requests
import os
import tempfile
import time

import config
from src.utils.text_helpers import split_message, format_math_response
from src.utils.pdf_generator import create_pdf_with_formulas, REPORTLAB_AVAILABLE
from src.utils.image_generator import create_full_answer_image

# --- Инициализация VK ---
# объекты будут использоваться всеми функциями тут
try:
    vk_session = vk_api.VkApi(token=config.VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, config.GROUP_ID)
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось подключиться к VK API. {e}")
    exit()

# КЛАСС: КОНТРОЛЛЕР СТАТУСА НАБОРА ТЕКСТА (TypingStatusController)
class TypingStatusController:
    """Управляет цикличным обновлением статуса 'Бот печатает...'"""
    def __init__(self, peer_id: int):
        self.peer_id = peer_id
        self._stop_event = Event()
        self._thread = None
        
    def _run_typing_loop(self):
        """Функция, которая будет выполняться в отдельном потоке"""
        
        # Обновляем статус каждые 7 сек (10 сек таймаут ВК)
        while not self._stop_event.is_set():
            try:
                # ВАЖНО: используем глобальный объект vk
                vk.messages.setActivity(
                    peer_id=self.peer_id,
                    type='typing' 
                )
                # Ждем 7 секунд. Если за это время _stop_event сработает, цикл прервется.
                self._stop_event.wait(timeout=7) 
                
            except Exception as e:
                # Если сбой при обновлении статуса, выходим из цикла
                print(f"⚠️ Ошибка обновления статуса набора текста для {self.peer_id}: {e}")
                break

    def start(self):
        """Запускает поток обновления статуса"""
        if self._thread is None or not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = Thread(target=self._run_typing_loop)
            self._thread.start()
            print(f"▶️ Запущен контроллер набора текста для {self.peer_id}")

    def stop(self):
        """Останавливает поток обновления статуса"""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=8) # Ждем немного, чтобы поток завершился
            print(f"⏹️ Остановлен контроллер набора текста для {self.peer_id}")

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ VK

def get_longpoll_listener():
    """Возвращает longpoll listener"""
    return longpoll

def upload_photo_to_vk(photo_path, user_id):
    """Загрузка фото"""
    try:
        upload_url = vk.photos.getMessagesUploadServer(peer_id=user_id)['upload_url']
        
        with open(photo_path, 'rb') as f:
            response = requests.post(upload_url, files={'photo': f}).json()
        
        photo = vk.photos.saveMessagesPhoto(
            photo=response['photo'],
            server=response['server'],
            hash=response['hash']
        )[0]
        
        return f"photo{photo['owner_id']}_{photo['id']}"
    except Exception as e:
        print(f"❌ Ошибка загрузки фото: {e}")
        return None

def upload_doc_to_vk(doc_path, user_id, title="document.pdf"):
    """Загрузка документа"""
    try:
        print(f"📤 Загрузка: {title}")
        
        upload_data = vk.docs.getMessagesUploadServer(type='doc', peer_id=user_id)
        if not upload_data or 'upload_url' not in upload_data:
            return None
        
        upload_url = upload_data['upload_url']
        
        with open(doc_path, 'rb') as f:
            response = requests.post(upload_url, files={'file': f})
        
        if response.status_code != 200:
            print(f"❌ Статус: {response.status_code}")
            return None
        
        upload_result = response.json()
        if 'file' not in upload_result:
            return None
        
        save_result = vk.docs.save(file=upload_result['file'], title=title)
        
        if isinstance(save_result, list):
            doc = save_result[0] if save_result else None
        elif isinstance(save_result, dict):
            doc = save_result.get('doc', save_result)
        else:
            return None
        
        if doc and 'owner_id' in doc and 'id' in doc:
            return f"doc{doc['owner_id']}_{doc['id']}"
        
        return None
    except Exception as e:
        print(f"❌ Ошибка загрузки doc: {e}")
        return None

def send_message(user_id, text, attachment=None, mode="math"):
    """
    Отправка (с форматированием LaTeX -> Unicode).
    mode влияет на то, будет ли текст очищаться от LaTeX.
    """
    try:
        # В режиме 'math' чистим LaTeX, в 'code' и 'raw' - нет
        if mode == "math":
            formatted = format_math_response(text)
        else:
            formatted = text
            
        parts = split_message(formatted)
        
        for i, part in enumerate(parts):
            if len(parts) > 1:
                part = f"[Часть {i+1}/{len(parts)}]\n\n" + part
            
            # Вложение отправляем только с первой частью
            att = attachment if i == 0 else None
            vk.messages.send(user_id=user_id, message=part, attachment=att, random_id=0)
            
    except Exception as e:
        print(f"⚠️ Ошибка отправки: {e}")
        try:
            # Попытка №2: отправить ошибку без форматирования
            vk.messages.send(user_id=user_id, message=f"Ошибка отправки. {text[:1000]}", random_id=0)
        except:
            pass # Критическая 

def send_as_format(user_id, text, format_type="text", mode="math"):
    """
    Отправка в формате (text, image, pdf).
    'mode' (math, code, raw) передается в send_message.
    """
    
    # /code и /raw всегда в текстовом режиме
    if mode == "code" or mode == "raw":
        send_message(user_id, text, mode=mode)
        return
    
    # /math (по умолчанию) использует format_type
    if format_type == "image":
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                tmp_file = tmp.name
            
            print("🎨 Создание изображения с полным ответом...")
            
            if create_full_answer_image(text, tmp_file):
                attachment = upload_photo_to_vk(tmp_file, user_id)
                if attachment:
                    # Уведомление отправляем как 'raw', чтобы не парсить LaTeX
                    send_message(user_id, "📐 Полное решение с формулами:", attachment, mode="raw")
                    # А сам текст (для копирования) - как 'math' (он очистит LaTeX)
                    send_message(user_id, text, mode="math")
                else:
                    send_message(user_id, text, mode="math")
            else:
                send_message(user_id, text + "\n\n⚠️ Не удалось создать изображение", mode="math")
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    time.sleep(0.5)
                    os.unlink(tmp_file)
                except:
                    pass
    
    elif format_type == "pdf":
        if not REPORTLAB_AVAILABLE:
            send_message(user_id, text + "\n\n⚠️ Модуль PDF (reportlab) не установлен на сервере.", mode="math")
            return
        
        tmp_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp_file = tmp.name
            
            print("📄 Создание PDF...")
            
            if create_pdf_with_formulas(text, tmp_file):
                attachment = upload_doc_to_vk(tmp_file, user_id, "Решение.pdf")
                if attachment:
                    send_message(user_id, "📄 PDF с решением", attachment, mode="raw")
                    send_message(user_id, text, mode="math")
                else:
                    send_message(user_id, "⚠️ Не удалось загрузить PDF\n\n" + text, mode="math")
            else:
                send_message(user_id, text + "\n\n⚠️ Не удалось создать PDF", mode="math")
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    time.sleep(0.5)
                    os.unlink(tmp_file)
                except:
                    pass
    
    else:
        # Просто текст
        send_message(user_id, text, mode="math")