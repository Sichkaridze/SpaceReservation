import uuid

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import OperationalError

from planetarium.models import (
    Reservation, Ticket, ShowSession, AstronomyShow, PlanetariumDome, ShowTheme, Payment
)
from django.utils.timezone import now, timedelta
import random
from faker import Faker


fake = Faker("it_IT")  # Using Italian localization (: I really like it :)

class Command(BaseCommand):
    help = "Fills the database with realistic test data"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        try:
            # Check if any data exists in the database
            if (
                    User.objects.exists() or
                    AstronomyShow.objects.exists() or
                    PlanetariumDome.objects.exists() or
                    ShowSession.objects.exists() or
                    Reservation.objects.exists() or
                    Ticket.objects.exists()
            ):
                self.stdout.write(
                    self.style.ERROR("❌  Database is not empty! Please save existing data and clear it from db before seeding."))
                self.stdout.write(
                    self.style.WARNING("💡 Use `python manage.py flush --noinput` to clear data or `reset_db` to renovate."))
                return  # Stop execution if data exists

        except OperationalError:
            self.stdout.write(self.style.ERROR("❌ Database is not available. Did you run `migrate`?"))
            return

        self.stdout.write("📥 Loading data from fixture...")
        try:
            call_command("loaddata", "initial_data.json")  # Load your fixture file
            self.stdout.write(self.style.SUCCESS("Fixture data loaded successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error loading fixture: {e}"))

        self.stdout.write("🛠 Generating test data...")

        # Generate Show Themes
        themes = []
        for _ in range(5):
            theme, _ = ShowTheme.objects.get_or_create(
                name=fake.word().capitalize()
            )
            themes.append(theme)

        self.stdout.write(f"🎭 Created {len(themes)} show themes.")

        # Generate Users
        users = []
        for _ in range(5):
            email = fake.email()
            first_name = fake.first_name()
            last_name = fake.last_name()

            user, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first_name, "last_name": last_name, "password": "password123"}
            )
            users.append(user)

        self.stdout.write(f"👤 Created {len(users)} users.")

        # Generate Astronomy Shows
        astronomy_shows = []
        for _ in range(5):
            show, _ = AstronomyShow.objects.get_or_create(
                title=fake.sentence(nb_words=3),
                description=fake.paragraph(),
            )
            astronomy_shows.append(show)

        self.stdout.write(f"🎥 Created {len(astronomy_shows)} astronomy shows.")

        # Generate Planetarium Domes
        planetarium_domes = []
        for _ in range(3):
            dome, _ = PlanetariumDome.objects.get_or_create(
                name=fake.company(),
                rows=random.randint(5, 15),
                seats_in_row=random.randint(10, 30),
            )
            planetarium_domes.append(dome)

        self.stdout.write(f"🏛 Created {len(planetarium_domes)} planetarium domes.")

        # Generate Show Sessions
        show_sessions = []
        for _ in range(5):
            session, _ = ShowSession.objects.get_or_create(
                show_time=now() + timedelta(days=random.randint(1, 30)),
                astronomy_show=random.choice(astronomy_shows),
                planetarium_dome=random.choice(planetarium_domes),
                duration=timedelta(minutes=random.randint(30, 120)),  # Random duration
                ticket_price=round(random.uniform(5, 25), 2),  # Ticket price
            )
            show_sessions.append(session)

        self.stdout.write(f"🕒 Created {len(show_sessions)} show sessions.")

        # Generate Reservations
        reservations = []
        for _ in range(5):
            reservation = Reservation.objects.create(
                user=random.choice(users),
                status=random.choice([0, 1, -1]),  # Pending, Paid, or Canceled
            )
            reservations.append(reservation)

        self.stdout.write(f"📜 Created {len(reservations)} reservations.")

        # Generate Tickets
        tickets = []
        for _ in range(10):
            session = random.choice(show_sessions[1:]) # Excludes the first session for examples of how to use documentation
            ticket = Ticket.objects.create(
                reservation=random.choice(reservations),
                show_session=session,
                row=random.randint(1, session.planetarium_dome.rows),
                seat=random.randint(1, session.planetarium_dome.seats_in_row),
                status=random.choice([1, -1]),  # Valid or Non-valid
            )
            tickets.append(ticket)

        self.stdout.write(f"🎟  Created {len(tickets)} tickets.")

        # Generate Payments
        for reservation in reservations:
            if reservation.status == 1:  # Paid reservations
                Payment.objects.create(
                    reservation=reservation,
                    session_url=f"https://fake.stripe.com/session/{uuid.uuid4()}",
                    session_id=str(uuid.uuid4()),
                    amount_of_money=reservation.total_price() or 0,
                    status=1,  # Paid
                )

        self.stdout.write(f"💰 Created payments for paid reservations.")

        self.stdout.write(self.style.SUCCESS("Database successfully populated with test data!"))
