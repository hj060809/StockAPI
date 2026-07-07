from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import key_router
from shared.shared_lib.config import settings

# sk-dev--X5H-AKr3_pii5IlgaXBiVwP6

# DB 테이블 변경 절차
# models 변경 후 __init__.py에 추가
# alembic -c shared/alembic.ini revision --autogenerate -m "add candles table"
# alembic -c shared/alembic.ini upgrade head

# uvicorn app.main:app --reload

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url='/docs'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(key_router.router, prefix="/api/keys", tags=["keys"])

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok"}
