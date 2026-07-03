from fastapi import APIRouter

router = APIRouter(prefix="/parking", tags=["parking"])


@router.get("/ping")
async def ping_parking():
    return {"message": "parking placeholder"}
