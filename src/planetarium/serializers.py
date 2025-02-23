from django.contrib.auth import get_user_model
from rest_framework.relations import SlugRelatedField, StringRelatedField
from rest_framework.serializers import ModelSerializer
from rest_framework.validators import UniqueTogetherValidator

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket, ShowSession


class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "email", "first_name", "last_name", "password", "is_staff")
        read_only_fields = ("id", "is_staff")
        extra_kwargs = {"password": {"write_only": True, "min_length": 8}}

    def create(self, validated_data):
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class ShowThemeSerializer(ModelSerializer):
    class Meta:
        model = ShowTheme
        fields = "__all__"


class AstronomyShowSerializer(ModelSerializer):
    class Meta:
        model = AstronomyShow
        fields = "__all__"


class PlanetariumDomeSerializer(ModelSerializer):
    class Meta:
        model = PlanetariumDome
        fields = "__all__"


class TicketSerializer(ModelSerializer):
    show_session = StringRelatedField()
    class Meta:
        model = Ticket
        exclude = "reservation",


class TicketCreateSerializer(ModelSerializer):
    class Meta:
        model = Ticket
        fields = "__all__"
        validators = (
            UniqueTogetherValidator(
                queryset= Ticket.objects.all().select_related("reservation", "show_session"),
                fields=("row", "seat", "show_session"),
                message="This seat is already taken."
            ),
        )


    def create(self, validated_data):
        """
        Creates a ticket and ensures it is linked to a valid reservation.
        If no active reservation exists for the user, a new one is created.
        """

        request = self.context.get("request")
        user = request.user

        reservation = Reservation.objects.get_or_create(user=user, status=Reservation.Status.PENDING)
        validated_data["reservation"] = reservation
        return super().create(validated_data)


class ReservationSerializer(ModelSerializer):
    user = UserSerializer()
    tickets = TicketSerializer(many=True)
    class Meta:
        model = Reservation
        fields = "__all__"


class ReservationDetailSerializer(ModelSerializer):
    """Will include info about payment""" # TODO Implement Detail Serializer with payment info for reservation
    pass


class ShowSessionSerializer(ModelSerializer):
    class Meta:
        model = ShowSession
        fields = "__all__"
        validators = (
            UniqueTogetherValidator(
                queryset=ShowSession.objects.all().select_related("astronomy_show", "planetarium_dome"),
                fields=("planetarium_dome", "show_time"),
                message="A show is already scheduled at this time in the selected dome. Please choose a different time or dome."
            ),
        )


class ShowSessionListSerializer(ModelSerializer):
    astronomy_show = SlugRelatedField(slug_field="title", read_only=True)
    planetarium_dome = SlugRelatedField( slug_field="name", read_only=True)

    class Meta:
        model = ShowSession
        fields = "__all__"


class ShowSessionDetailSerializer(ModelSerializer):
    astronomy_show = AstronomyShowSerializer()
    planetarium_dome = PlanetariumDomeSerializer()
    class Meta:
        model = ShowSession
        fields = "__all__"
