from django.contrib.auth import get_user_model
from rest_framework.serializers import ModelSerializer

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket


class UserSerializer(ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "first_name", "last_name", "email")


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
    class Meta:
        model = Ticket
        fields = "__all__"

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user
        show_session = validated_data["show_session"]

        reservation = Reservation.objects.get_or_create(user=user, status=)


class ReservationSerializer(ModelSerializer):
    user = UserSerializer()
    tickets = TicketSerializer(many=True)
    class Meta:
        model = Reservation
        fields = "__all__"

class ShowSessionSerializer(ModelSerializer):
    pass

