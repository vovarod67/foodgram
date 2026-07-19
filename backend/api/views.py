from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, status
from django.shortcuts import get_object_or_404, redirect
from django.http import HttpResponse
from djoser.views import UserViewSet
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredientAmount,
    Favorite,
    ShoppingCart,
    Subscription,
)
from .serializers import (
    TagSerializer,
    IngredientSerializer,
    RecipeSerializer,
    ShortRecipeSerializer,
    UserSerializer,
    AvatarSerializer,
    SubscriptionSerializer,
)
from .permissions import IsAuthorOrReadOnly


User = get_user_model()


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (permissions.AllowAny(),)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'me'):
            return UserSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=('put', 'delete'),
        url_path='me/avatar',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def avatar(self, request):
        if request.method == 'PUT':
            serializer = AvatarSerializer(request.user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if request.user.avatar:
            request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request):
        users = User.objects.filter(subscribers__user=request.user)
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = SubscriptionSerializer(
                page,
                many=True,
                context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            users,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, *args, **kwargs):
        author = self.get_object()
        subscription = Subscription.objects.filter(
            user=request.user,
            author=author
        )
        if request.method == 'POST':
            if author == request.user:
                return Response(
                    {'errors': 'Невозможно подписаться на себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if subscription.exists():
                return Response(
                    {'errors': 'Подписка уже оформлена.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(
                user=request.user,
                author=author
            )
            serializer = SubscriptionSerializer(
                author,
                context=self.get_serializer_context()
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        if not subscription.exists():
            return Response(
                {'errors': 'Подписка на пользователя не оформлена.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get('name')
        if name:
            queryset = queryset.filter(name__istartswith=name)
        return queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags',
        'recipeingredientamount_set__ingredient',
    )
    serializer_class = RecipeSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        author = self.request.query_params.get('author')
        tags = self.request.query_params.getlist('tags')
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        if author:
            queryset = queryset.filter(author_id=author)
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        if self.request.user.is_authenticated:
            if is_favorited == '1':
                queryset = queryset.filter(
                    in_favorites__user=self.request.user
                )
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(
                    in_shopping_carts__user=self.request.user
                )
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def favorite(self, request, *args, **kwargs):
        recipe = self.get_object()
        favorite = Favorite.objects.filter(user=request.user, recipe=recipe)
        if request.method == 'POST':
            if favorite.exists():
                return Response(
                    {'errors': 'Рецепт уже в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Favorite.objects.create(user=request.user, recipe=recipe)
            serializer = ShortRecipeSerializer(
                recipe,
                context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if not favorite.exists():
            return Response(
                {'errors': 'Рецепт не в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def shopping_cart(self, request, *args, **kwargs):
        recipe = self.get_object()
        cart_item = ShoppingCart.objects.filter(
            user=request.user,
            recipe=recipe
        )
        if request.method == 'POST':
            if cart_item.exists():
                return Response(
                    {'errors': 'Рецепт уже в списке покупок'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            ShoppingCart.objects.create(
                user=request.user,
                recipe=recipe
            )
            serializer = ShortRecipeSerializer(
                recipe,
                context=self.get_serializer_context()
            )
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        if not cart_item.exists():
            return Response(
                {'errors': 'Рецепт не в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        recipe_ingredients = RecipeIngredientAmount.objects.filter(
            recipe__in_shopping_carts__user=request.user
        ).select_related('ingredient')
        shopping_list = {}
        for recipe_ingredient in recipe_ingredients:
            ingredient = recipe_ingredient.ingredient
            ingredient_data = (
                ingredient.name,
                ingredient.measurement_unit
            )
            shopping_list[ingredient_data] = (
                shopping_list.get(ingredient_data, 0)
                + recipe_ingredient.amount
            )
        lines = ['Список покупок:', '']
        for ingredient_data, amount in sorted(shopping_list.items()):
            name, measurement_unit = ingredient_data
            lines.append(f'{name}: {amount} {measurement_unit}')
        response = HttpResponse(
            '\n'.join(lines),
            content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=('get',),
        url_path='get-link'
    )
    def get_short_link(self, request, *args, **kwargs):
        recipe = self.get_object()
        short_link = request.build_absolute_uri(f'/s/{recipe.id}')
        return Response({'short-link': short_link})


def redirect_to_recipe(request, recipe_id):
    get_object_or_404(Recipe, id=recipe_id)
    return redirect(f'/recipes/{recipe_id}')
