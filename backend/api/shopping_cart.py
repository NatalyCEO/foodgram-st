from typing import Any, Dict, List
from django.contrib.auth import get_user_model
from django.db.models.query import QuerySet
from io import StringIO

User = get_user_model()

def render_shopping_cart(
    user: User,
    ingredients: QuerySet,
    recipes: QuerySet
) -> StringIO:
    shopping_list = StringIO()
    
    shopping_list.write("Список покупок:\n\n")
    
    for item in ingredients:
        shopping_list.write(
            f"- {item['ingredient__name']} "
            f"({item['ingredient__measurement_unit']}) — "
            f"{item['total_amount']}\n"
        )
    
    if recipes:
        shopping_list.write("\nРецепты в списке покупок:\n")
        for recipe in recipes:
            shopping_list.write(f"- {recipe.name}\n")
    
    shopping_list.seek(0)
    return shopping_list 