"""add achievements

Revision ID: 3af93e5f02f6
Revises: 4da38f695777
Create Date: 2025-08-11 13:31:47.480454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3af93e5f02f6'
down_revision: Union[str, None] = '4da38f695777'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

achievements_table = sa.Table(
    'achievements',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(255), nullable=False),
    sa.Column('is_active', sa.Boolean, default=True),
    sa.Column('image', sa.String(255), default='default.png'),
    sa.Column('description', sa.String(255))
)


def upgrade() -> None:
    op.bulk_insert(
        achievements_table,
        [
            {
                'name': 'Везунчик',
                'description': 'Успешно выполните апгрейд на 1%',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Неудачник',
                'description': 'Провалите апгрейд на 99%',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Друг админа',
                'description': 'Выиграть 5 баттлов подряд',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Ценитель',
                'description': 'Совершите Апгрейд себе в убыток',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Кейс Джуниор',
                'description': 'Откройте 100 кейсов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Кейс',
                'description': 'Откройте 1000 кейсов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Кейс Де Люкс',
                'description': 'Откройте 10000 кейсов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Биг Кейс',
                'description': 'Откройте 100000 кейсов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Мега Кейс',
                'description': 'Откройте 1000000 кейсов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Рыжий Ап',
                'description': 'Совершите 10 апгрейдов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': '100грейд',
                'description': 'Совершите 100 апгрейдов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Жабгрейдер',
                'description': 'Совершите 1000 апгрейдов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Квартира на 1%',
                'description': 'Совершите 10000 апгрейдов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'ВКонтракте',
                'description': 'Подпишите 10 контрактов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Художник',
                'description': 'Подпишите 100 контрактов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Контрактный душ',
                'description': 'Подпишите 1000 контрактов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Бизнесмен',
                'description': 'Подпишите 10000 контрактов',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Гладиатор',
                'description': 'Поучаствуйте в 10 баттлах',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Самурай',
                'description': 'Поучаствуйте в 100 баттлах',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Воин дракона',
                'description': 'Поучаствуйте в 1000 баттлах',
                'is_active': True,
                'image': 'default.png'
            },
            {
                'name': 'Пользователь @WordleCrackerBot',
                'description': 'В чате с любым человеком написать сегодняшнее слово wordle на английском',
                'is_active': True,
                'image': 'default.png'
            },
        ]
    )


def downgrade() -> None:
    op.execute(
        achievements_table.delete().where(
            achievements_table.c.name.in_(['Везунчик', 'Неудачник', 'Друг админа', 'Ценитель',
                                           'Кейс Джуниор', 'Кейс', 'Кейс Де Люкс', 'Биг Кейс',
                                           'Мега Кейс', 'Рыжий Ап', '100грейд', 'Жабгрейдер',
                                           'Квартира на 1%', 'ВКонтракте', 'Художник', 'Контрактный душ',
                                           'Бизнесмен', 'Гладиатор', 'Самурай', 'Воин дракона',
                                           'Пользователь @WordleCrackerBot'])
        )
    )
