# conftest.py
# (raíz del proyecto)

import pytest

from django.contrib.auth.models import User

from rest_framework.test import APIClient

from rest_framework_simplejwt.tokens import (
    RefreshToken,
)


# ── Cliente API sin autenticación ────────────────────────────────


@pytest.fixture
def api_client():
    """
    Cliente DRF sin autenticación.
    """

    return APIClient()


# ── Usuario de prueba ────────────────────────────────────────────


@pytest.fixture
def user(db):
    """
    Usuario básico para pruebas.
    """

    return User.objects.create_user(
        username="test_empleado",
        email="empleado@encomiendas.pe",
        password="test1234",
    )


# ── Cliente autenticado con JWT ──────────────────────────────────


@pytest.fixture
def auth_client(api_client, user):
    """
    Cliente DRF con JWT válido.
    """

    refresh = RefreshToken.for_user(user)

    api_client.credentials(HTTP_AUTHORIZATION=(f"Bearer {refresh.access_token}"))

    return api_client
