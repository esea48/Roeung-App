from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import book, family_members, keepers, stories
from app.core.config import get_settings

app = FastAPI(title="Roeung API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stories.router)
app.include_router(family_members.router)
app.include_router(keepers.router)
app.include_router(book.router)


@app.get("/health")
def health():
    return {"status": "ok"}
