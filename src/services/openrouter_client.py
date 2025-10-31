from openai import OpenAI, APITimeoutError, APIConnectionError
import traceback
import config

try:
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )
except Exception as e:
    print(f"❌ Не удалось инициализировать OpenRouter: {e}")
    openrouter_client = None


def get_openrouter_response(model_name, user_prompt):
    """OpenRouter"""
    if not openrouter_client:
        return "❌ Клиент OpenRouter не инициализирован."

    model_id = config.MODELS.get(model_name)
    if not model_id or model_id == "proxy":
        return f"❌ Ошибка: модель {model_name} не настроена для OpenRouter."
    
    print(f"⏳ Запрос к OpenRouter ({model_id})...")

    try:
        completion = openrouter_client.chat.completions.create(
            
            # заголовки берутся из config
            extra_headers={
                "HTTP-Referer": config.APP_REFERER, 
                "X-Title": config.APP_TITLE
            },
            # -------------------------
            model=model_id,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=1000,
            timeout=45,
        )
        return completion.choices[0].message.content
    except APITimeoutError:
        return f"⏰ {model_name}: Таймаут"
    except APIConnectionError:
        return f"🔌 {model_name}: Ошибка подключения к OpenRouter"
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА OpenRouter: {e}")
        traceback.print_exc()
        return "❌ Произошла внутренняя ошибка. Попробуйте снова."