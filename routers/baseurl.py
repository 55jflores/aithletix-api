from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check():
    return {"status": "Base URL ok", "app": "AthleteIQ API v1"}
