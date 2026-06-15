from fastapi import FastAPI

from app.api import book, keepers, stories

app = FastAPI(title="Roeung API")

app.include_router(stories.router)
app.include_router(keepers.router)
app.include_router(book.router)


@app.get("/health")
def health():
    return {"status": "ok"}
