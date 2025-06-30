from fastapi import APIRouter, Depends, Path, HTTPException, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete, desc
import pandas as pd

from app.skin.models import Skin_model
from db.db_depends import get_db
skinRouter = APIRouter(prefix='/skin', tags=['skin'])


@skinRouter.get('/list')
async def get_skin_list(db: Annotated[AsyncSession, Depends(get_db)]):
    skins = await db.scalars(select(Skin_model).where(
        Skin_model.is_active == True
    ))
    return skins.all()


@skinRouter.get('/{name}')
async def get_skin(db: Annotated[AsyncSession, Depends(get_db)],
                   name: str = Path()):
    skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active == True,
        Skin_model.name == name
    ))
    prev_skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active == True,
        Skin_model.id < skin.id
    ).order_by(desc('id')))
    next_skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active == True,
        Skin_model.id > skin.id
    ).order_by('id'))
    if not skin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Skin not found'
        )
    return {'prev_skin': prev_skin,
            'current_skin': skin,
            'next_skin': next_skin}


@skinRouter.post('/add_all_skins')
async def post_add_all_skins(db: Annotated[AsyncSession, Depends(get_db)]):
    df = pd.read_csv('skins_with_filenames.csv')
    for index, row in df.iterrows():
        await db.execute(insert(Skin_model).values(
            name=row['name'],
            quality=row['quality'],
            tag=row['tag'],
            image=row['image']
        ))
    await db.commit()
    return "SUCCESS"


@skinRouter.post('/delete_all_skins')
async def post_delete_all_skins(db: Annotated[AsyncSession, Depends(get_db)]):
    await db.execute(delete(Skin_model))
    await db.commit()
    return "SUCCESS"
