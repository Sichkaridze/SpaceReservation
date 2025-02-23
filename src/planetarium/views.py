import os

from django.conf import settings
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket, ShowSession
from planetarium.permissions import IsOwnerOrAdmin
from planetarium.serializers import ShowThemeSerializer, AstronomyShowSerializer, ReservationSerializer, \
    PlanetariumDomeSerializer, TicketCreateSerializer, ShowSessionListSerializer, \
    ShowSessionDetailSerializer, ShowSessionSerializer, UserSerializer, CardInformationSerializer


class PaymentAPI(APIView):
    serializer_class = CardInformationSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        pass

    def stripe_card_payment(self, data_dict):
        pass


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

class ReservationCreateView():
    pass

class TicketView(CreateAPIView):
    queryset = Ticket.objects.all().select_related("reservation", "show_session")
    serializer_class = TicketCreateSerializer


class ShowSessionViewSet(ModelViewSet):
    queryset = ShowSession.objects.all().select_related("astronomy_show", "planetarium_dome")

    def get_serializer_class(self):
        if self.action == "list":
            return ShowSessionListSerializer
        elif self.action == "create":
            return ShowSessionSerializer
        elif self.action == "retrieve":
            return ShowSessionDetailSerializer
        return ShowSessionSerializer


class CreateUserView(CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (AllowAny, )


class UpdateUserView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, )

    def get_object(self):
        return self.request.user