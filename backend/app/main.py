from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.embedding_client import EmbeddingError
from app.services.llm_client import LLMError
from app.routers import (
    auth,
    dashboard,
    evaluate,
    explain,
    gap_report,
    plan,
    quiz,
    syllabi,
    topics,
    upload,
)

settings = get_settings()

app = FastAPI(title="GapFinder AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.exception_handler(LLMError)
@app.exception_handler(EmbeddingError)
async def ai_provider_error(_: Request, exc: Exception) -> JSONResponse:
    """AI-provider problems (quota, key, outage) -> a readable 503, not a bare 500."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(topics.router)
app.include_router(syllabi.router)
app.include_router(quiz.router)
app.include_router(evaluate.router)
app.include_router(gap_report.router)
app.include_router(plan.router)
app.include_router(explain.router)
app.include_router(dashboard.router)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "GapFinder AI API",
        "status": "running",
        "app": "Open the website at http://localhost:3000",
        "api_docs": "/docs",
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
