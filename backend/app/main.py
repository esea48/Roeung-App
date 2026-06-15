from fastapi import FastAPI

from app.api import stories

app = FastAPI(title="Roeung API")

app.include_router(stories.router)


@app.get("/health")
def health():
    return {"status": "ok"}
