from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/ping")
async def ping_analytics():
    return {"message": "analytics placeholder"}
