from fastapi import APIRouter

from app.api.companies import router as companies_router
from app.api.comparisons import router as comparisons_router
from app.api.imports import router as imports_router

api_router = APIRouter()


@api_router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(imports_router)
api_router.include_router(companies_router)
api_router.include_router(comparisons_router)
