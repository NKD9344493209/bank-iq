"""Every test module builds its own TestClient(app); this fixture logs a test user into each of them
so the suite runs with authentication ON (the production default)."""
import os
import tempfile

os.environ.setdefault("VASOOL_DB", os.path.join(tempfile.mkdtemp(), "test.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def _login(client: TestClient, login: str = "tester@example.com"):
    r = client.post("/api/auth/signup", json={"login": login, "name": "Tester", "password": "correct horse"})
    if r.status_code == 409:
        r = client.post("/api/auth/login", json={"login": login, "password": "correct horse"})
    assert r.status_code == 200, r.text
    # TestClient keeps the Set-Cookie automatically


@pytest.fixture(autouse=True, scope="session")
def _auth_all_clients():
    import gc
    for obj in gc.get_objects():
        if isinstance(obj, TestClient):
            try:
                _login(obj)
            except Exception:
                pass
    yield
