from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from catalog.models import Category, Product


class StaticSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ["catalog:home", "catalog:product_list", "core:shipping_returns", "core:terms", "core:about"]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, obj):
        return reverse("catalog:category", args=[obj.slug])


class ProductSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"

    def items(self):
        return Product.objects.filter(is_active=True, category__is_active=True)

    def location(self, obj):
        return reverse("catalog:product_detail", args=[obj.slug])

    def lastmod(self, obj):
        return obj.updated_at


SITEMAPS = {"static": StaticSitemap, "categories": CategorySitemap, "products": ProductSitemap}