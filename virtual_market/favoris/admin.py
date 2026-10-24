from django.contrib import admin
from .models import Favorite, Review, ReviewReport


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "product__name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "stars", "status", "created_at")
    list_filter = ("stars", "status", "created_at")
    search_fields = ("user__username", "product__name", "comment")


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ("id", "review", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("review__product__name", "user__username")
