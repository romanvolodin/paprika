from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.companies.models import Company

from .defaults import create_default_roles


@receiver(post_save, sender=Company)
def seed_default_roles(sender, instance, created, raw=False, **kwargs):
    """Give every new company the starter set of roles."""
    if raw or not created:
        return
    create_default_roles(instance)
