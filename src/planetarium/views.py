import os
import stripe
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket, ShowSession
from planetarium.permissions import IsOwnerOrAdmin
from planetarium.serializers import ShowThemeSerializer, AstronomyShowSerializer, ReservationSerializer, \
    PlanetariumDomeSerializer, TicketCreateSerializer, ShowSessionListSerializer, \
    ShowSessionDetailSerializer, ShowSessionSerializer, UserSerializer, CardInformationSerializer

class StripeCheckoutAPI(APIView):
    """
    Створення сесії Stripe Checkout для квитка.
    """
    permission_classes = (AllowAny,)

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        ticket_id = request.data.get("ticket_id")
        try:
            ticket = Ticket.objects.get(id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

        # Створення посилань success та cancel
        success_url = request.build_absolute_uri(reverse("planetarium:stripe-success")) + "?session_id={CHECKOUT_SESSION_ID}"
        cancel_url = request.build_absolute_uri(reverse("planetarium:stripe-cancel"))

        try:
            # Створення Stripe Checkout сесії
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Ticket for {ticket.show_session.astronomy_show.title}",
                            },
                            "unit_amount": int(ticket.show_session.ticket_price * 100),  # Stripe працює в центах
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )

            # Збереження session_id у квитку
            ticket.payment_session_id = checkout_session.id
            ticket.save()

            return Response({"checkout_url": checkout_session.url, "session_id": checkout_session.id})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class StripeSuccessAPI(APIView):
    """
    Перевірка успішного платежу через session_id.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session_id = request.GET.get("session_id")
        if not session_id:
            return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                # Позначаємо квиток як оплачений
                ticket = Ticket.objects.filter(payment_session_id=session_id).first()
                if ticket:
                    ticket.is_paid = True
                    ticket.save()
                    return Response({"message": "Payment successful", "ticket_id": ticket.id})

                return Response({"error": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"error": "Payment not completed"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class StripeCancelAPI(APIView):
    """
    Відповідь для випадку, якщо користувач скасував оплату.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"message": "Payment was cancelled. You can try again."})

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