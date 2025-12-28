"""Tests for the FastAPI application endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from logging_lab.app import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_read_root(client: TestClient) -> None:
    """Test the root endpoint returns Hello World."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_health_check(client: TestClient) -> None:
    """Test the ping endpoint returns pong."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == "pong"


def test_read_item_without_query(client: TestClient) -> None:
    """Test reading an item without query parameter."""
    response = client.get("/items/42")
    assert response.status_code == 200
    assert response.json() == {"item_id": 42, "q": None}


def test_read_item_with_query(client: TestClient) -> None:
    """Test reading an item with query parameter."""
    response = client.get("/items/1?q=test")
    assert response.status_code == 200
    assert response.json() == {"item_id": 1, "q": "test"}


def test_invalid_endpoint_raises_error(client: TestClient) -> None:
    """Test that /invalid returns 400 with error message."""
    response = client.get("/invalid")
    assert response.status_code == 400
    assert "intentional error" in response.json()["detail"]


def test_exception_demo(client: TestClient) -> None:
    """Test that /exception handles and returns error info."""
    response = client.get("/exception")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error_handled"
    assert "Simulated error" in data["message"]


@pytest.mark.slow
def test_external_api_call(client: TestClient) -> None:
    """Test external API call to httpbin.org."""
    response = client.get("/external-api")
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "httpbin.org"
    assert data["status_code"] == 200
    assert "origin" in data


def test_external_api_call_mocked(client: TestClient) -> None:
    """Test external API call with mocked httpx."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"origin": "1.2.3.4"}
    mock_response.raise_for_status.return_value = None

    with patch("logging_lab.app.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance

        response = client.get("/external-api")
        assert response.status_code == 200
        assert response.json()["origin"] == "1.2.3.4"
