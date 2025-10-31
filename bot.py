import traceback
from vk_api.bot_longpoll import VkBotEventType

import config
from state_manager import StateManager
from src.bot import vk_client, command_handler, message_handler

def main():
    # 1. Инициализация
    longpoll = vk_client.get_longpoll_listener()
    state = StateManager()
    
    print(f"✅ Бот запущен. Группа ID: {config.GROUP_ID}")
    if config.TRUSTED_IDS:
        print(f"🔒 Доверенные ID: {sorted(config.TRUSTED_IDS)}")
    else:
        print("⚠️ Бот доступен всем (TRUSTED_IDS не задан)")
    
    print("👂 Слушаю...")

    # 2. Главный цикл
    for event in longpoll.listen():
        if event.type != VkBotEventType.MESSAGE_NEW:
            continue
            
        msg = event.obj.message
        user_id = msg["from_id"]
        text = msg.get("text", "").strip()
        attachments = msg.get("attachments", [])

        # 3. Фильтры
        if config.TRUSTED_IDS and user_id not in config.TRUSTED_IDS:
            print(f"[{user_id}] ID нет в списке доверенных, игнорирую.")
            continue
            
        if not text and not attachments:
            print(f"[{user_id}] ...пустой запрос, игнорирую.")
            continue
            
        print(f"📩 [{user_id}] {text[:60]}...")
        
        try:
            # 4. Обработка команд
            # (handle_command сам отправит ответ, если это команда)
            if command_handler.handle_command(text, user_id, state):
                continue
            
            # 5. Обработка сообщений AI
            message_handler.handle_message(msg, user_id, state)

        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА В ЦИКЛЕ: {e}")
            traceback.print_exc()
            try:
                vk_client.send_message(
                    user_id, 
                    "❌ Произошла непредвиденная внутренняя ошибка. "
                    "Я сообщил о ней администратору.", 
                    mode="raw"
                )
            except:
                pass

if __name__ == "__main__":
    main()