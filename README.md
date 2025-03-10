# SpaceReservation API

**SpaceReservation** is a Django REST Framework (DRF) project for managing **planetarium shows, ticket reservations, and payments**. The project includes **email-based authentication with JWT**, **Celery for background tasks**, **Redis as a message broker**, and **Stripe for payments**.

---

## Features

- 🚀 **Planetarium Show Management** – CRUD operations for astronomy shows.
- 🎟 **Reservation System** – Users can book seats for shows.
- 💳 **Stripe Payments** – Secure online payments.
- 🔒 **JWT Authentication (via Email)** – Secure user login with email and password.
- 📩 **Email Notifications** – Automatic emails for **registration verification**.
- 🏗 **Containerized Deployment** – Uses **Docker & Docker Compose**.
- ⚙ **Celery & Redis Integration** – Background tasks for email sending.

---

## Installation & Setup

### 1. Clone the Repository

```sh
  git clone https://github.com/Sichkaridze/SpaceReservation.git
  cd SpaceReservation
```

### 2. Create & Activate Virtual Environment

```sh
  python3 -m venv venv
  source venv/bin/activate
```

### 3. Install Dependencies

```sh
  pip install -r requirements.txt
```

### 4. Set Up the Database

```sh
  python src/manage.py makemigrations
  python src/manage.py migrate
```

### 5. Load Initial Data (Optional)

```sh
  python src/manage.py loaddata planetarium/fixtures/initial_data.json
```

### 6. Create a Superuser

```sh
  python src/manage.py createsuperuser
```

### 7. Run the Development Server

```sh
  python src/manage.py runserver
```

The project will be available at **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**.

---

## Running the Project with Docker

### 1. Create a `.env` File

Rename `.env.sample` to `.env` and fill in the necessary environment variables.

Example:

```ini
# Django Secret Key
SECRET_KEY=_eSHIGrn*@OSo!H1hDISxl4hH8wj90La

# Email Configuration (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False

# Stripe API Keys
STRIPE_SECRET_KEY="your_stripe_secret_key"
STRIPE_PUBLISHABLE_KEY="your_stripe_publishable_key"

# Celery & Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Database Selection
DJANGO_DB=postgresql

# PostgreSQL
POSTGRES_HOST=postgres-planetarium
POSTGRES_DB=planetarium_db#----> name
POSTGRES_USER=admin
POSTGRES_PASSWORD=some_password
POSTGRES_DB_PORT=5432

# pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@gmail.com
PGADMIN_DEFAULT_PASSWORD=admin
```

### 2. Build & Start Containers

```sh
  docker-compose up --build
```

Once running, the API will be available at:

- **http://127.0.0.1:8000/**
- PostgreSQL on port `5432`
- **pgAdmin** on `http://127.0.0.1:3333/`

To stop the containers:

```sh
  docker-compose down
```

---

## Authentication (Email & JWT)

This API uses **email-based authentication with JWT tokens**.

### 1. Register a New User

**Endpoint:** `POST /api/register/`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "password123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response:**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe"
}
```

### 2. Obtain JWT Token

**Endpoint:** `POST /api/token/`

**Request:**

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**

```json
{
  "access": "your_access_token",
  "refresh": "your_refresh_token"
}
```

Use the `access` token in the **Authorization** header:

```
Authorization: Bearer your_access_token
```

### 3. Refresh Token

**Endpoint:** `POST /api/token/refresh/`

**Request:**

```json
{
  "refresh": "your_refresh_token"
}
```

**Response:**

```json
{
  "access": "new_access_token"
}
```

---

## API Endpoints

### 1. Astronomy Shows

- **Get all shows:** `GET /api/astronomy_shows/`
- **Get show details:** `GET /api/astronomy_shows/{id}/`
- **Create a show:** `POST /api/astronomy_shows/`

  ```json
  {
    "title": "The Universe",
    "description": "A journey through space",
    "poster": "https://example.com/image.jpg"
  }
  ```

- **Update a show:** `PUT /api/astronomy_shows/{id}/`
- **Delete a show:** `DELETE /api/astronomy_shows/{id}/`

### 2. Reservations

- **List user reservations:** `GET /api/reservations/`
- **Create a reservation:** `POST /api/reservations/`

  ```json
  {
    "tickets": [
      {
        "show_session": 1,
        "row": 5,
        "seat": 10
      }
    ]
  }
  ```

  **Response:**

  ```json
  {
    "checkout_url": "https://stripe.com/payment"
  }
  ```

  Redirect the user to `checkout_url` for payment.

- **Get reservation details:** `GET /api/reservations/{id}/`

### 3. Show Sessions

- **List sessions:** `GET /api/show_sessions/`
- **Create session:** `POST /api/show_sessions/`

  ```json
  {
    "show_time": "2025-03-01T15:00:00",
    "duration": "01:30:00",
    "ticket_price": "50.00",
    "astronomy_show": 1,
    "planetarium_dome": 2
  }
  ```

### 4. Payments

- **Stripe Success:** `GET /api/stripe/success/`
- **Stripe Cancel:** `GET /api/stripe/cancel/`

---

## Celery & Background Tasks

Celery is used for:

- Sending **email verifications**.
- Running **asynchronous tasks** without blocking the main app.

Run Celery worker manually:

```sh
  celery -A DjangoCore worker --loglevel=info
```
