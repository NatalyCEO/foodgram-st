from foodgram.models import Recipe
from django_filters import rest_framework as filters
from django.db.models import QuerySet



class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ('author','is_favorited','is_in_shopping_cart')
    
    def filter_is_favorited(
            self,
            queryset: QuerySet,
            name: str,
            value: bool
    ) -> QuerySet:
        if value and self.request.user.is_authenticated:
            return queryset.filter(favorites__user=self.request.user)
        return queryset
    
    def filter_is_in_shopping_cart(
            self,
            queryset: QuerySet,
            name: str,
            value: bool,
    ) -> QuerySet:
        if value and self.request.user.is_authenticated:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset