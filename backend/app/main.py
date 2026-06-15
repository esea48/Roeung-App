from fastapi import FastAPI

app = FastAPI(title="Roeung API")


@app.get("/health")
def health():
    return {"status": "ok"}
