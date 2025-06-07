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
    response, decorators
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
        methods=['get'],
        url_path='me',
        permission_classes=[permissions.IsAuthenticated]
    )
    def me(self, request: Any) -> Response:
        try:
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )

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
                return Response(
                    {'error': 'Avatar data is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                format, imgstr = data.split(';base64,')
            except ValueError:
                return Response(
                    {'error': 'Invalid avatar format'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ext = format.split('/')[-1]
            if ext not in ['jpeg', 'jpg', 'png']:
                return Response(
                    {'error': 'Invalid file format. Only jpeg, jpg, and png are allowed'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file = ContentFile(
                base64.b64decode(imgstr),
                name=f'avatar{user.id}.{ext}'
            )
            user.avatar = file
            user.save()
            return Response({'avatar': user.avatar.url})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @avatar.mapping.delete
    def delete_avatar(self, request: Any) -> Response:
        try:
            user = request.user
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
                user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request: Any, id: Optional[int] = None) -> Response:
        author = get_object_or_404(User, id=id)
        
        try:
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
            
            context = {'request': request}
            return Response(
                RecipesUserSerializer(
                    author,
                    context=context
                ).data,
                status=status.HTTP_201_CREATED
            )
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @subscribe.mapping.delete
    def unsubscribe(self, request: Any, id: Optional[int] = None) -> Response:
        try:
            author = get_object_or_404(User, pk=id)
        except Http404:
            return Response(
                {'error': _('Author not found.')},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            subscription = get_object_or_404(
                Subscription,
                user=request.user,
                author=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(
                {'error': _('You are not subscribed to this author.')},
                status=status.HTTP_400_BAD_REQUEST
            )
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
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Recipe.objects.all()
        return queryset.select_related('author').prefetch_related(
            'ingredients',
            'tags',
            'recipe_ingredients',
            'recipe_ingredients__ingredient'
        )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            
            if instance.author != request.user:
                return Response(
                    {'detail': 'You do not have permission to update this recipe'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            
            instance = self.get_queryset().get(id=instance.id)
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer: Any) -> None:
        serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @staticmethod
    def handle_recipe(
        model: Any,
        user: User,
        recipe_id: int,
        add: bool = True
    ) -> Response:
        try:
            if not Recipe.objects.filter(pk=recipe_id).exists():
                return Response(
                    {'detail': 'Recipe not found.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            recipe = Recipe.objects.get(pk=recipe_id)

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

            obj = model.objects.filter(user=user, recipe=recipe).first()
            if not obj:
                return Response(
                    {'detail': 'Recipe not in collection.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except serializers.ValidationError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication credentials were not provided.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return self.handle_recipe(Favorite, request.user, pk, True)

    @favorite.mapping.delete
    def remove_favorite(self, request: Any, pk: Optional[int] = None) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication credentials were not provided.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return self.handle_recipe(Favorite, request.user, pk, False)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request: Any, pk: Optional[int] = None) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication credentials were not provided.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        return self.handle_recipe(ShoppingCart, request.user, pk, True)

    @shopping_cart.mapping.delete
    def remove_shopping_cart(
        self,
        request: Any,
        pk: Optional[int] = None
    ) -> Response:
        if not request.user.is_authenticated:
            return Response(
                {'detail': 'Authentication credentials were not provided.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
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
        except Http404:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.author != request.user:
                return Response(
                    {'detail': 'You do not have permission to delete this recipe.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(
                {'detail': 'Not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self) -> Any:
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)