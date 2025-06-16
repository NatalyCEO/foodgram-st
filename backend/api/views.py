from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.urls import reverse
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import (
    viewsets, status, permissions, serializers,
    response, decorators, filters
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
import base64

from foodgram.models import (
    User, Ingredient, Recipe,
    Favorite, ShoppingCart, Subscription,
    RecipeIngredient
)
from api.serializers import (
    UserProfileSerializer,
    IngredientSerializer,
    RecipeSerializer,
    SubscriptionRecipeSerializer,
    RecipesUserSerializer,
    AvatarSerializer,
    SubscriptionSerializer,
    RecipeCollectionSerializer
)
from api.pagination import PageLimitPagination
from api.filters import RecipeFilter
from api.permissions import IsOwnerOrReadOnly
from api.shopping_cart import render_shopping_cart
from djoser.views import UserViewSet


class BaseModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = PageLimitPagination

    def handle_error(self, error: Exception) -> Response:
        if isinstance(error, (ValidationError, serializers.ValidationError)):
            return Response(
                {'error': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'error': str(error)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class UserManagementViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.AllowAny]

    @action(
        detail=False,
        methods=['get'],
        url_path='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request: Any) -> Response:
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request: Any) -> Response:
        serializer = AvatarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.avatar = serializer.validated_data['avatar']
        user.save()
        return Response({'avatar': user.avatar.url})

    @avatar.mapping.delete
    def delete_avatar(self, request: Any) -> Response:
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request: Any, id: Optional[int] = None) -> Response:
        author = get_object_or_404(User, id=id)
        serializer = SubscriptionSerializer(data={
            'user': request.user.id,
            'author': author.id
        })
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            RecipesUserSerializer(
                author,
                context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def unsubscribe(self, request: Any, id: Optional[int] = None) -> Response:
        author = get_object_or_404(User, pk=id)
        serializer = SubscriptionSerializer(
            data={'user': request.user.id, 'author': author.id}
        )
        try:
            serializer.delete(request.user, author)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except serializers.ValidationError as e:
            return Response(
                {'detail': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscriptions(self, request: Any) -> Response:
        try:
            subscriptions = Subscription.objects.filter(
                user=request.user
            ).select_related('author')

            queryset = [sub.author for sub in subscriptions]
            page = self.paginate_queryset(queryset)
            
            context = {'request': request}
            return self.get_paginated_response(
                RecipesUserSerializer(
                    page,
                    many=True,
                    context=context
                ).data
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RecipeViewSet(BaseModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = PageLimitPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [IsOwnerOrReadOnly]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsOwnerOrReadOnly()]
        if self.action in ['shopping_cart', 'favorite'] or (
            self.action in ['remove_favorite'] and self.request.method == 'DELETE'
        ):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Recipe.objects.all()
        return queryset.select_related('author').prefetch_related(
            'ingredients',
            'recipe_ingredients',
            'recipe_ingredients__ingredient'
        )

    def _handle_collection_action(self, model, request, pk, add):
        if request.method == 'POST':
            add = True
        elif request.method == 'DELETE':
            add = False
        
        return self.handle_recipe(model, request.user, pk, add)

    @staticmethod
    def handle_recipe(
        model: Any,
        user: User,
        recipe_id: int,
        add: bool = True
    ) -> Response:
        recipe = get_object_or_404(Recipe, pk=recipe_id)

        serializer = RecipeCollectionSerializer(
            data={'user': user.id, 'recipe': recipe_id},
            context={'collection_model': model, 'action': 'delete' if not add else None}
        )
        serializer.is_valid(raise_exception=True)

        if add:
            serializer.save()
            return Response(
                SubscriptionRecipeSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )

        serializer.delete(serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        return self._handle_collection_action(Favorite, request, pk, add=True)

    @favorite.mapping.delete
    def remove_favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        return self._handle_collection_action(Favorite, request, pk, add=False)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request: Any, pk: Optional[int] = None) -> Response:
        return self._handle_collection_action(ShoppingCart, request, pk, add=request.method == 'POST')

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request: Any) -> FileResponse:
        try:
            user = request.user
            ingredients = (
                RecipeIngredient.objects
                .filter(recipe__shopping_carts__user=user)
                .values('ingredient__name', 'ingredient__measurement_unit')
                .annotate(total_amount=Sum('amount'))
                .order_by('ingredient__name')
            )

            recipes = Recipe.objects.filter(shopping_carts__user=user)
            shopping_cart_text = render_shopping_cart(
                user,
                ingredients,
                recipes
            )

            response = HttpResponse(
                shopping_cart_text.getvalue(),
                content_type='text/plain; charset=utf-8'
            )
            response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
            return response

        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link',
        permission_classes=[permissions.AllowAny]
    )
    def get_link(self, request: Any, pk: Optional[int] = None) -> Response:
        try:
            recipe = self.get_object()
            url = request.build_absolute_uri(f'/s/{recipe.pk}/')
            return Response({'short-link': url}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            return queryset.filter(name__istartswith=name)
        return queryset
