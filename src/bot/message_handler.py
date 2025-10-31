import traceback
from src.bot.vk_client import send_message, send_as_format, TypingStatusController
from src.services import prompt_builder, qwen_client, openrouter_client


def handle_message(msg_obj, user_id, state):
    """
    Обрабатывает обычные (не команды) сообщения.
    """
    text = msg_obj.get("text", "").strip()
    # В LongPoll Bot API имеет поле 'message'
    msg_data = msg_obj.get("message", msg_obj) #  msg_obj на случай, если структура другая
    attachments = msg_data.get("attachments", [])
    
    # --- СБРОС КОНТЕКСТА ---
    # Если это НЕ ответ на сообщение (нет reply_message), то сбрасываем контекст Qwen.
    if 'reply_message' not in msg_data:
        state.clear_user_chat(user_id) 
        
    # --- 1 Обработка вложений ---
    image_url = None
    has_unsupported_attachments = False
    if attachments:
        for att in attachments:
            if att["type"] == "photo":
                sizes = att["photo"]["sizes"]
                largest = max(sizes, key=lambda s: s["width"] * s["height"])
                image_url = largest["url"]
                break # Поддерживаем только одно фото пока так
            else:
                # Любой другой тип (doc, video, etc.)
                has_unsupported_attachments = True
        
        if has_unsupported_attachments and not image_url:
            send_message(user_id, "⚠️ Я умею работать только с *фотографиями* (jpg, png). Пожалуйста, не присылайте документы, видео или другие файлы.", mode="raw")
            return

    # --- 2 Получение настроек ---
    current_model = state.get_user_model(user_id)
    current_mode = state.get_mode(user_id)
    current_format = state.get_format(user_id)
    chat_context = state.get_user_chat(user_id)
    chat_id, parent_id = (chat_context[0], chat_context[1]) if chat_context else (None, None)

    # Изображения поддерживаются только Qwen
    if image_url and current_model != "qwen":
        send_message(user_id, f"⚠️ Выбрана модель {current_model}, она не умеет работать с изображениями. Временно переключаю на Qwen.", mode="raw")
        current_model = "qwen"

    # --- 3 Сборка промпта ---
    final_prompt = prompt_builder.get_final_prompt(text, current_mode, image_url)

    # --- 4 Отправка подтверждения и запуск индикатора ---
    model_name = current_model.upper()
    mode_name = current_mode.upper()
    image_status = " 📸 (с фото)" if image_url else ""

    send_message(user_id, 
        f"🤖 {model_name} | Режим: {mode_name}{image_status} | Ваш запрос принят в работу...", 
        mode="raw"
    )
    print(f"-> 🧠 {current_model} | {current_mode}{image_status} запрос отправлен в работу.")
    
    # ЗАПУСК КОНТРОЛЛЕРА
    typing_controller = TypingStatusController(user_id)
    typing_controller.start()
    
    response_text = ""
    new_chat_id, new_parent_id = None, None
    
    try:
        # --- 5 Вызов AI ---
        if current_model == "qwen":
            if image_url:
                response_text, new_chat_id, new_parent_id = qwen_client.get_qwen_response_with_image(
                    final_prompt, image_url, chat_id, parent_id
                )
            else:
                response_text, new_chat_id, new_parent_id = qwen_client.get_qwen_response_text_only(
                    final_prompt, chat_id, parent_id
                )
            
            # Обнова контекста чата qwen
            if new_chat_id:
                state.update_user_chat(user_id, new_chat_id, new_parent_id)
                
        else:
            # OpenRouter (Kimi, Deepseek)
            response_text = openrouter_client.get_openrouter_response(
                current_model, final_prompt
            )

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА AI: {e}")
        traceback.print_exc()
        send_message(user_id, f"❌ Ошибка при обработке запроса: {e}", mode="raw")
        raise e # Перебрасываем исключение для обработки в finally

    finally:
        # ОСТАНОВКА ИНДИКАТОРА ПРОИЗВОДИТСЯ ЗДЕСЬ
        typing_controller.stop()

    # --- 6 Отправка ответа ---
    if response_text:
        send_as_format(user_id, response_text, current_format, current_mode)
    else:
        send_message(user_id, "❌ Получен пустой ответ от AI.", mode="raw")