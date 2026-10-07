from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.auth import get_current_user
from app.database import async_session_maker
from app.models import AttemptAnswer, Question, TestAttempt, User

router = APIRouter(prefix="/api", tags=["Quiz Mini App"])


# ---------------- Schemas ----------------
class OptionOut(BaseModel):
    id: int
    option_text: str
    is_correct: bool | None = None  # None in exam mode


class QuestionOut(BaseModel):
    id: int
    text: str
    has_options: bool
    options: list[OptionOut]
    answer_text: str | None = None  # None in exam mode


class QuizStartRequest(BaseModel):
    count: int = 10
    mode: str = "training"  # "training" or "exam"


class QuizStartResponse(BaseModel):
    test_attempt_id: int
    mode: str
    total_questions: int
    questions: list[QuestionOut]


class CheckAnswerRequest(BaseModel):
    question_id: int
    selected_option_ids: list[int] | None = None
    text_answer: str | None = None


class CheckAnswerResponse(BaseModel):
    is_correct: bool
    correct_option_ids: list[int]
    correct_option_texts: list[str]
    expected_answer_text: str | None


class AnswerSubmission(BaseModel):
    question_id: int
    selected_option_ids: list[int] | None = None
    text_answer: str | None = None


class QuizFinishRequest(BaseModel):
    test_attempt_id: int
    answers: list[AnswerSubmission]


class QuestionReview(BaseModel):
    question_id: int
    text: str
    has_options: bool
    is_correct: bool
    user_answer: str
    correct_answer: str


class QuizFinishResponse(BaseModel):
    test_attempt_id: int
    score: int
    total_questions: int
    percentage: float
    duration_seconds: int
    reviews: list[QuestionReview]


# ---------------- Endpoints ----------------
@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        attempts_q = await session.execute(
            select(TestAttempt).where(TestAttempt.user_id == user.id)
        )
        attempts = list(attempts_q.scalars().all())

        total_attempts = len(attempts)
        completed_attempts = [a for a in attempts if a.end_time is not None]
        avg_score = (
            sum(
                (a.score / a.total_questions * 100)
                for a in completed_attempts
                if a.total_questions > 0
            )
            / len(completed_attempts)
            if completed_attempts
            else 0.0
        )

    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "total_attempts": total_attempts,
        "completed_attempts": len(completed_attempts),
        "avg_percentage": round(avg_score, 1),
    }


@router.get("/questions")
async def list_questions(
    q: str | None = Query(None, description="Поисковый запрос"),
    has_options: bool | None = Query(None, description="Фильтр по типу вопроса"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit
    async with async_session_maker() as session:
        query = select(Question).options(selectinload(Question.options))
        count_query = select(func.count(Question.id))

        if q:
            query = query.where(Question.text.ilike(f"%{q.strip()}%"))
            count_query = count_query.where(Question.text.ilike(f"%{q.strip()}%"))

        if has_options is not None:
            query = query.where(Question.has_options == has_options)
            count_query = count_query.where(Question.has_options == has_options)

        total_count = (await session.execute(count_query)).scalar() or 0

        query = query.order_by(Question.id.asc()).limit(limit).offset(offset)
        result = await session.execute(query)
        questions = list(result.scalars().all())

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 0,
        "items": [
            {
                "id": q_item.id,
                "text": q_item.text,
                "has_options": q_item.has_options,
                "answer_text": q_item.answer_text,
                "options": [
                    {
                        "id": opt.id,
                        "option_text": opt.option_text,
                        "is_correct": opt.is_correct,
                    }
                    for opt in q_item.options
                ],
            }
            for q_item in questions
        ],
    }


@router.post("/quiz/start", response_model=QuizStartResponse)
async def start_quiz(
    payload: QuizStartRequest,
    user: User = Depends(get_current_user),
):
    async with async_session_maker() as session:
        total_avail = (
            await session.execute(select(func.count(Question.id)))
        ).scalar() or 500
        count = max(1, min(payload.count, total_avail))
        query = (
            select(Question)
            .options(selectinload(Question.options))
            .order_by(func.random())
            .limit(count)
        )
        result = await session.execute(query)
        questions = list(result.scalars().all())

        if not questions:
            # Fallback if no questions
            return QuizStartResponse(
                test_attempt_id=0,
                mode=payload.mode,
                total_questions=0,
                questions=[],
            )

        test_attempt = TestAttempt(
            user_id=user.id,
            total_questions=len(questions),
            start_time=datetime.now(),
        )
        session.add(test_attempt)
        await session.commit()
        await session.refresh(test_attempt)

    is_exam = payload.mode == "exam"
    out_questions = []
    for q in questions:
        out_questions.append(
            QuestionOut(
                id=q.id,
                text=q.text,
                has_options=q.has_options,
                answer_text=None if is_exam else q.answer_text,
                options=[
                    OptionOut(
                        id=opt.id,
                        option_text=opt.option_text,
                        is_correct=None if is_exam else opt.is_correct,
                    )
                    for opt in q.options
                ],
            )
        )

    return QuizStartResponse(
        test_attempt_id=test_attempt.id,
        mode=payload.mode,
        total_questions=len(out_questions),
        questions=out_questions,
    )


@router.post("/quiz/check-answer", response_model=CheckAnswerResponse)
async def check_single_answer(
    payload: CheckAnswerRequest,
    user: User = Depends(get_current_user),
):
    async with async_session_maker() as session:
        query = (
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == payload.question_id)
        )
        result = await session.execute(query)
        question = result.scalar_one_or_none()
        if not question:
            return CheckAnswerResponse(
                is_correct=False,
                correct_option_ids=[],
                correct_option_texts=[],
                expected_answer_text="",
            )

        if question.has_options:
            correct_opts = [o for o in question.options if o.is_correct]
            correct_ids = [o.id for o in correct_opts]
            user_ids = payload.selected_option_ids or []
            is_correct = set(user_ids) == set(correct_ids)
            return CheckAnswerResponse(
                is_correct=is_correct,
                correct_option_ids=correct_ids,
                correct_option_texts=[o.option_text for o in correct_opts],
                expected_answer_text=None,
            )
        else:
            expected = (question.answer_text or "").strip()
            user_val = (payload.text_answer or "").strip()
            is_correct = user_val.lower() == expected.lower()
            return CheckAnswerResponse(
                is_correct=is_correct,
                correct_option_ids=[],
                correct_option_texts=[],
                expected_answer_text=expected,
            )


@router.post("/quiz/finish", response_model=QuizFinishResponse)
async def finish_quiz(
    payload: QuizFinishRequest,
    user: User = Depends(get_current_user),
):
    end_time = datetime.now()
    async with async_session_maker() as session:
        test_attempt = await session.get(TestAttempt, payload.test_attempt_id)
        if not test_attempt or test_attempt.user_id != user.id:
            # create or use placeholder
            duration_sec = 0
        else:
            duration = end_time - (test_attempt.start_time or end_time)
            duration_sec = duration.seconds

        # Evaluate answers
        q_ids = [a.question_id for a in payload.answers]
        q_map = {}
        if q_ids:
            res = await session.execute(
                select(Question)
                .options(selectinload(Question.options))
                .where(Question.id.in_(q_ids))
            )
            for q in res.scalars():
                q_map[q.id] = q

        correct_count = 0
        reviews = []

        for item in payload.answers:
            q = q_map.get(item.question_id)
            if not q:
                continue

            if q.has_options:
                correct_opts = [o for o in q.options if o.is_correct]
                correct_ids = [o.id for o in correct_opts]
                selected_ids = item.selected_option_ids or []
                is_correct = set(selected_ids) == set(correct_ids)

                opt_dict = {o.id: o.option_text for o in q.options}
                user_str = ", ".join(opt_dict.get(i, "") for i in selected_ids)
                correct_str = ", ".join(o.option_text for o in correct_opts)
            else:
                expected = (q.answer_text or "").strip()
                user_val = (item.text_answer or "").strip()
                is_correct = user_val.lower() == expected.lower()
                user_str = user_val or "(нет ответа)"
                correct_str = expected

            if is_correct:
                correct_count += 1

            reviews.append(
                QuestionReview(
                    question_id=q.id,
                    text=q.text,
                    has_options=q.has_options,
                    is_correct=is_correct,
                    user_answer=user_str,
                    correct_answer=correct_str,
                )
            )

            if test_attempt:
                att_ans = AttemptAnswer(
                    test_attempt_id=test_attempt.id,
                    question_id=q.id,
                    is_correct=is_correct,
                )
                session.add(att_ans)

        if test_attempt:
            test_attempt.end_time = end_time
            test_attempt.score = correct_count
            await session.commit()

        total = len(payload.answers)
        pct = (correct_count / total * 100) if total > 0 else 0.0

    return QuizFinishResponse(
        test_attempt_id=payload.test_attempt_id,
        score=correct_count,
        total_questions=total,
        percentage=round(pct, 1),
        duration_seconds=duration_sec,
        reviews=reviews,
    )


@router.get("/history")
async def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    offset = (page - 1) * limit
    async with async_session_maker() as session:
        query = (
            select(TestAttempt)
            .where(TestAttempt.user_id == user.id)
            .order_by(TestAttempt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        res = await session.execute(query)
        attempts = list(res.scalars().all())

        count_q = select(func.count(TestAttempt.id)).where(
            TestAttempt.user_id == user.id
        )
        total_count = (await session.execute(count_q)).scalar() or 0

    return {
        "total": total_count,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "end_time": a.end_time.isoformat() if a.end_time else None,
                "score": a.score or 0,
                "total_questions": a.total_questions,
                "percentage": round(
                    ((a.score or 0) / a.total_questions * 100)
                    if a.total_questions > 0
                    else 0,
                    1,
                ),
                "is_completed": a.end_time is not None,
            }
            for a in attempts
        ],
    }


@router.get("/history/{attempt_id}")
async def get_history_detail(
    attempt_id: int,
    user: User = Depends(get_current_user),
):
    async with async_session_maker() as session:
        query = (
            select(TestAttempt)
            .options(
                selectinload(TestAttempt.answers)
                .selectinload(AttemptAnswer.question)
                .selectinload(Question.options)
            )
            .where(TestAttempt.id == attempt_id, TestAttempt.user_id == user.id)
        )
        res = await session.execute(query)
        attempt = res.scalar_one_or_none()
        if not attempt:
            raise HTTPException(status_code=404, detail="Попытка не найдена")

        duration_sec = 0
        if attempt.start_time and attempt.end_time:
            duration_sec = int((attempt.end_time - attempt.start_time).total_seconds())

        answers_out = []
        for ans in attempt.answers:
            q = ans.question
            if not q:
                continue
            correct_opts = (
                [o.option_text for o in q.options if o.is_correct]
                if q.has_options
                else []
            )
            answers_out.append(
                {
                    "question_id": q.id,
                    "text": q.text,
                    "has_options": q.has_options,
                    "is_correct": ans.is_correct,
                    "options": [
                        {
                            "id": o.id,
                            "option_text": o.option_text,
                            "is_correct": o.is_correct,
                        }
                        for o in q.options
                    ],
                    "correct_answer": (
                        ", ".join(correct_opts)
                        if q.has_options
                        else (q.answer_text or "")
                    ),
                }
            )

        total = attempt.total_questions or len(answers_out)
        pct = (
            round(((attempt.score or 0) / total * 100), 1)
            if total > 0
            else 0.0
        )

        return {
            "id": attempt.id,
            "created_at": (
                attempt.created_at.isoformat() if attempt.created_at else None
            ),
            "start_time": (
                attempt.start_time.isoformat() if attempt.start_time else None
            ),
            "end_time": (
                attempt.end_time.isoformat() if attempt.end_time else None
            ),
            "duration_seconds": duration_sec,
            "score": attempt.score or 0,
            "total_questions": total,
            "percentage": pct,
            "answers": answers_out,
        }
