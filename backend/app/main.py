from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth, users, stats, platforms, questions, roadmap, sheet, insights

app = FastAPI(title="AlgoSweeped API", version="1.0.0", docs_url="/docs")

s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(stats.router)
app.include_router(platforms.router)
app.include_router(questions.router)
app.include_router(roadmap.router)
app.include_router(sheet.router)
app.include_router(insights.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
