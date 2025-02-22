from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.db.models import DO_NOTHING
from django.db.models.manager import BaseManager


class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        """ Create a new user profile """
        if not email:
            raise ValueError('User must have an email address')

        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name)

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, first_name, last_name, password):
        """ Create a new superuser profile """
        user = self.create_user(email, first_name, last_name, password)
        user.is_superuser = True
        user.is_staff = True

        user.save(using=self._db)

        return user


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = None
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="planetarium_users",  # Унікальна назва для уникнення конфлікту
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="planetarium_users_permissions",  # Унікальна назва
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ("first_name", "last_name")

    def __str__(self):
        return (f"{self.first_name} {self.last_name}\n"
                f"{self.email}")


class ShowTheme(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class AstronomyShow(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="reservations"
    )


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    show_session = models.ForeignKey(
        "ShowSession",
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("row", "seat", "show_session"),
                name="unique_seat_per_session"
            ),
        )

    def __str__(self):
        return (
            f"Ticket owner: {self.reservation.user.first_name} {self.reservation.user.last_name}\n"
            f"Show: {self.show_session.astronomy_show}\n"
            f"Show time: {self.show_session.show_time}\n"
            f"Dome: {self.show_session.planetarium_dome}\n"
            f"{self.row} row, {self.seat} seat."
        )


class PlanetariumDome(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()

    def __str__(self):
        return self.name


class ShowSession(models.Model):
    astronomy_show = models.ForeignKey(
        AstronomyShow,
        on_delete=models.CASCADE,
        related_name="show_sessions"
    )
    planetarium_dome = models.ForeignKey(
        PlanetariumDome,
        on_delete=DO_NOTHING,
        related_name="show_sessions"
    )
    show_time = models.DateTimeField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("planetarium_dome", "show_time"),
                name="unique_show_for_dome"
            ),
        )

    def __str__(self):
        return (
            f"Show: {self.astronomy_show}"
            f"Dome: {self.planetarium_dome}"
            f"Time: {self.show_time}"
        )
