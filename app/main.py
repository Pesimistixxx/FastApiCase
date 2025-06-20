from fastapi import FastAPI
from app.auth.router import authRouter
from app.case.router import caseRouter
from app.skin.router import skinRouter

app = FastAPI()

app.include_router(authRouter)
app.include_router(caseRouter)
app.include_router(skinRouter)


@app.get('/')
async def home():
    return 0
