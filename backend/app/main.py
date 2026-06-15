from fastapi import FastAPI

from app.api import keepers, stories

app = FastAPI(title="Roeung API")

app.include_router(stories.router)
app.include_router(keepers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
