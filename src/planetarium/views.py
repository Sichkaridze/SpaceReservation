import os
import stripe
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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
        serializer = CardInformationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            try:
                result = self.stripe_card_payment(serializer.validated_data)
                return Response(result)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def stripe_card_payment(self, data_dict):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            card_token = stripe.Token.create(
                card={
                    "number": data_dict.get("card_number"),
                    "exp_month": data_dict.get("expiry_month"),
                    "exp_year": data_dict.get("expiry_year"),
                    "cvc": data_dict.get("cvv"),
                }
            )
            payment = stripe.Charge.create(
                amount=data_dict.get("amount"),
                currency="usd",
                source=card_token.id,
                description=f"Test payment for {data_dict.get('email')}"
            )
            return {
                "status": payment.status,
                "payment_id": payment.id,
                "amount": payment.amount / 100,  # Convert cents to dollars
            }
        except stripe.error.CardError as e:
            raise Exception(f"Card error: {e.error.message}")
        except stripe.error.StripeError as e:
            raise Exception(f"Payment failed: {str(e)}")



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