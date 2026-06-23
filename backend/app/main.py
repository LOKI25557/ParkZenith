from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .api.router import api_router
from .database.session import engine

app = FastAPI(title="ParkZenith API", debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    # place for startup tasks (migrations, connections, caches)
    pass


@app.on_event("shutdown")
async def shutdown_event():
    # cleanup tasks
    await engine.dispose()


@app.get("/", tags=["health"])
async def health_check():
    return {"message": "ParkZenith API Running"}


# Include API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
