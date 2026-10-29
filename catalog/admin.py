from django.contrib import admin
from django.db.models import Exists, F, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from .models import Category, PixelModel, Product, ProductImage, ProductVariant

class StockFilter(admin.SimpleListFilter):
    title = "stock"
    parameter_name = "stock"

    def lookups(self, request, model_admin):
        return [("low", "Stock bas"), ("out", "Épuisé")]

    def queryset(self, request, queryset):
        if self.value() == "out":
            return queryset.filter(total_stock=0)
        if self.value() == "low":
            return queryset.filter(has_low_stock=True)
        return queryset


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    fields = ("name", "sku", "price_usd", "stock", "low_stock_threshold", "is_active")
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_usd", "stock_total", "is_active", "is_featured")
    list_filter = (StockFilter, "category", "is_active", "is_featured", "compatible_models")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("compatible_models",)
    inlines = [ProductImageInline, ProductVariantInline]

    def get_queryset(self, request):
        stock = (
            ProductVariant.objects.filter(product=OuterRef("pk"), is_active=True)
            .values("product")
            .annotate(total=Sum("stock"))
            .values("total")
        )
        low_stock = ProductVariant.objects.filter(
            product=OuterRef("pk"),
            is_active=True,
            stock__gt=0,
            stock__lte=F("low_stock_threshold"),
        )
        return super().get_queryset(request).annotate(
            total_stock=Coalesce(Subquery(stock, output_field=IntegerField()), 0),
            has_low_stock=Exists(low_stock),
        )

    @admin.display(description="Stock", ordering="total_stock")
    def stock_total(self, obj):
        if obj.total_stock == 0:
            return format_html('<b style="color:#B91C1C">{}</b>', "Épuisé")
        if obj.has_low_stock:
            return format_html('<b style="color:#B45309">{} (bas)</b>', obj.total_stock)
        return obj.total_stock


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "position", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PixelModel)
class PixelModelAdmin(admin.ModelAdmin):
    list_display = ("name", "release_year", "is_active")
    prepopulated_fields = {"slug": ("name",)}