from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.relations import SlugRelatedField, StringRelatedField
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.validators import UniqueTogetherValidator

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket, ShowSession, Payment
from planetarium.services import send_verification_email


class EmptySerializer(serializers.Serializer):
    """Empty serializer for API views that do not require serialization."""
    pass


class UserSerializer(ModelSerializer):
    """Serializer for user data."""

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "first_name", "last_name", "password", "is_staff")
        read_only_fields = ("id", "is_staff")
        extra_kwargs = {"password": {"write_only": True, "min_length": 8}}

    @transaction.atomic
    def create(self, validated_data):
        """Create a user but set `is_active=False` and send a verification email."""
        # validated_data["is_active"] = False  # User is inactive until email verification
        # validated_data["verification_token"] = uuid.uuid4()  # Generate unique token

        user = get_user_model().objects.create_user(**validated_data)
        send_verification_email(user)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ShowThemeSerializer(ModelSerializer):
    """Serializer for show themes."""

    class Meta:
        model = ShowTheme
        fields = "__all__"


class AstronomyShowSerializer(ModelSerializer):
    """Serializer for astronomy shows."""

    class Meta:
        model = AstronomyShow
        fields = "__all__"


class PlanetariumDomeSerializer(ModelSerializer):
    """Serializer for planetarium domes."""

    class Meta:
        model = PlanetariumDome
        fields = "__all__"


class ShowSessionSerializer(ModelSerializer):
    """Serializer for show sessions with validation to prevent scheduling conflicts."""

    class Meta:
        model = ShowSession
        fields = "__all__"
        validators = (
            UniqueTogetherValidator(
                queryset=ShowSession.objects.select_related("astronomy_show", "planetarium_dome"),
                fields=("planetarium_dome", "show_time"),
                message="A show is already scheduled at this time in the selected dome. Please choose a different time or dome."
            ),
        )


class ShowSessionListSerializer(ModelSerializer):
    """Serializer for listing show sessions with related fields."""

    astronomy_show = SlugRelatedField(slug_field="title", read_only=True)
    planetarium_dome = SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = ShowSession
        fields = "__all__"


class ShowSessionDetailSerializer(ModelSerializer):
    """Serializer for detailed view of a show session."""

    astronomy_show = AstronomyShowSerializer()
    planetarium_dome = PlanetariumDomeSerializer()

    class Meta:
        model = ShowSession
        fields = "__all__"


class TicketSerializer(ModelSerializer):
    """Serializer for displaying ticket details."""

    show_session = StringRelatedField()

    class Meta:
        model = Ticket
        exclude = ("reservation",)


class TicketCreateSerializer(ModelSerializer):
    """Serializer for creating tickets with validation to prevent seat duplication."""

    show_session = serializers.PrimaryKeyRelatedField(queryset=ShowSession.objects.all())

    class Meta:
        model = Ticket
        exclude = ("reservation",)
        validators = (
            UniqueTogetherValidator(
                queryset=Ticket.objects.select_related("reservation", "show_session"),
                fields=("row", "seat", "show_session"),
                message="Seat is already taken."
            ),
        )


class PaymentSerializer(ModelSerializer):
    """Serializer for payment details."""

    class Meta:
        model = Payment
        fields = ("id", "reservation", "session_url", "session_id", "amount_of_money", "status")
        read_only_fields = ("id", "session_url", "session_id", "amount_of_money", "status")


class ReservationSerializer(ModelSerializer):
    """Serializer for reservation details, including user, tickets, and payment info."""

    user = UserSerializer()
    tickets = TicketSerializer(many=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = "__all__"


class ReservationCreateSerializer(ModelSerializer):
    """Serializer for creating reservations, adding tickets, and initiating Stripe payment."""

    tickets = TicketCreateSerializer(many=True)
    checkout_url = serializers.URLField(read_only=True)

    class Meta:
        model = Reservation
        fields = ("tickets", "checkout_url")

    @transaction.atomic
    def create(self, validated_data):
        """
        Creates a reservation, adds tickets, and generates a Stripe Checkout session.
        """
        tickets_data = validated_data.pop("tickets")

        user = self.context["request"].user
        if user.is_authenticated:
            reservation = Reservation.objects.create(user=user)
        else:
            reservation = Reservation.objects.create(user=None)  # Anonymous user

        # Add tickets
        Ticket.objects.bulk_create(
            [Ticket(reservation=reservation, **ticket_data) for ticket_data in tickets_data]
        )

        # Call the reusable method to create Stripe Checkout
        checkout_url = reservation.create_stripe_checkout(self.context["request"])

        reservation.checkout_url = checkout_url

        return reservation


class ReservationDetailSerializer(ModelSerializer):
    """Detailed reservation serializer with user, tickets, and payment details."""

    user = UserSerializer()
    tickets = TicketSerializer(many=True)
    payment = PaymentSerializer()

    class Meta:
        model = Reservation
        fields = "__all__"
