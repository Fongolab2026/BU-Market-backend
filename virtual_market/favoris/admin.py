from django.contrib import admin
from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "stars", "created_at")
    list_filter = ("stars", "created_at")
    search_fields = ("user__username", "product__name")