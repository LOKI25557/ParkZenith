from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/ping")
async def ping_auth():
    return {"message": "auth placeholder"}
