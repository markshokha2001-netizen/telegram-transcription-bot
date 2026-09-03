import httpx
from groq import AsyncGroq
from bot.config import GROQ_API_KEY


class Summarizer:
    def __init__(self):
        """Инициализирует Groq API для создания конспектов"""
        http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(300.0, connect=60.0),
            follow_redirects=True
        )
        self.client = AsyncGroq(api_key=GROQ_API_KEY, http_client=http_client)

    async def create_summary(self, transcript: str) -> str:
        """
        Создаёт структурированный конспект из дословного транскрипта.
        Убирает слова-паразиты, повторы, структурирует по смысловым пунктам.
        """
        prompt = f"""Ты получил дословную транскрипцию аудиозаписи. Твоя задача:

1. Убрать слова-паразиты (эээ, ммм, ну, как бы, типа и т.п.)
2. Убрать повторы и запинки
3. Структурировать текст по смысловым пунктам
4. Сохранить все факты, цифры и важную информацию БЕЗ ИСКАЖЕНИЙ
5. Ничего не додумывать и не добавлять от себя

Транскрипт:
{transcript}

Создай краткий структурированный конспект:"""

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "Ты помощник для создания структурированных конспектов из транскриптов аудиозаписей."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"Ошибка при создании конспекта: {str(e)}")
