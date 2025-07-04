from typing import Annotated
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, HTTPException, status

from app.auth.models import User_model
from app.auth.security import get_user
from app.models_associations import Case_Skin_model, User_Skin_model
from db.db_depends import get_db
from app.case.models import Case_model
from app.skin.models import Skin_model
from app.case.schemas import CaseCreate, CaseOpen, CaseCalculateProbability
from app.case.probability import get_item_by_probability, calculate_probabilities

caseRouter = APIRouter(prefix='/case', tags=['case'])


@caseRouter.get('/list')
async def get_case_list(db: Annotated[AsyncSession, Depends(get_db)]):
    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active == True
    ))
    return cases.all()


@caseRouter.post('/calculate_probability')
async def post_calculate_probability(db: Annotated[AsyncSession, Depends(get_db)],
                                     case_inp: CaseCalculateProbability):
    result = await db.scalars(select(Skin_model).where(
        Skin_model.id.in_(case_inp.skins)
    ))
    skins = result.all()

    probabilities = calculate_probabilities(skins,
                                            case_inp.sigma,
                                            case_inp.math_exception)

    mo = sum(skin.price * probability for skin, probability in zip(skins, probabilities))

    return {f'Средняя цена дропа {mo:.2f}, Оптимальная цена для кейса {mo * 0.9:.0f} - {mo * 1.1:.0f}'}


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
        await db.execute(insert(Case_Skin_model).values(
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


@caseRouter.get('/skin_case')
async def get_skin_case(db: Annotated[AsyncSession, Depends(get_db)]):
    skin_case = await db.scalars(select(Case_Skin_model))

    return skin_case.all()


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

    result = await db.scalars(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id, Skin_model.is_active == True)
    )
    skins = result.all()

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

    result = await db.scalars(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id,
               Skin_model.is_active == True))
    skins = result.all()

    """
    Функцию get_item_by_probability не имеет смысла эвэйтить там нет
    ни одного места которое могло бы выполняться асинхронно(only CPU)
    """
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
            user_id=user.id,
            skin_id=skin.id
        ))

    await db.commit()

    return result_items


@caseRouter.get('/{name}/chances')
async def get_case_chances(db: Annotated[AsyncSession, Depends(get_db)],
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

    result = await db.scalars(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id,
               Skin_model.is_active == True))
    skins = result.all()

    probabilities = calculate_probabilities(skins,
                                            case.sigma,
                                            case.math_exception)
    skin_probability = {}
    for i, skin in enumerate(skins):
        skin_probability[skin.name] = f'{probabilities[i] * 100:.2f}%'

    return skin_probability
