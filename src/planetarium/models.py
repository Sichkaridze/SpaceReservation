from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import DO_NOTHING
from django.utils.timezone import now

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        """ Create a new user profile """
        if not email:
            raise ValueError('User must have an email address')
        if not first_name:
            raise ValueError('User must have first name')
        if not last_name:
            raise ValueError('User must have last name')

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
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="planetarium_users",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="planetarium_users_permissions",
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

class PlanetariumDome(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()

    def __str__(self):
        return self.name

class Reservation(models.Model):
    class Status(models.IntegerChoices):
        PENDING = 0, 'Pending'
        PAID = 1, 'Paid'
        CANCELLED = -1, 'Cancelled'

    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="reservations"
    )

    def is_expired(self):
        """Checks if more than 15 minutes have passed since the reservation was created."""
        return self.status == self.Status.PENDING and (now() - self.created_at > timedelta(minutes=15))

    def cancel_if_expired(self):
        """Automatically cancels the reservation if it has expired."""
        if self.is_expired():
            self.status = self.Status.CANCELLED
            self.save()

class Ticket(models.Model):
    class Status(models.IntegerChoices):
        VALID = 1, "Valid"
        RETURNED = -1, "Returned"
    status = models.IntegerField(choices=Status.choices, default=Status.VALID)
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

class ShowSession(models.Model):
    astronomy_show = models.ForeignKey(
        AstronomyShow,
        on_delete=models.CASCADE,
        related_name="show_sessions"
    )
    planetarium_dome = models.ForeignKey(
        PlanetariumDome,
        on_delete=models.CASCADE,
        related_name="show_sessions"
    )
    show_time = models.DateTimeField()
    duration = models.DurationField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("planetarium_dome", "show_time"),
                name="unique_show_for_dome"
            ),
        )

    def __str__(self):
        return (
            f"Show: {self.astronomy_show}\n"
            f"Dome: {self.planetarium_dome}\n"
            f"Time: {self.show_time}"
        )

class Payment(models.Model):
    class Status(models.IntegerChoices):
        PENDING = 0, 'Pending'
        PAID = 1, 'Paid'
    reservation = models.OneToOneField(Reservation, on_delete=DO_NOTHING, related_name="payment")
    session_url = models.URLField() # url to stripe payment session
    session_id = models.CharField(max_length=255) # id of stripe payment session
    amount_of_money = models.DecimalField(max_digits=10, decimal_places=2) # (in $USD) calculated total price
# 4. Payment:
# Status: Enum: PENDING | PAID