from fastapi import APIRouter, Depends, Path, HTTPException, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, desc
import pandas as pd
from sqlalchemy.orm import selectinload

from app.auth.models import User_model
from app.auth.security import get_user
from app.models_associations import User_Skin_model
from app.skin.models import Skin_model
from db.db_depends import get_db
skinRouter = APIRouter(prefix='/skin', tags=['skin'])


@skinRouter.get('/list')
async def get_skin_list(db: Annotated[AsyncSession, Depends(get_db)]):
    skins = await db.scalars(select(Skin_model).where(
        Skin_model.is_active
    ))
    return skins.all()


@skinRouter.post('/sell/all')
async def post_sell_all_skins(db: Annotated[AsyncSession, Depends(get_db)],
                              user: User_model = Depends(get_user)):
    result = await db.scalars(select(User_Skin_model).where(
        User_Skin_model.user_id == user.id,
        User_Skin_model.is_active
    ).options(selectinload(User_Skin_model.skin)))
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='skin not found'
        )
    user_skins = result.all()
    new_balance = user.balance
    total_sold = 0
    sold_cnt = len(user_skins)
    for skin in user_skins:
        skin.is_active = False
        new_balance += skin.skin.price
        total_sold += skin.skin.price

    user.balance = new_balance
    await db.commit()

    return {'status': status.HTTP_200_OK,
            'detail': 'successfully sold',
            'new_balance': new_balance,
            'total_sold': total_sold,
            'sold_count': sold_cnt}


@skinRouter.post('/sell/{id}')
async def post_sell_skin(db: Annotated[AsyncSession, Depends(get_db)],
                         id: int = Path(),
                         user: User_model = Depends(get_user)):
    user_skin = await db.scalar(select(User_Skin_model).where(
        User_Skin_model.id == id,
        User_Skin_model.user_id == user.id,
        User_Skin_model.is_active
    ).options(selectinload(User_Skin_model.skin)))

    if not user_skin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='skin not found'
        )
    new_balance = user.balance + user_skin.skin.price
    user.balance = new_balance
    user_skin.is_active = False
    await db.commit()
    return {
        "detail": "successfully sold",
        "new_balance": new_balance,
    }


@skinRouter.get('/{name}')
async def get_skin(db: Annotated[AsyncSession, Depends(get_db)],
                   name: str = Path()):
    skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active,
        Skin_model.name == name
    ))
    prev_skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active,
        Skin_model.id < skin.id
    ).order_by(desc('id')))
    next_skin = await db.scalar(select(Skin_model).where(
        Skin_model.is_active,
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


async def add_all_skins_to_db(db: AsyncSession):
    df = pd.read_csv('skins_with_filenames.csv')
    for index, row in df.iterrows():
        await db.execute(insert(Skin_model).values(
            name=row['name'],
            quality=row['quality'],
            tag=row['tag'],
            image=row['image']
        ))
    await db.commit()


# @skinRouter.post('/delete_all_skins')
# async def post_delete_all_skins(db: Annotated[AsyncSession, Depends(get_db)]):
#     await db.execute(delete(Skin_model))
#     await db.commit()
#     return "SUCCESS"
