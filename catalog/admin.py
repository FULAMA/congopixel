from django.contrib import admin

from .models import Category, PixelModel, Product, ProductImage, ProductVariant


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_usd", "is_active", "is_featured")
    list_filter = ("category", "is_active", "is_featured", "compatible_models")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("compatible_models",)
    inlines = [ProductImageInline, ProductVariantInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PixelModel)
class PixelModelAdmin(admin.ModelAdmin):
    list_display = ("name", "release_year", "is_active")
    prepopulated_fields = {"slug": ("name",)}