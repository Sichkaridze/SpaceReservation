import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.http import JsonResponse
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView, get_object_or_404
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
    ReservationCreateSerializer, ReservationDetailSerializer, EmptySerializer
)


class StripeSuccessAPI(APIView):
    """
    Verifies successful payment using session_id.
    """
    serializer_class = EmptySerializer
    permission_classes = (AllowAny,)

    @transaction.atomic
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

                if not payment:
                    return Response({"error": "Payment not found"}, status=status.HTTP_404_NOT_FOUND)

                reservation = payment.reservation

                # Assign user from Stripe payment details if not already assigned
                if not reservation.user:
                    reservation.assign_user_from_stripe(session.customer_details)

                payment.mark_as_paid()  # Updates payment and ticket statuses
                return Response({"message": "Payment successful", "reservation_id": payment.reservation.id})


            return Response({"error": "Payment not completed"}, status=status.HTTP_400_BAD_REQUEST)

        except stripe.error.StripeError as e:
            return Response({"error": f"Stripe error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


class StripeCancelAPI(APIView):
    """
    Handles cases where the user cancels the payment.
    """
    serializer_class = EmptySerializer
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
    Updating and deleting reservations is **not allowed**.
    """
    queryset = Reservation.objects.all().select_related("user")
    http_method_names = ["get", "post"]

    def get_permissions(self):
        """
        Assign permissions dynamically:
        - `create`: Any user can create a reservation (anonymous or authenticated).
        - Other actions: Only authenticated users.
        """
        if self.action == "create":
            return (AllowAny(),)
        return (IsAuthenticated(), IsOwnerOrAdmin())

    def get_serializer_class(self):
        """
        Selects the appropriate serializer based on the action.
        """
        if self.action == "create":
            return ReservationCreateSerializer
        elif self.action == "retrieve":
            return ReservationDetailSerializer
        return ReservationSerializer

    def get_queryset(self):
        """
        Staff users can view all reservations.
        Regular users only see their own.
        """
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all().select_related("user")
        return Reservation.objects.filter(user=user)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Creates a reservation and returns a `payment_url`.
        """

        # Validate request payload
        if not request.data.get("tickets"):
            return Response({"error": "Cannot create an empty reservation."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReservationCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        # Save reservation and tickets
        self.perform_create(serializer)
        reservation = serializer.instance
        # reservation.refresh_from_db()

        payment = Payment.objects.filter(reservation=reservation).first()

        return Response({"redirect_url": payment.session_url}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Automatically assigns the current user to the reservation if authenticated.
        If the user is anonymous, `user=None` is stored, but will be updated later.
        """
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)


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


class VerifyEmailView(APIView):
    """API view to verify user email via token."""

    def get(self, request, uidb64, token):
        """Handles email verification when the user clicks the link."""
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(get_user_model(), pk=uid)

            if user.is_active:
                return Response({"message": "Email already verified."}, status=status.HTTP_200_OK)

            if not default_token_generator.check_token(user, token):  # Validate the token
                return Response({"error": "❌ Invalid or expired verification token."}, status=status.HTTP_400_BAD_REQUEST)

            # Activate user
            user.is_active = True
            user.save()

            return Response({"message": "🎉 Email successfully verified! You can now log in."}, status=status.HTTP_200_OK)

        except Exception:
            return Response({"error": "❌ Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)


def health_check(request):
    return JsonResponse({"status": "ok"})
