from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.companies.models import CompanyMembership
from apps.core.storage import delete_on_commit

from .models import Project, ProjectMembership


@receiver(post_delete, sender=Project)
def delete_project_cover(sender, instance, **kwargs):
    """Remove a deleted project's cover from storage.

    A signal rather than code in the delete endpoint because projects also
    disappear via cascades (deleting a whole company).
    """
    delete_on_commit(instance.cover)


@receiver(post_delete, sender=CompanyMembership)
def remove_project_memberships(sender, instance, **kwargs):
    """Take a person out of the company's projects when they leave the company.

    A signal because memberships also disappear via cascades (a user or a
    whole company being deleted).
    """
    ProjectMembership.objects.filter(
        user_id=instance.user_id, project__company_id=instance.company_id
    ).delete()
