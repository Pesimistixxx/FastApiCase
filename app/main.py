import uvicorn
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from app.auth.router import authRouter
from app.case.router import caseRouter
from app.skin.router import skinRouter


app = FastAPI()
templates = Jinja2Templates(directory='templates')


app.include_router(authRouter)
app.include_router(caseRouter)
app.include_router(skinRouter)


@app.get('/')
async def get_main_page(request: Request):
    return templates.TemplateResponse('main.html', {'request': request})


if __name__ == '__main__':
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)