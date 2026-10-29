from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.storage import USERS_DIR, file_with_token

from .managers import UserManager
from .validators import AVATAR_ALLOWED_EXTENSIONS, validate_avatar_size


def user_avatar_upload_to(instance, filename: str) -> str:
    """`users/<user id>/avatar/<name>-<token>.<ext>`.

    The uploaded file's name is kept, with a random token before the
    extension. The token also makes a new avatar's URL differ from the old
    one, so browsers don't keep showing the replaced image from their cache.

    A user that isn't saved yet has no id (this happens when an avatar is
    attached in the admin while creating the account); such a file goes to
    `users/new/` instead.
    """
    owner = instance.pk or "new"
    return f"{USERS_DIR}/{owner}/avatar/{file_with_token(filename)}"


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model representing a user of the application.

    Uses email as the unique identifier instead of username.
    Includes personal details, avatar, and Django auth fields.
    """

    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    avatar = models.ImageField(
        _("avatar"),
        upload_to=user_avatar_upload_to,
        max_length=255,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=AVATAR_ALLOWED_EXTENSIONS),
            validate_avatar_size,
        ],
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    must_change_password = models.BooleanField(
        _("must change password"),
        default=False,
        help_text=_(
            "Set for an account created with a temporary password: until the "
            "person chooses their own, the API only lets them do that."
        ),
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["email"]

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    def __str__(self):
        return self.email

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
