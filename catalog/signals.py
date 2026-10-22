from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import ProductImage


@receiver(post_delete, sender=ProductImage)
def delete_image_files(sender, instance, **kwargs):
    for field_file in (instance.image, instance.thumb):
        if field_file:
            field_file.delete(save=False)