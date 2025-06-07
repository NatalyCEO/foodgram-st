from django.urls import path
from foodgram.views import recipe_redirect

app_name = 'foodgram'

urlpatterns = [
    path('s/<int:recipe_id>/', recipe_redirect, name='recipe_redirect'),
]