from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket
from planetarium.permissions import IsOwnerOrAdmin
from planetarium.serializers import ShowThemeSerializer, AstronomyShowSerializer, ReservationSerializer, \
    PlanetariumDomeSerializer, TicketSerializer


class ShowThemeViewSet(ModelViewSet):
    queryset = ShowTheme.objects.all()
    serializer_class = ShowThemeSerializer


class AstronomyShowViewSet(ModelViewSet):
    queryset = AstronomyShow.objects.all()
    serializer_class = AstronomyShowSerializer

class PlanetariumDomeViewSet(ModelViewSet):
    queryset = PlanetariumDome.objects.all()
    serializer_class = PlanetariumDomeSerializer


class ReservationViewSet(ReadOnlyModelViewSet):
    queryset = Reservation.objects.all().select_related()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)


    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all().select_related()
        return Reservation.objects.filter(user=user)

class TicketViewSet(ModelViewSet):
    queryset = Ticket.objects.all().select_related("reservation", "show_session")
    serializer_class = TicketSerializer


class ShowSessionViewSet(ModelViewSet):
    pass