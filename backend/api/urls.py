from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import UserManagementViewSet, RecipeViewSet, IngredientViewSet

router = DefaultRouter()
router.register('users', UserManagementViewSet, basename='users')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
