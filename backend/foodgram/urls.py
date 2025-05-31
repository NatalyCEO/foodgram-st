from django.urls import path
from foodgram.views import recipe_redirect

urlpatterns = [
    path('s/<int:recipe_id>/', recipe_redirect, name='recipe_redirect'),
]