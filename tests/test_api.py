import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest
from httpx import ASGITransport, AsyncClient

from app.api import create_app
from app.api.auth import validate_telegram_data
from app.models import Option, Question


def generate_valid_tg_init_data(bot_token: str, user_dict: dict) -> str:
    data = {
        "auth_date": "1710000000",
        "query_id": "AAHdF6IQAAAAAN0XohC8b28a",
        "user": json.dumps(user_dict, separators=(",", ":")),
    }
    data_check_list = [f"{k}={v}" for k, v in sorted(data.items())]
    data_check_string = "\n".join(data_check_list)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    hash_val = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    data["hash"] = hash_val
    return urlencode(data)


def test_telegram_auth_validation():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    user_info = {"id": 987654321, "first_name": "Тест", "username": "tester"}

    valid_init_data = generate_valid_tg_init_data(bot_token, user_info)
    validated = validate_telegram_data(valid_init_data, bot_token)
    assert validated is not None
    assert validated["id"] == 987654321
    assert validated["first_name"] == "Тест"

    # Tampered data
    tampered_init_data = valid_init_data.replace("tester", "hacker")
    assert validate_telegram_data(tampered_init_data, bot_token) is None

    # Empty
    assert validate_telegram_data("", bot_token) is None


@pytest.mark.asyncio
async def test_api_static_and_me(session_maker):
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check static index.html
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "Quiz Solver" in resp.text

        # Check /api/me
        resp = await client.get("/api/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "total_attempts" in data


@pytest.mark.asyncio
async def test_api_quiz_flow(session_maker):
    app = create_app()
    transport = ASGITransport(app=app)

    # Seed 2 questions in the database
    async with session_maker() as session:
        q1 = Question(text="Столица Франции?", has_options=True)
        q1.options.append(Option(option_text="Париж", is_correct=True))
        q1.options.append(Option(option_text="Лондон", is_correct=False))
        session.add(q1)

        q2 = Question(text="Сколько будет 2+2?", has_options=False, answer_text="4")
        session.add(q2)
        await session.commit()
        await session.refresh(q1, attribute_names=["options"])
        await session.refresh(q2)
        q1_id = q1.id
        q1_opt_correct = [o.id for o in q1.options if o.is_correct][0]
        q2_id = q2.id

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get questions catalog
        cat_resp = await client.get("/api/questions")
        assert cat_resp.status_code == 200
        cat_data = cat_resp.json()
        assert cat_data["total"] >= 2

        # 2. Start quiz in training mode
        start_resp = await client.post(
            "/api/quiz/start", json={"count": 5, "mode": "training"}
        )
        assert start_resp.status_code == 200
        start_data = start_resp.json()
        attempt_id = start_data["test_attempt_id"]
        assert attempt_id > 0
        assert len(start_data["questions"]) >= 2

        # 3. Check single answer (training)
        check_resp = await client.post(
            "/api/quiz/check-answer",
            json={"question_id": q1_id, "selected_option_ids": [q1_opt_correct]},
        )
        assert check_resp.status_code == 200
        assert check_resp.json()["is_correct"] is True

        # Check text answer
        check_text = await client.post(
            "/api/quiz/check-answer",
            json={"question_id": q2_id, "text_answer": "4"},
        )
        assert check_text.status_code == 200
        assert check_text.json()["is_correct"] is True

        # 4. Finish quiz
        finish_resp = await client.post(
            "/api/quiz/finish",
            json={
                "test_attempt_id": attempt_id,
                "answers": [
                    {"question_id": q1_id, "selected_option_ids": [q1_opt_correct]},
                    {"question_id": q2_id, "text_answer": "4"},
                ],
            },
        )
        assert finish_resp.status_code == 200
        finish_data = finish_resp.json()
        assert finish_data["score"] == 2
        assert finish_data["percentage"] == 100.0
        assert len(finish_data["reviews"]) == 2

        # 5. Check history
        hist_resp = await client.get("/api/history")
        assert hist_resp.status_code == 200
        hist_data = hist_resp.json()
        assert len(hist_data["items"]) >= 1
        assert hist_data["items"][0]["score"] == 2
