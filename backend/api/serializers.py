from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from drf_extra_fields.fields import Base64ImageField

from recipes.models import (
    Tag,
    Ingredient,
    RecipeIngredientAmount,
    Recipe,
    Favorite,
    ShoppingCart,
    Subscription,
)


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')

        return (
            request is not None
            and request.user.is_authenticated
            and obj.subscribers.filter(user=request.user).exists()
        )


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug',
        )


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit',
        )


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class FavoriteSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = Favorite
        fields = (
            'user',
            'recipe',
        )

    def validate(self, attrs):
        if Favorite.objects.filter(
            user=attrs['user'],
            recipe=attrs['recipe'],
        ).exists():
            raise serializers.ValidationError(
                {'errors': 'Рецепт уже в избранном.'}
            )
        return attrs

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context,
        ).data


class ShoppingCartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    class Meta:
        model = ShoppingCart
        fields = (
            'user',
            'recipe',
        )

    def validate(self, attrs):
        if ShoppingCart.objects.filter(
            user=attrs['user'],
            recipe=attrs['recipe'],
        ).exists():
            raise serializers.ValidationError(
                {'errors': 'Рецепт уже в списке покупок.'}
            )
        return attrs

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = RecipeIngredientAmount
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount',
        )


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient',
    )

    class Meta:
        model = RecipeIngredientAmount
        fields = (
            'id',
            'amount',
        )


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(
        many=True,
        read_only=True,
    )
    ingredients = RecipeIngredientReadSerializer(
        source='recipeingredientamount_set',
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        return (
            request is not None
            and request.user.is_authenticated
            and Favorite.objects.filter(user=request.user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        return (
            request is not None
            and request.user.is_authenticated
            and ShoppingCart.objects.filter(
                user=request.user,
                recipe=obj,
            ).exists()
        )


class RecipeSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientWriteSerializer(
        source='recipeingredientamount_set',
        many=True,
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'tags',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def validate(self, attrs):
        errors = {}
        tags = attrs.get('tags')
        if not tags:
            errors['tags'] = (
                'Теги нужно указать при создании или изменении рецепта.'
            )
        else:
            tag_ids = [tag.id for tag in tags]
            if len(tag_ids) != len(set(tag_ids)):
                errors['tags'] = 'Один тег указан несколько раз.'
        ingredients = attrs.get('recipeingredientamount_set')
        if not ingredients:
            errors['ingredients'] = (
                'Ингредиенты нужно указать при создании или изменении рецепта.'
            )
        else:
            ingredient_ids = [item['ingredient'].id for item in ingredients]
            if len(ingredient_ids) != len(set(ingredient_ids)):
                errors['ingredients'] = 'Один ингредиент указан несколько раз.'
        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError(
                'Поле изображения не должно быть пустым.'
            )
        return image

    @staticmethod
    def add_ingredients(recipe, ingredients):
        for ingredient_data in ingredients:
            RecipeIngredientAmount.objects.create(
                recipe=recipe,
                **ingredient_data,
            )

    @transaction.atomic
    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipeingredientamount_set')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )
        recipe.tags.set(tags)
        self.add_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipeingredientamount_set')
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.recipeingredientamount_set.all().delete()
        self.add_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context=self.context,
        ).data


class SubscriptionSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        recipes = obj.recipes.all()
        request = self.context.get('request')
        if request is not None:
            recipes_limit = request.query_params.get('recipes_limit')
            if (
                recipes_limit
                and recipes_limit.isdigit()
                and int(recipes_limit) > 0
            ):
                recipes = recipes[:int(recipes_limit)]
        return ShortRecipeSerializer(
            recipes,
            many=True,
            context=self.context,
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscription
        fields = (
            'user',
            'author',
        )

    def validate(self, attrs):
        user = attrs['user']
        author = attrs['author']
        if user == author:
            raise serializers.ValidationError(
                {'errors': 'Невозможно подписаться на себя.'}
            )
        if Subscription.objects.filter(
            user=user,
            author=author,
        ).exists():
            raise serializers.ValidationError(
                {'errors': 'Подписка уже оформлена.'}
            )
        return attrs

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance.author,
            context=self.context,
        ).data
