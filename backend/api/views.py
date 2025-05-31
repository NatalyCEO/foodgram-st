from typing import Any, Dict, List, Optional
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.urls import reverse
from django.core.files.base import ContentFile
from django.http import FileResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import (
    viewsets, status, permissions, serializers,
    response, decorators
)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

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
    RecipesUserSerializer
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
        if isinstance(error, ValidationError):
            return Response(
                {'error': str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )
        if isinstance(error, serializers.ValidationError):
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
        methods=['put'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request: Any) -> Response:
        try:
            user = request.user
            data = request.data.get('avatar')

            if not data:
                raise ValidationError(_('Avatar data is required'))

            try:
                format, imgstr = data.split(';base64,')
            except ValueError:
                raise ValidationError(_('Invalid avatar format'))

            ext = format.split('/')[-1]
            file = ContentFile(
                base64.b64decode(imgstr),
                name=f'avatar{user.id}.{ext}'
            )
            user.avatar = file
            user.save()
            return Response({'avatar': user.avatar.url})
        except Exception as e:
            return self.handle_error(e)

    @avatar.mapping.delete
    def delete_avatar(self, request: Any) -> Response:
        try:
            user = request.user
            if user.avatar and user.avatar.name != 'users/default_avatar.jpg':
                user.avatar.delete(save=False)
                user.avatar = 'users/default_avatar.jpg'
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_error(e)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request: Any, id: Optional[int] = None) -> Response:
        try:
            author = get_object_or_404(User, pk=id)
            if request.user == author:
                raise serializers.ValidationError(
                    _("You cannot subscribe to yourself")
                )
            _, created = Subscription.objects.get_or_create(
                user=request.user,
                author=author
            )
            if not created:
                raise serializers.ValidationError(
                    _("You are already subscribed to this user")
                )
            return Response(
                RecipesUserSerializer(
                    author,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return self.handle_error(e)

    @subscribe.mapping.delete
    def unsubscribe(self, request: Any, id: Optional[int] = None) -> Response:
        try:
            subscription = get_object_or_404(
                Subscription,
                user=request.user,
                author_id=id
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return self.handle_error(e)

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
            return self.get_paginated_response(
                RecipesUserSerializer(
                    page,
                    many=True,
                    context={'request': request}
                ).data
            )
        except Exception as e:
            return self.handle_error(e)


class RecipeViewSet(BaseModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    permission_classes = [
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly
    ]

    def perform_create(self, serializer: Any) -> None:
        serializer.save(author=self.request.user)

    @staticmethod
    def handle_recipe(
        model: Any,
        user: User,
        recipe_id: int,
        add: bool = True
    ) -> Response:
        try:
            recipe = get_object_or_404(Recipe, pk=recipe_id)

            if add:
                _, created = model.objects.get_or_create(
                    user=user,
                    recipe=recipe
                )
                if not created:
                    raise serializers.ValidationError(
                        _('Recipe is already in collection')
                    )
                return Response(
                    SubscriptionRecipeSerializer(recipe).data,
                    status=status.HTTP_201_CREATED
                )

            get_object_or_404(model, user=user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        return self.handle_recipe(Favorite, request.user, pk, True)

    @favorite.mapping.delete
    def remove_favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        return self.handle_recipe(Favorite, request.user, pk, False)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request: Any, pk: Optional[int] = None) -> Response:
        return self.handle_recipe(ShoppingCart, request.user, pk, True)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(
        self,
        request: Any,
        pk: Optional[int] = None
    ) -> Response:
        return self.handle_recipe(ShoppingCart, request.user, pk, False)

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

            return FileResponse(
                shopping_cart_text,
                as_attachment=True,
                filename='shopping_list.txt',
                content_type='text/plain'
            )
        except Exception as e:
            return self.handle_error(e)

    @action(
        detail=True,
        methods=['get'],
        url_path='get-link'
    )
    def get_link(self, request: Any, pk: Optional[int] = None) -> Response:
        try:
            if not Recipe.objects.filter(pk=pk).exists():
                return Response(
                    {'error': _('Recipe not found')},
                    status=status.HTTP_404_NOT_FOUND
                )
            return Response(
                {
                    'short-link': request.build_absolute_uri(
                        reverse('recipe_redirect', args=[pk])
                    )
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return self.handle_error(e)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    search_fields = ('^name',)

    def get_queryset(self) -> Any:
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset