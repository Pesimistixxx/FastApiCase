from typing import Annotated
from sqlalchemy import select, insert, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, Path, HTTPException, status, Request
from sqlalchemy.orm import selectinload
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates

from app.auth.models import User_model
from app.auth.security import get_user, get_current_user_or_none
from app.models_associations import Case_Skin_model, User_Skin_model
from db.db_depends import get_db
from app.case.models import Case_model
from app.skin.models import Skin_model
from app.case.schemas import CaseCreate, CaseOpen, CaseCalculateProbability
from app.case.probability import get_item_by_probability, calculate_probabilities

caseRouter = APIRouter(prefix='/case', tags=['case'])
templates = Jinja2Templates(directory='templates')


@caseRouter.get('/list')
async def get_case_list(db: Annotated[AsyncSession, Depends(get_db)]):
    cases = await db.scalars(select(Case_model).where(
        Case_model.is_active == True
    ))
    return cases.all()


@caseRouter.get('/create')
async def get_case_create(request: Request,
                          db: Annotated[AsyncSession, Depends(get_db)],
                          user: User_model | None = Depends(get_current_user_or_none)):
    if not user:
        return RedirectResponse('/')

    return templates.TemplateResponse('case_create.html',
                                      {'request': request,
                                       'username': user.username,
                                       'balance': user.balance,
                                       'avatar': user.avatar})


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
async def get_case(request: Request,
                   db: Annotated[AsyncSession, Depends(get_db)],
                   user: User_model | None = Depends(get_current_user_or_none),
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

    last_skins = await db.scalars(
        select(User_Skin_model)
        .where(User_Skin_model.is_active == True)
        .options(selectinload(User_Skin_model.skin))
        .order_by(desc('id'))
        .limit(5)
    )

    result = await db.scalars(
        select(Skin_model)
        .join(Skin_model.cases)
        .where(Case_model.id == case.id, Skin_model.is_active == True)
    )
    skins = result.all()
    if user:
        return templates.TemplateResponse('case_opener.html', {'request': request,
                                                               'user': user,
                                                               'username': user.name,
                                                               'balance': user.balance,
                                                               'skins': skins,
                                                               'case_name': case.name,
                                                               'case_price': case.price,
                                                               'case_image': case.image,
                                                               'last_skins': last_skins})

    return templates.TemplateResponse('case_opener.html', {'request': request,
                                                           'skins': skins,
                                                           'case_name': case.name,
                                                           'case_price': case.price,
                                                           'case_image': case.image,
                                                           'last_skins': last_skins})


@caseRouter.post('/{name}')
async def post_open_case(db: Annotated[AsyncSession, Depends(get_db)],
                         num_cases: CaseOpen,
                         name: str = Path(),
                         user: User_model = Depends(get_user)
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
    new_balance = user.balance - (case.price * num_cases.cnt)
    user.balance = new_balance

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

    user_skin_ids = []

    for skin in dropped_items:
        result = await db.execute(
            insert(User_Skin_model)
            .values(user_id=user.id, skin_id=skin.id)
            .returning(User_Skin_model.id)
        )
        user_skin_id = result.scalar_one()
        user_skin_ids.append(user_skin_id)

    result_items = []
    for i, skin in enumerate(dropped_items):
        result_items.append({
            "id": user_skin_ids[i],
            "name": skin.name,
            "price": str(skin.price),
            "image": skin.image,
        })
    await db.commit()

    return {'new_balance': new_balance,
            'skins': result_items}


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
