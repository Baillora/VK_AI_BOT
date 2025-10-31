import requests
import json
import traceback
import config


def log_response(data):
    """Лог ответа от API"""
    try:
        if isinstance(data, str):
            data = json.loads(data)
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        model = data.get("model", "unknown")
        tokens = data.get("usage", {})
        
        # При пустом больеш инфы
        if not content or content.strip() == "":
            print(f"\n{'='*60}")
            print(f"⚠️ ПУСТОЙ ОТВЕТ ОТ {model}")
            print(f"📊 Токены: {tokens.get('prompt_tokens', 0)} → {tokens.get('completion_tokens', 0)}")
            print(f"🔍 Полный ответ: {json.dumps(data, ensure_ascii=False, indent=2)}")
            print(f"{'='*60}\n")
        else:
            print(f"\n{'='*60}")
            print(f"🤖 {model}")
            print(f"📊 Токены: {tokens.get('prompt_tokens', 0)} → {tokens.get('completion_tokens', 0)}")
            print(f"📝 {content[:100]}...")
            print(f"{'='*60}\n")
    except Exception as e:
        print(f"⚠️ Ошибка логирования: {e}")


def validate_image_url(url):
    """
    Проверка доступности и корректности изображения.
    Возвращает (is_valid, error_message)
    """
    try:
        # Проверяем, что URL не пустой
        if not url or not url.startswith('http'):
            return False, "Некорректный URL изображения"
        
        # Быстрая проверка доступности (HEAD запрос)
        response = requests.head(url, timeout=5, allow_redirects=True)
        
        # Проверяем тип контента
        content_type = response.headers.get('Content-Type', '').lower()
        if 'image' not in content_type:
            return False, f"Неверный тип файла: {content_type}"
        
        # Проверяем размер
        content_length = response.headers.get('Content-Length')
        if content_length:
            size_mb = int(content_length) / (1024 * 1024)
            if size_mb > 20:  # Qwen ограничивает 20MB
                return False, f"Изображение слишком большое: {size_mb:.1f} MB"
        
        return True, None
        
    except requests.exceptions.Timeout:
        return False, "Превышено время ожидания при загрузке изображения"
    except Exception as e:
        print(f"⚠️ Ошибка проверки изображения: {e}")
        return False, f"Не удалось проверить изображение: {str(e)}"


def get_qwen_response_with_image(user_prompt, image_url, chat_id=None, parent_id=None):
    """Qwen с изображением"""
    try:
        # ВАЛИДАЦИЯ ИЗОБРАЖЕНИЯ
        is_valid, error_msg = validate_image_url(image_url)
        if not is_valid:
            print(f"❌ Валидация изображения провалилась: {error_msg}")
            return f"⚠️ Проблема с изображением: {error_msg}", None, None
        
        payload = {
            "message": [
                {"type": "text", "text": user_prompt or "Проанализируй изображение"},
                {"type": "image", "image": image_url}
            ],
            "model": "qwen3-vl-plus",
        }
        
        if chat_id:
            payload["chatId"] = chat_id
        if parent_id:
            payload["parentId"] = parent_id
        
        print(f"⏳ Запрос с изображением... ({config.QWEN_PROXY_URL})")
        print(f"📎 URL: {image_url[:80]}...")
        
        response = requests.post(
            f"{config.QWEN_PROXY_URL}/api/chat", 
            json=payload, 
            timeout=360
        )
        response.raise_for_status()
        data = response.json()
        
        # ПРОВЕРКА СТРУКТУРЫ ОТВЕТА
        if "choices" not in data or not data["choices"]:
            print(f"❌ Некорректная структура ответа: {json.dumps(data, ensure_ascii=False)}")
            return "❌ API вернул некорректный ответ. Попробуйте снова.", None, None
        
        log_response(data)
        
        # ИЗВЛЕЧЕНИЕ КОНТЕНТА С FALLBACK
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Если контент пустой
        if not content or content.strip() == "":
            print("⚠️ Получен пустой контент от API")
            
            # Проверяем finish_reason
            finish_reason = data.get("choices", [{}])[0].get("finish_reason", "unknown")
            print(f"   Finish reason: {finish_reason}")
            
            # Формируем понятное сообщение
            if finish_reason == "content_filter":
                content = "⚠️ Модель отказалась обрабатывать изображение (сработал контент-фильтр). Попробуйте другое изображение."
            elif finish_reason == "length":
                content = "⚠️ Ответ был обрезан из-за ограничения длины. Попробуйте упростить запрос."
            else:
                content = (
                    "⚠️ Модель вернула пустой ответ. \n\n"
                    "Используйте /new для сброса диалога."
                )
        
        # ИЗВЛЕЧЕНИЕ МЕТАДАННЫХ ДЛЯ КОНТЕКСТА
        new_chat_id = data.get("chatId") or data.get("chat_id")
        new_parent_id = (
            data.get("parentId") or 
            data.get("parent_id") or 
            data.get("response_id") or
            data.get("id")
        )
        
        print(f"✅ Ответ получен. Chat ID: {new_chat_id}, Parent ID: {new_parent_id}")
        
        return content, new_chat_id, new_parent_id
        
    except requests.exceptions.Timeout:
        print("⏰ Превышено время ожидания")
        return "⏰ Превышено время ожидания ответа от API. Попробуйте снова.", None, None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ошибка: {e}")
        if e.response:
            print(f"   Код: {e.response.status_code}")
            print(f"   Тело: {e.response.text[:500]}")
        return f"❌ Ошибка API (код {e.response.status_code if e.response else 'N/A'}). Проверьте прокси-сервер.", None, None
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА Qwen (Image): {e}")
        traceback.print_exc()
        return "❌ Произошла внутренняя ошибка. Попробуйте снова.", None, None


def get_qwen_response_text_only(user_prompt, chat_id=None, parent_id=None):
    """Qwen текст"""
    try:
        # ВАЛИДАЦИЯ ВХОДНЫХ ДАННЫХ
        if not user_prompt or user_prompt.strip() == "":
            return "⚠️ Пустой запрос. Напишите что-нибудь!", None, None
        
        payload = {
            "message": user_prompt, 
            "model": "qwen3-max"
        }
        
        if chat_id:
            payload["chatId"] = chat_id
        if parent_id:
            payload["parentId"] = parent_id
            
        print(f"⏳ Запрос (текст)... ({config.QWEN_PROXY_URL})")
        print(f"   💬 Текст: {user_prompt[:60]}...")

        response = requests.post(
            f"{config.QWEN_PROXY_URL}/api/chat", 
            json=payload, 
            timeout=90
        )
        response.raise_for_status()
        data = response.json()
        
        # ПРОВЕРКА СТРУКТУРЫ
        if "choices" not in data or not data["choices"]:
            print(f"❌ Некорректная структура ответа")
            return "❌ API вернул некорректный ответ.", None, None
        
        log_response(data)
        
        # ИЗВЛЕЧЕНИЕ С ПРОВЕРКОЙ
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        if not content or content.strip() == "":
            print("⚠️ Получен пустой контент")
            content = "⚠️ Модель вернула пустой ответ. Попробуйте переформулировать запрос."
        
        new_chat_id = data.get("chatId") or data.get("chat_id")
        new_parent_id = (
            data.get("parentId") or 
            data.get("parent_id") or 
            data.get("response_id") or
            data.get("id")
        )
        
        return content, new_chat_id, new_parent_id
        
    except requests.exceptions.Timeout:
        print("⏰ Превышено время ожидания")
        return "⏰ Таймаут. Попробуйте снова.", None, None
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ошибка: {e}")
        return f"❌ Ошибка API (код {e.response.status_code if e.response else 'N/A'}).", None, None
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА Qwen (Text): {e}")
        traceback.print_exc()
        return "❌ Произошла внутренняя ошибка. Попробуйте снова.", None, None


# УТИЛИТЫ ДЛЯ ОТЛАДКИ

def test_qwen_connection():
    """Тестирование подключения к Qwen API"""
    try:
        print("🧪 Тестируем подключение к Qwen API...\n")
        
        # Тест 1: Простой текстовый запрос
        print("1️⃣ Тестовый текстовый запрос...")
        content, chat_id, parent_id = get_qwen_response_text_only("Скажи 'привет'")
        print(f"   Результат: {content[:50]}...")
        print(f"   Chat ID: {chat_id}, Parent ID: {parent_id}\n")
        
        # Тест 2: Проверка API эндпоинта
        print("2️⃣ Проверяем доступность API...")
        response = requests.get(f"{config.QWEN_PROXY_URL}/api", timeout=5)
        print(f"   Статус: {response.status_code}")
        print(f"   Ответ: {response.text[:100]}\n")
        
        print("✅ Тесты завершены")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    # Запуск тестов при прямом вызове модуля
    test_qwen_connection()