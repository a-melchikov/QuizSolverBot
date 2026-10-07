# QuizSolverBot

Telegram-бот для тренировки и решения тестов (викторин) на базе **Python 3.14**, **Aiogram 3**, **SQLAlchemy 2** (AsyncIO), **Alembic**, **aiosqlite** и пакета **uv**.

---

## Требования

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (быстрый менеджер пакетов Python)
- Docker и Docker Compose (для контейнеризации)

---

## Быстрый старт

### 1. Настройка окружения

Скопируйте шаблон переменных окружения и укажите токен бота:

```bash
cp .env.template .env
```

Заполните `.env`:
```ini
TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
SQLITE_DB_PATH=data/database.db
ADMINS=123456789,987654321
```

### 2. Установка зависимостей (uv)

```bash
uv sync
```

### 3. Запуск тестов и проверка кода

```bash
# Запуск автотестов
uv run pytest -v

# Проверка форматирования и линтинг
uv run ruff check .
uv run ruff format --check .
```

### 4. Загрузка вопросов в базу данных

Для импорта базы вопросов из текстового файла (`questions.txt`):

```bash
uv run python -m app.utils.parse_question questions.txt
```

### 5. Запуск бота

```bash
uv run python main.py
```

> **Примечание:** Миграции базы данных Alembic применяются автоматически при старте бота.

---

## Запуск в Docker

### С помощью Docker Compose (рекомендуется)

```bash
docker compose up -d --build
```

### С помощью Docker напрямую

```bash
docker build -t telegram-bot-quiz .
docker run -v $(pwd)/data:/app/data --env-file .env -d --name telegram-bot-quiz telegram-bot-quiz
```

---

## Команды бота

- `/start` — регистрация и приветствие.
- `/help` — меню доступных команд и действий.
- `/start_test` — запуск режима тестирования с выбором количества вопросов.
- `/start_question` — решение одного вопроса по его ID.
- `/list_questions` — просмотр списка доступных вопросов с постраничной пагинацией.
- `/solve_question <id>` — отображение вопроса с правильным ответом.
- `/history` — просмотр истории ваших попыток прохождения теста.

### Команды администратора (доступны только ID из `ADMINS`):
- `/add_question` — пошаговое добавление нового вопроса через FSM.
- `/delete_question <id>` — удаление вопроса по идентификатору.