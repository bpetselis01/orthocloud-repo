from fastapi import FastAPI

from app.routes import structures, segment

app = FastAPI(title="OrthoCloud API")

app.include_router(structures.router)
app.include_router(segment.router)


@app.get("/health")
def health():
    return {"status": "ok"}
