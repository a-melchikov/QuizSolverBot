# QuizSolverBot

Telegram-бот и **Telegram Mini App (TMA)** для тренировки и решения тестов (викторин) на базе **Python 3.14**, **Aiogram 3**, **FastAPI**, **SQLAlchemy 2** (AsyncIO), **Alembic**, **aiosqlite** и менеджера пакетов **uv**.

---

## Возможности

- 🚀 **Telegram Mini App (Web App)**:
  - Удобный веб-интерфейс прямо внутри Telegram (адаптируется под темную и светлую тему Telegram, haptic feedback).
  - Два режима прохождения:
    - **«Тренировка»**: мгновенная проверка ответов и подсветка ошибок.
    - **«Экзамен»**: непрерывное решение теста с подробным разбором результатов в конце.
  - **Каталог вопросов**: живой поиск в реальном времени и просмотр правильных ответов.
  - **Личный кабинет**: общая статистика успеваемости, средний балл и история завершенных попыток.
- 💬 **Telegram-бот**:
  - Решение одиночных вопросов и тестов через интерактивные Telegram Polls.
  - Просмотр истории попыток и списка вопросов через чат.
  - Панель администратора (`ADMINS`) для добавления и удаления вопросов.
- 📦 **Монолитная архитектура**:
  - FastAPI сервер и Aiogram поллинг запускаются параллельно в одном процессе.
  - Общая база данных SQLite и модели SQLAlchemy.

---

## Требования

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) (быстрый менеджер пакетов Python)
- Docker и Docker Compose (для контейнеризации)

---

## Быстрый старт

### 1. Настройка окружения

Скопируйте шаблон переменных окружения:

```bash
cp .env.template .env
```

Заполните `.env`:
```ini
TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
SQLITE_DB_PATH=data/database.db
ADMINS=123456789,987654321
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8000
WEBAPP_URL=https://your-domain-or-tunnel.example.com
```

> **Совет для WebApp:** Чтобы Mini App открывался в Telegram, укажите HTTPS URL (например, полученный через `ngrok http 8000` или Caddy/Cloudflare Tunnel) в `WEBAPP_URL`. Локально в браузере интерфейс доступен по адресу `http://localhost:8000`.

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

### 5. Запуск приложения

```bash
uv run python main.py
```

При запуске:
- Автоматически применяются миграции Alembic.
- Стартует веб-сервер Mini App на порту 8000.
- Стартует поллинг Telegram-бота.

---

## Запуск в Docker

### С помощью Docker Compose (рекомендуется)

```bash
docker compose up -d --build
```

Сервер Mini App будет доступен на порту `8000`.

---

## Команды бота

- `/start` — приветствие и кнопка запуска Web App.
- `/help` — меню доступных команд и кнопка Web App.
- `/start_test` — запуск теста через Telegram Polls.
- `/start_question` — решение одного вопроса по ID.
- `/list_questions` — просмотр списка вопросов с пагинацией.
- `/solve_question <id>` — отображение вопроса с правильным ответом.
- `/history` — история ваших попыток.

### Команды администратора (доступны пользователям из `ADMINS`):
- `/add_question` — пошаговое добавление вопроса через FSM.
- `/delete_question <id>` — удаление вопроса по ID.