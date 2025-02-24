import stripe
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.viewsets import ModelViewSet

from planetarium.models import (
    ShowTheme, AstronomyShow, Reservation, PlanetariumDome, ShowSession, Payment
)
from planetarium.permissions import IsOwnerOrAdmin
from planetarium.serializers import (
    ShowThemeSerializer, AstronomyShowSerializer, ReservationSerializer,
    PlanetariumDomeSerializer, ShowSessionListSerializer,
    ShowSessionDetailSerializer, ShowSessionSerializer, UserSerializer,
    ReservationCreateSerializer, ReservationDetailSerializer
)


class StripeSuccessAPI(APIView):
    """
    Verifies successful payment using session_id.
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
                # Retrieve payment record by session_id
                payment = Payment.objects.filter(session_id=session_id).first()
                if payment:
                    payment.mark_as_paid()  # Updates payment and ticket statuses
                    return Response({"message": "Payment successful", "reservation_id": payment.reservation.id})

                return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

            return Response({"error": "Payment not completed"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class StripeCancelAPI(APIView):
    """
    Handles cases where the user cancels the payment.
    """
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"message": "Payment was cancelled. You can try again."})


class ShowThemeViewSet(ModelViewSet):
    """ViewSet for managing show themes."""
    queryset = ShowTheme.objects.all()
    serializer_class = ShowThemeSerializer


class AstronomyShowViewSet(ModelViewSet):
    """ViewSet for managing astronomy shows."""
    queryset = AstronomyShow.objects.all()
    serializer_class = AstronomyShowSerializer


class PlanetariumDomeViewSet(ModelViewSet):
    """ViewSet for managing planetarium domes."""
    queryset = PlanetariumDome.objects.all()
    serializer_class = PlanetariumDomeSerializer


class ReservationViewSet(ModelViewSet):
    """
    ViewSet for retrieving and creating reservations.
    """
    queryset = Reservation.objects.all().select_related("user")
    permission_classes = (IsAuthenticated, IsOwnerOrAdmin)

    # def get_permissions(self): # TODO create get permissions

    def get_serializer_class(self):
        if self.action == "create":
            return ReservationCreateSerializer
        elif self.action == "retrieve":
            return ReservationDetailSerializer
        return ReservationSerializer

    def get_queryset(self):
        """
        If the user is staff, return all reservations.
        Otherwise, return only the user's own reservations.
        """
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all().select_related("user")
        return Reservation.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        """
        Returns `payment_url` after creating a reservation.
        """

        # Handles the API request: Validates, processes, and returns the response/
        if not request.data.get("tickets"):
            return Response({"error": f"Cannot create empty reservation"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Save the reservation and tickets
        self.perform_create(serializer)
        reservation = serializer.instance

        return Response({"redirect_url": reservation.payment.session_url}, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        """
        Automatically assigns the current user to the new reservation.
        """

        # Handles data saving: Assigns user before calling serializer.save().
        serializer.save(user=self.request.user)


class ShowSessionViewSet(ModelViewSet):
    """ViewSet for managing show sessions."""

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
    """API view for user registration."""
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)


class UpdateUserView(RetrieveUpdateAPIView):
    """API view for updating user profile."""
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
