"""
Красивый прогресс-бар для отображения процесса обработки
"""
import asyncio
import random
from typing import Optional, Callable
from aiogram.types import Message


class ProgressBar:
    """Класс для создания анимированного прогресс-бара"""

    def __init__(self, message: Message, total_steps: int = 100):
        self.message = message
        self.total_steps = total_steps
        self.current_step = 0
        self.status_message: Optional[Message] = None
        self.is_running = False
        self.should_stop = False

        # Визуальные элементы
        self.filled_char = "🟩"
        self.empty_char = "⬜"
        self.bar_length = 10

    def _get_status_text(self, progress: int) -> str:
        """Возвращает текст статуса в зависимости от прогресса"""
        if progress < 15:
            return "🔍 Сканирую файл..."
        elif progress < 30:
            return "📥 Загружаю данные..."
        elif progress < 50:
            return "🎵 Извлекаю аудио..."
        elif progress < 70:
            return "🤖 Транскрибирую (ИИ думает)..."
        elif progress < 85:
            return "✨ Обрабатываю результат..."
        elif progress < 95:
            return "🔧 Финализирую..."
        else:
            return "✅ Почти готово!"

    def _render_bar(self, progress: int) -> str:
        """Рисует прогресс-бар"""
        filled = int(self.bar_length * progress / 100)
        empty = self.bar_length - filled

        bar = self.filled_char * filled + self.empty_char * empty
        percentage = f"{progress}%"

        status = self._get_status_text(progress)

        return f"{status}\n\n[{bar}] {percentage}"

    async def start(self, completion_check: Optional[Callable[[], bool]] = None):
        """
        Запускает анимацию прогресс-бара

        Args:
            completion_check: функция, которая возвращает True когда задача завершена
        """
        if self.is_running:
            return

        self.is_running = True
        self.should_stop = False
        self.current_step = 0

        # Создаём начальное сообщение
        self.status_message = await self.message.answer(self._render_bar(0))

        # Нелинейные этапы загрузки
        stages = [
            # (до какого %, средняя скорость шага, задержка между обновлениями)
            (15, 3, 0.3),   # Быстрый старт
            (25, 2, 0.5),   # Замедление
            (40, 1, 0.8),   # Медленная фаза (думает)
            (50, 2, 0.6),   # Ускорение
            (70, 1, 1.0),   # Очень медленно (ИИ транскрибирует)
            (85, 3, 0.4),   # Ускорение к концу
            (95, 2, 0.3),   # Финализация
        ]

        try:
            for target, speed, delay in stages:
                while self.current_step < target and not self.should_stop:
                    # Проверяем, завершена ли задача
                    if completion_check and completion_check():
                        # Задача завершена — прыгаем к 100%
                        self.current_step = 100
                        break

                    # Добавляем случайность к скорости
                    step = random.randint(max(1, speed - 1), speed + 1)
                    self.current_step = min(self.current_step + step, target)

                    # Обновляем визуализацию
                    try:
                        await self.status_message.edit_text(self._render_bar(self.current_step))
                    except:
                        pass  # Игнорируем ошибки редактирования (too many requests)

                    # Случайная задержка для реалистичности
                    actual_delay = delay + random.uniform(-0.1, 0.2)
                    await asyncio.sleep(max(0.1, actual_delay))

                if self.should_stop or self.current_step >= 100:
                    break

            # Финальный рывок до 100% если задача завершена
            if completion_check and completion_check() and self.current_step < 100:
                for i in range(self.current_step, 101, 5):
                    self.current_step = i
                    try:
                        await self.status_message.edit_text(self._render_bar(self.current_step))
                    except:
                        pass
                    await asyncio.sleep(0.1)

        finally:
            self.is_running = False

    async def complete(self):
        """Завершает прогресс-бар и показывает 100%"""
        self.should_stop = True
        self.current_step = 100

        if self.status_message:
            try:
                await self.status_message.edit_text(self._render_bar(100))
                await asyncio.sleep(0.5)  # Показываем 100% на полсекунды
                await self.status_message.delete()
            except:
                pass

    async def update_to(self, progress: int):
        """Принудительно обновляет прогресс до определённого значения"""
        self.current_step = min(max(0, progress), 100)
        if self.status_message:
            try:
                await self.status_message.edit_text(self._render_bar(self.current_step))
            except:
                pass


async def with_progress_bar(message: Message, task_coroutine, estimated_time: float = 30.0):
    """
    Обёртка для выполнения задачи с прогресс-баром

    Args:
        message: сообщение пользователя
        task_coroutine: корутина задачи для выполнения
        estimated_time: примерное время выполнения в секундах

    Returns:
        Результат выполнения задачи
    """
    progress = ProgressBar(message)

    # Флаг завершения задачи
    task_completed = False

    def is_completed():
        return task_completed

    # Запускаем прогресс-бар в фоне
    progress_task = asyncio.create_task(progress.start(completion_check=is_completed))

    try:
        # Выполняем основную задачу
        result = await task_coroutine

        # Задача завершена
        task_completed = True

        # Ждём пока прогресс-бар дойдёт до 100%
        await asyncio.sleep(0.5)

        # Завершаем прогресс-бар
        await progress.complete()

        return result

    except Exception as e:
        task_completed = True
        await progress.complete()
        raise e
    finally:
        # Останавливаем прогресс-бар если он ещё работает
        if not progress_task.done():
            progress_task.cancel()
            try:
                await progress_task
            except asyncio.CancelledError:
                pass
