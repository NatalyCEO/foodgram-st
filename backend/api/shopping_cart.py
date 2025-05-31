from foodgram.models import User, Recipe
from django.http import HttpResponse
from typing import Any, Dict, List, Optional, TextIO
from django.db.models import QuerySet




def render_shopping_cart(
        user: User,
        ingredients: QuerySet,
        recipes: QuerySet
) -> HttpResponse:
    from  io import StringIO
    buffer = StringIO

    buffer.write(f'Список покупок для {user.get_full_name()}\n\n')

    buffer.write('Ингредиенты:\n')
    for ingredient in ingredients:
        buffer.write(
            f'• {ingredient["ingredient__name"]} - '
            f'{ingredient["total_amount"]}'
            f'{ingredient["ingredient_measurtment_unit"]}\n'
        )

    buffer.write('\nРецепты:\n')
    for recipe in recipes:
        buffer.write(f'• {recipe.name}\n')

    buffer.write('\nПриятного аппетита!')

    buffer.seek(0)

    return HttpResponse(
        buffer.getvalue(),
        content_type='text/plain; charset=utf-8'
    )