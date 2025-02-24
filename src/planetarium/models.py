import pathlib
import uuid
from datetime import timedelta

import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.db.models import DO_NOTHING, Sum
from django.utils.text import slugify
from django.utils.timezone import now
from rest_framework.reverse import reverse


class UserManager(BaseUserManager):
    """Custom manager for User model with helper methods."""

    def create_user(self, email, first_name, last_name, password=None):
        """Creates a new user profile."""
        if not email:
            raise ValueError("User must have an email address")
        if not first_name:
            raise ValueError("User must have a first name")
        if not last_name:
            raise ValueError("User must have a last name")

        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password):
        """Creates a new superuser."""
        user = self.create_user(email, first_name, last_name, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractUser):
    """Custom user model using email as the unique identifier."""

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
        return f"{self.first_name} {self.last_name} ({self.email})"


class ShowTheme(models.Model):
    """Model for categorizing different show themes."""

    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

# ______________________________________________________________________________________

def poster_image_path(instance, filename: str) -> pathlib.Path:
    """Generates a unique file path for storing poster images."""
    filename = f"{slugify(instance.title)}-{uuid.uuid4()}" + pathlib.Path(filename).suffix
    return pathlib.Path("upload/posters") / pathlib.Path(filename)
# ______________________________________________________________________________________


class AstronomyShow(models.Model):
    """Model representing an astronomy show."""

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    poster = models.ImageField(null=True, blank=True, upload_to=poster_image_path)

    def __str__(self):
        return self.title


class PlanetariumDome(models.Model):
    """Model for a planetarium dome (theater) where shows take place."""

    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()

    def __str__(self):
        return self.name


class ShowSession(models.Model):
    """A scheduled show session in a specific dome."""

    astronomy_show = models.ForeignKey(
        AstronomyShow, on_delete=models.CASCADE, related_name="show_sessions"
    )
    planetarium_dome = models.ForeignKey(
        PlanetariumDome, on_delete=models.CASCADE, related_name="show_sessions"
    )
    show_time = models.DateTimeField()
    duration = models.DurationField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("planetarium_dome", "show_time"),
                name="unique_show_for_dome",
            ),
        )

    def __str__(self):
        return (
            f"Show: {self.astronomy_show}\n"
            f"Dome: {self.planetarium_dome}\n"
            f"Time: {self.show_time}"
        )


class Reservation(models.Model):
    """Model representing a user's reservation for tickets."""

    class Status(models.IntegerChoices):
        PENDING = 0, "Pending"
        PAID = 1, "Paid"
        CANCELLED = -1, "Cancelled"

    status = models.IntegerField(choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="reservations", null=True
    )

    def assign_user_from_stripe(self, stripe_customer_details):
        """
        Assigns a user to the reservation based on Stripe payment details.
        If the user exists, updates their first and last name.
        """
        email = stripe_customer_details.get("email")
        name_parts = stripe_customer_details.get("name", "Anonymous User").split(" ")

        first_name = name_parts[0] if len(name_parts) > 0 else "Anonymous"
        last_name = name_parts[1] if len(name_parts) > 1 else "User"

        # Create or update user
        user, created = get_user_model().objects.update_or_create(
            email=email,
            defaults={"first_name": first_name, "last_name": last_name}
        )

        # Assign the user to the reservation
        self.user = user
        self.save()

    def is_expired(self):
        """Checks if the reservation has expired (15 minutes after creation)."""
        return (
            self.status == self.Status.PENDING
            and (now() - self.created_at > timedelta(minutes=15))
        )

    def cancel_if_expired(self):
        """Automatically cancels the reservation if it has expired."""
        if self.is_expired():
            self.status = self.Status.CANCELLED
            self.save()

    def total_price(self):
        """Calculates the total price of tickets in this reservation."""
        return self.tickets.aggregate(total=Sum("show_session__ticket_price"))["total"]

    @transaction.atomic
    def create_stripe_checkout(self, request):
        """
        Creates a Stripe Checkout Session and returns its URL and session ID.
        """
        # Create Stripe Checkout Session
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Calculate total price
        total_amount = self.total_price()

        user_email = self.user.email if self.user else None

        if total_amount == 0:
            raise ValueError("Cannot process payment for an empty reservation.")

        success_url = request.build_absolute_uri(
            reverse("planetarium:stripe-success")) + "?session_id={CHECKOUT_SESSION_ID}"
        cancel_url = request.build_absolute_uri(reverse("planetarium:stripe-cancel"))

        checkout_session = stripe.checkout.Session.create(
            customer_email=user_email,
            allow_promotion_codes=True,
            payment_method_types=["card"],
            # custom_fields=[
            #     {
            #         "key": "email_verification",
            #         "label": {"type": "custom", "custom": "Enter your correct email"},
            #         "type": "text",
            #         "optional": False,
            #     }
            # ],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Planetarium Ticket Reservation 🎟️",
                            "description": (
                                "⚠️ Please enter a valid email. "
                                "Tickets will be sent there after payment confirmation."
                            )
                        },
                        "unit_amount": int(total_amount * 100),  # Stripe works in cents
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )

        # Create Payment record
        Payment.objects.create(
            reservation=self,
            session_id=checkout_session.id,
            session_url=checkout_session.url,
            amount_of_money=total_amount,
            status=Payment.Status.PENDING
        )

        return checkout_session.url


class Ticket(models.Model):
    """Model representing a ticket for a specific show session."""

    class Status(models.IntegerChoices):
        VALID = 1, "Valid"
        NON_VALID = -1, "Non-valid"

    status = models.IntegerField(choices=Status.choices, default=Status.NON_VALID)
    row = models.IntegerField()
    seat = models.IntegerField()
    show_session = models.ForeignKey(
        ShowSession, on_delete=models.CASCADE, related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="tickets"
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("row", "seat", "show_session"),
                name="unique_seat_per_session",
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


class Payment(models.Model):
    """Model representing a Stripe payment for a reservation."""

    class Status(models.IntegerChoices):
        PENDING = 0, "Pending"
        PAID = 1, "Paid"

    reservation = models.OneToOneField(
        Reservation, on_delete=DO_NOTHING, related_name="payment"
    )
    session_url = models.URLField()  # Stripe checkout session URL
    session_id = models.CharField(max_length=255)  # Stripe session ID
    amount_of_money = models.DecimalField(
        max_digits=10, decimal_places=2
    )  # Total payment amount
    status = models.IntegerField(
        choices=Status.choices, default=Status.PENDING
    )  # Payment status

    @transaction.atomic
    def mark_as_paid(self):
        """Marks payment as completed and updates reservation and tickets status."""
        self.status = self.Status.PAID
        self.save()
        self.reservation.status = Reservation.Status.PAID
        self.reservation.save()
        self.reservation.tickets.update(
            status=Ticket.Status.VALID
        )  # All tickets in the reservation become valid

    def __str__(self):
        return f"Payment for Reservation {self.reservation.id} - {self.get_status_display()} (${self.amount_of_money})"
