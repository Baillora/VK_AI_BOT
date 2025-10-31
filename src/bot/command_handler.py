import config
from src.bot.vk_client import send_message

def handle_command(text, user_id, state):
    """
    Обрабатывает команды True, если команда была обработана иначе False.
    """
    if not text.startswith('/'):
        return False

    # Команды обрабатываются в режиме "raw" (без парсинга LaTeX)
    text = text.lower()
    
    if text == "/help":
        send_message(user_id,
            "🤖 Команды:\n\n"
            "/model qwen|kimi|deepseek - Выбор ИИ\n"
            "/new - Сбросить/начать новый диалог\n\n"
            "Режимы (влияют на ИИ):\n"
            "/raw - 'Сырой' текст\n"
            "/math - Для задач, формул (LaTeX, **PDF/Image**)\n"
            "/code - Для программирования, кода\n\n"
            "Формат (только для /math):\n"
            "/format text|image|pdf\n"
            "/text - Текст (по умолчанию для кода/raw)\n"
            "/image - Картинкой (с формулами)\n"
            "/pdf - Документом (с формулами, **по умолчанию для math**)\n\n"
            "📸 Отправьте фото (и текст) для Qwen"
        , mode="raw")
        return True
    
    if text == "/new":
        state.clear_user_chat(user_id)
        send_message(user_id, "✅ Контекст диалога сброшен.", mode="raw")
        return True

    if text.startswith("/model"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(user_id, "Укажите: /model qwen|kimi|deepseek", mode="raw")
            return True
        
        model = parts[1].lower()
        if model in config.MODELS:
            state.set_user_model(user_id, model)
            send_message(user_id, f"✅ Модель: {model}", mode="raw")
        else:
            send_message(user_id, "❌ Неизвестная модель", mode="raw")
        return True
    
    # --- КОМАНДЫ ФОРМАТА (/format, /pdf, /image, /text) ---
    
    if text.startswith("/format"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            send_message(user_id, "Укажите: /format text|image|pdf", mode="raw")
            return True
        
        fmt = parts[1].lower()
        if state.set_format(user_id, fmt):
            send_message(user_id, f"✅ Формат: {fmt}", mode="raw")
        else:
            send_message(user_id, "❌ Доступны: text, image, pdf", mode="raw")
        return True
    
    elif text == "/pdf":
        # Команды /pdf /image /text влияют только на формат
        state.set_format(user_id, "pdf")
        send_message(user_id, "✅ Формат вывода: PDF", mode="raw")
        return True

    elif text == "/image":
        state.set_format(user_id, "image")
        send_message(user_id, "✅ Формат вывода: Изображение", mode="raw")
        return True
        
    elif text == "/text":
        state.set_format(user_id, "text")
        send_message(user_id, "✅ Формат вывода: Текст", mode="raw")
        return True
    
    # --- КОМАНДЫ РЕЖИМА (/math, /code, /raw) ---
    
    elif text == "/math":
        state.set_mode(user_id, "math")
        # Устанавливаем формат по умолчанию PDF
        state.set_format(user_id, "pdf")
        send_message(user_id, "✅ Режим: Математика (LaTeX). Формат по умолчанию: PDF.", mode="raw")
        return True

    elif text == "/code":
        state.set_mode(user_id, "code")
        state.set_format(user_id, "text") # Сбрасываем формат для кода в текст
        send_message(user_id, "✅ Режим: Код (Форматирование ``` ... ```)", mode="raw")
        return True
        
    elif text == "/raw":
        state.set_mode(user_id, "raw")
        state.set_format(user_id, "text") # Сбрасываем формат для raw в текст
        send_message(user_id, "✅ Режим: Raw (Без обработки)", mode="raw")
        return True
    
    send_message(user_id, "❓ Неизвестная команда. Введите /help для списка.", mode="raw")
    return True