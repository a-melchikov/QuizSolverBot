FROM python:3.13-slim

RUN pip install poetry

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry config virtualenvs.create false && poetry install --no-root --no-interaction --no-ansi

COPY . .

ENV PYTHONPATH=/app

CMD ["python", "main.py"]