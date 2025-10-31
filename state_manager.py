class StateManager:
    
    # Управляет состоянием пользователей, заменяя глобальные словари.
    def __init__(self):
        self.user_model_choice = {}
        self.user_chats = {}
        self.user_format_preference = {}
        self.user_processing_mode = {}

    # --- Модель ---
    def get_user_model(self, user_id):
        return self.user_model_choice.get(user_id, "qwen")

    def set_user_model(self, user_id, model):
        self.user_model_choice[user_id] = model

    # --- Чат (для Qwen) ---
    def get_user_chat(self, user_id):
        """Возвращает (chat_id, parent_id)"""
        return self.user_chats.get(user_id)

    def update_user_chat(self, user_id, chat_id, parent_id):
        if chat_id and parent_id:
            self.user_chats[user_id] = (chat_id, parent_id)

    def clear_user_chat(self, user_id):
        self.user_chats.pop(user_id, None)

    # --- Формат вывода (/math) ---
    def get_format(self, user_id):
        return self.user_format_preference.get(user_id, "text")

    def set_format(self, user_id, fmt):
        if fmt in ["text", "image", "pdf"]:
            self.user_format_preference[user_id] = fmt
            return True
        return False

    # --- Режим обработки (math, code, raw) ---
    def get_mode(self, user_id):
        return self.user_processing_mode.get(user_id, "raw") 

    def set_mode(self, user_id, mode):
        if mode in ["math", "code", "raw"]:
            self.user_processing_mode[user_id] = mode
            return True
        return False