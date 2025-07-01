import asyncio
import threading

import uvicorn
from fastapi import FastAPI
from app.auth.router import authRouter
from app.case.router import caseRouter
from app.skin.router import skinRouter

from db_cleaner.db_cleaner import db_cleaner_scheduler
from price_tracker.price_tracker import price_tracker_scheduler

app = FastAPI()

app.include_router(authRouter)
app.include_router(caseRouter)
app.include_router(skinRouter)


@app.get('/')
async def home():
    return 0


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)