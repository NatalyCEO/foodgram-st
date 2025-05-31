from foodgram.models import Recipe
from django.http import Http404
from django.shortcuts import redirect



def recipe_redirect(request, recipe_id):
    if not Recipe.objects.filter(id=recipe_id).exists():
        raise Http404(f"Рецепта с ID={recipe_id} не существует")
    return redirect(f'/recipes/{recipe_id}')
