from django.urls import path, include
from rest_framework import routers

from planetarium.views import ShowThemeViewSet, AstronomyShowViewSet, ReservationViewSet, PlanetariumDomeViewSet, \
    ShowSessionViewSet

app_name = "planetarium"

router = routers.DefaultRouter()

router.register("show_themes", ShowThemeViewSet)
router.register("astronomy_shows", AstronomyShowViewSet)
router.register("planetarium_domes", PlanetariumDomeViewSet)
router.register("reservations", ReservationViewSet)
router.register("show_sessions", ShowSessionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
