import httpx
import asyncio
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
        self.max_chars_per_chunk = 10000  # ~5000-6000 токенов (с запасом для промпта = ~6000-7000 токенов)

    def split_text(self, text: str, max_chars: int) -> list[str]:
        """Разбивает текст на части по максимальному количеству символов"""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        while text:
            # Ищем конец предложения в пределах лимита
            if len(text) <= max_chars:
                chunks.append(text)
                break

            # Ищем конец предложения (точка, восклицательный, вопросительный)
            chunk = text[:max_chars]
            last_period = max(chunk.rfind('. '), chunk.rfind('! '), chunk.rfind('? '))

            if last_period > max_chars // 2:  # Нашли разумное место для разреза
                split_pos = last_period + 2
            else:  # Режем по пробелу
                last_space = chunk.rfind(' ')
                split_pos = last_space if last_space > 0 else max_chars

            chunks.append(text[:split_pos])
            text = text[split_pos:]

        return chunks

    async def create_summary(self, transcript: str) -> str:
        """
        Создаёт структурированный конспект из дословного транскрипта.
        Убирает слова-паразиты, повторы, структурирует по смысловым пунктам.
        """
        # Если текст короткий — обрабатываем за раз
        if len(transcript) <= self.max_chars_per_chunk:
            return await self._summarize_chunk(transcript)

        # Длинный текст — разбиваем на части
        chunks = self.split_text(transcript, self.max_chars_per_chunk)
        summaries = []

        for i, chunk in enumerate(chunks, 1):
            print(f"[Summarizer] Обрабатываю часть {i}/{len(chunks)}...")
            summary = await self._summarize_chunk(chunk, part_num=i, total_parts=len(chunks))
            summaries.append(summary)

            # Пауза между запросами (соблюдаем rate limit 8000 токенов/минуту)
            if i < len(chunks):
                await asyncio.sleep(10)  # 10 секунд между частями

        # Склеиваем все части
        return "\n\n".join(summaries)

    async def _summarize_chunk(self, text: str, part_num: int = None, total_parts: int = None) -> str:
        """Создаёт конспект для одной части текста"""
        part_info = f" (часть {part_num} из {total_parts})" if part_num else ""

        prompt = f"""Ты получил дословную транскрипцию аудиозаписи{part_info}. Твоя задача:

1. Убрать слова-паразиты (эээ, ммм, ну, как бы, типа и т.п.)
2. Убрать повторы и запинки
3. Структурировать текст по смысловым пунктам
4. Сохранить все факты, цифры и важную информацию БЕЗ ИСКАЖЕНИЙ
5. Ничего не додумывать и не добавлять от себя

Транскрипт:
{text}

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

    async def fix_transcript(self, transcript: str) -> str:
        """
        Исправляет ошибки в словах транскрипции с учётом контекста.
        Фокус на исправлении слов, а не на пунктуации.
        """
        # Если текст короткий — обрабатываем за раз
        if len(transcript) <= self.max_chars_per_chunk:
            return await self._fix_chunk(transcript)

        # Длинный текст — разбиваем на части
        chunks = self.split_text(transcript, self.max_chars_per_chunk)
        fixed_parts = []

        for i, chunk in enumerate(chunks, 1):
            print(f"[Summarizer] Исправляю часть {i}/{len(chunks)}...")
            fixed = await self._fix_chunk(chunk)
            fixed_parts.append(fixed)

            # Пауза между запросами (соблюдаем rate limit)
            if i < len(chunks):
                await asyncio.sleep(10)  # 10 секунд между частями

        # Склеиваем все части
        return " ".join(fixed_parts)

    async def _fix_chunk(self, text: str) -> str:
        """Исправляет ошибки для одной части текста"""
        prompt = f"""Ты получил автоматическую транскрипцию речи. Твоя задача — исправить СЛОВА, понимая контекст:

ЧТО ИСПРАВЛЯТЬ:
1. Добавить пропущенные предлоги и союзы ("переводить текст" → "переводить в текст")
2. Исправить неправильные окончания слов (если не подходят по контексту)
3. Исправить созвучные ошибки распознавания ("пришёл" вместо "прошёл", "продал" вместо "пропал")
4. Добавить минимум пунктуации — только точки в конце предложений и запятые где критично

ЧТО НЕ ДЕЛАТЬ:
1. НЕ убирай разговорные слова (а, ну, вот, типа, короче, как бы — оставляй!)
2. НЕ меняй порядок слов
3. НЕ переформулируй
4. НЕ перегружай пунктуацией — только необходимое

Транскрипт:
{text}

Исправленный текст (все слова на месте, исправлены ошибки по контексту):"""

        try:
            response = await self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "Ты исправляешь ошибки распознавания речи, добавляешь пропущенные предлоги, исправляешь неправильные окончания и созвучные слова по контексту. НЕ убираешь разговорные слова, НЕ переформулируешь. Минимум пунктуации."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.15,
                max_tokens=4000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            raise RuntimeError(f"Ошибка при исправлении текста: {str(e)}")

