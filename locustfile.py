"""
Locust load testing file for logging-lab API.

Run with:
    uv run locust -f locustfile.py --headless --users 10 --spawn-rate 1 -H http://localhost:5002

Or interactively:
    uv run locust -f locustfile.py -H http://localhost:5002
"""

from __future__ import annotations

import time
from typing import Any, Callable

from locust import HttpUser, task, between


class QuickstartUser(HttpUser):
    wait_time: Callable[[Any], float] = between(1, 5)

    @task
    def hello_world(self) -> None:
        self.client.get("/", name="/home")

    @task
    def health_check(self) -> None:
        self.client.get("/ping", name="/ping")

    @task
    def invalid(self) -> None:
        self.client.get("/invalid", name="/invalid")

    @task(3)
    def view_items(self) -> None:
        for item_id in range(10):
            self.client.get(f"/items/{item_id}", name="/items")
            time.sleep(1)

    @task(3)
    def make_external_api_calls(self) -> None:
        self.client.get("/external-api", name="/external-api")
        time.sleep(1)

    @task(2)
    def exception_demo(self) -> None:
        self.client.get("/exception", name="/exception")
        time.sleep(1)
