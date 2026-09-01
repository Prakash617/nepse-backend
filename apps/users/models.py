from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """Custom user model for NEPSE Platform."""

    class Meta:
        db_table = "auth_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return self.username
