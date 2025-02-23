import stripe
from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from planetarium.models import ShowTheme, AstronomyShow, Reservation, PlanetariumDome, Ticket, ShowSession, Payment
from planetarium.permissions import IsOwnerOrAdmin
from planetarium.serializers import (
    ShowThemeSerializer, AstronomyShowSerializer, ReservationSerializer,
    PlanetariumDomeSerializer, TicketCreateSerializer, ShowSessionListSerializer,
    ShowSessionDetailSerializer, ShowSessionSerializer, UserSerializer, PaymentSerializer, EmptySerializer
)


class StripeCheckoutAPI(APIView):
    """
    Створення Stripe Checkout Session для бронювання.
    """
    serializer_class = EmptySerializer
    permission_classes = (AllowAny,)


    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        reservation_id = request.data.get("reservation_id")
        try:
            reservation = Reservation.objects.get(id=reservation_id, status=Reservation.Status.PENDING)
        except Reservation.DoesNotExist:
            return Response({"error": "Reservation not found or already paid."}, status=status.HTTP_404_NOT_FOUND)

        # Отримуємо загальну вартість бронювання
        total_amount = reservation.total_price()
        if total_amount == 0:
            return Response({"error": "Cannot process payment for an empty reservation."}, status=status.HTTP_400_BAD_REQUEST)

        # Посилання на сторінки успіху/відміни
        success_url = request.build_absolute_uri(reverse("planetarium:stripe-success")) + "?session_id={CHECKOUT_SESSION_ID}"
        cancel_url = request.build_absolute_uri(reverse("planetarium:stripe-cancel"))

        try:
            # Створення Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Reservation {reservation.id} - Planetarium",
                            },
                            "unit_amount": int(total_amount * 100),  # Stripe працює в центах
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=success_url,
                cancel_url=cancel_url,
            )

            # Створюємо об'єкт Payment
            payment = Payment.objects.create(
                reservation=reservation,
                session_id=checkout_session.id,
                session_url=checkout_session.url,
                amount_of_money=total_amount,
                status=Payment.Status.PENDING
            )

            return Response({"checkout_url": checkout_session.url, "session_id": checkout_session.id})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StripeSuccessAPI(APIView):
    """
    Перевірка успішного платежу через session_id.
    """
    serializer_class = EmptySerializer
    permission_classes = (AllowAny,)

    def get(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session_id = request.GET.get("session_id")
        if not session_id:
            return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.payment_status == "paid":
                # Отримуємо оплату по session_id
                payment = Payment.objects.filter(session_id=session_id).first()
                if payment:
                    payment.mark_as_paid()  # Оновлення статусу оплати та квитків
                    return Response({"message": "Payment successful", "reservation_id": payment.reservation.id})

                return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"error": "Payment not completed"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class StripeCancelAPI(APIView):
    """
    Відповідь, якщо користувач скасував оплату.
    """
    serializer_class = EmptySerializer
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
    queryset = Reservation.objects.all().select_related("user")
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all().select_related("user")
        return Reservation.objects.filter(user=user)


class ReservationCreateView(CreateAPIView):
    """
    API для створення бронювання.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = (IsAuthenticated,)


    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TicketView(CreateAPIView):
    queryset = Ticket.objects.all().select_related("reservation", "show_session")
    serializer_class = TicketCreateSerializer
    permission_classes = (IsAuthenticated,)


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
    permission_classes = (AllowAny,)


class UpdateUserView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
