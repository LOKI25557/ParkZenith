from fastapi import APIRouter

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.get("/ping")
async def ping_reservation():
    return {"message": "reservation placeholder"}
