from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import DO_NOTHING


class ShowTheme(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class AstronomyShow(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title


class Reservation(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="reservations"
    )


class Ticket(models.Model):
    row = models.IntegerField()
    seat = models.IntegerField()
    show_session = models.ForeignKey(
        "ShowSession",
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("row", "seat", "show_session"),
                name="unique_seat_per_session"
            ),
        )

    def __str__(self):
        return (
            f"Ticket owner: {self.reservation.user.first_name} {self.reservation.user.last_name}\n"
            f"Show: {self.show_session.astronomy_show}\n"
            f"Show time: {self.show_session.show_time}\n"
            f"Dome: {self.show_session.planetarium_dome}\n"
            f"{self.row} row, {self.seat} seat."
        )


class PlanetariumDome(models.Model):
    name = models.CharField(max_length=255, unique=True)
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()

    def __str__(self):
        return self.name


class ShowSession(models.Model):
    astronomy_show = models.ForeignKey(
        AstronomyShow,
        on_delete=models.CASCADE,
        related_name="show_sessions"
    )
    planetarium_dome = models.ForeignKey(
        PlanetariumDome,
        on_delete=DO_NOTHING,
        related_name="show_sessions"
    )
    show_time = models.DateTimeField()

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("planetarium_dome", "show_time"),
                name="unique_show_for_dome"
            ),
        )

    def __str__(self):
        return (
            f"Show: {self.astronomy_show}"
            f"Dome: {self.planetarium_dome}"
            f"Time: {self.show_time}"
        )
