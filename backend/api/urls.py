from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import UserManagementViewSet, RecipeViewSet, IngredientViewSet

router = DefaultRouter()
router.register(r'users', UserManagementViewSet, basename='users')
router.register(r'recipes', RecipeViewSet, basename='recipes')
router.register(r'ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
]
