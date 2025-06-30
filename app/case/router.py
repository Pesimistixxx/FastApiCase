from typing import Annotated
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, HTTPException, status

from app.auth.models import User_model
from app.auth.security import get_user
from app.models_associations import case_skin_association, User_Skin_model
from db.db_depends import get_db
from app.case.models import Case_model
from app.skin.models import Skin_model
from app.case.schemas import CaseCreate, CaseOpen
from app.case.probability import get_item_by_probability

caseRouter = APIRouter(prefix='/case', tags=['case'])


@caseRouter.get('/list')
async def get_case_list(db: Annotated[AsyncSession, Depends(get_db)]):
    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active == True
    ))
    return cases.all()


@caseRouter.post('/create_case')
async def post_create_case(db: Annotated[AsyncSession, Depends(get_db)],
                           case_inp: CaseCreate):
    new_case = Case_model(name=case_inp.name,
                          price=case_inp.price,
                          math_exception=case_inp.math_exception,
                          sigma=case_inp.sigma,
                          image=case_inp.image)
    db.add(new_case)
    await db.flush()

    for skin_id in case_inp.skins:
        await db.execute(insert(case_skin_association).values(
            case_id=new_case.id,
            skin_id=skin_id
        ))

    await db.commit()

    return {'status': status.HTTP_201_CREATED,
            'detail': 'created'}


@caseRouter.delete('/{name}')
async def delete_case(db: Annotated[AsyncSession, Depends(get_db)],
                      name: str = Path()):
    case = await db.scalar(select(Case_model).where(
        Case_model.is_active == True,
        Case_model.name == name
    ))
    case.is_active = False
    await db.commit()

    return {'status': status.HTTP_200_OK,
            'detail': 'case was deleted'}


@caseRouter.get('/{name}')
async def get_case(db: Annotated[AsyncSession, Depends(get_db)],
                   name: str = Path()):

    case = await db.scalar(select(Case_model).where(
        Case_model.is_active == True,
        Case_model.name == name
    ))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Case not found'
        )

    result = await db.execute(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id, Skin_model.is_active == True)
    )
    skins = result.scalars().all()

    return skins


@caseRouter.post('/{name}')
async def post_open_case(db: Annotated[AsyncSession, Depends(get_db)],
                         num_cases: CaseOpen,
                         name: str = Path(),
                         user: User_model = Depends(get_user),
                         ):

    case = await db.scalar(select(Case_model).where(
        Case_model.is_active == True,
        Case_model.name == name
    ))

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Case not found'
        )

    if user.balance < (case.price * num_cases.cnt):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Not enough money'
        )
    user.balance = user.balance - (case.price * num_cases.cnt)

    result = await db.execute(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id,
               Skin_model.is_active == True))
    skins = result.scalars().all()

    dropped_items = get_item_by_probability(skins,
                                            case.sigma,
                                            case.math_exception,
                                            num_cases.cnt)

    result_items = [
        {
            "id": skin.id,
            "name": skin.name,
            "price": skin.price,
            "image": skin.image,
        }
        for skin in dropped_items
    ]
    for skin in dropped_items:
        await db.execute(insert(User_Skin_model).values(
            user_id = user.id,
            skin_id = skin.id
        ))

    await db.commit()

    return result_items
