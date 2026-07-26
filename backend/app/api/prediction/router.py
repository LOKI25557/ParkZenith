from fastapi import APIRouter

router = APIRouter(prefix="/prediction", tags=["prediction"])


@router.get("/ping")
async def ping_prediction():
    return {"message": "prediction placeholder"}
