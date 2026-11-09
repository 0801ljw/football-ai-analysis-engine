import pytest

from app.desktop_settings import SystemApiKeyStore


class MemoryKeyring:
    def __init__(self):
        self.values = {}

    def get_password(self, service, username):
        return self.values.get((service, username))

    def set_password(self, service, username, password):
        self.values[service, username] = password

    def delete_password(self, service, username):
        self.values.pop((service, username), None)


@pytest.fixture(autouse=True)
def memory_keyring(monkeypatch):
    """Unit tests must never read/write the developer's real credential store."""
    backend = MemoryKeyring()
    monkeypatch.setattr(SystemApiKeyStore, "_native_backend", lambda self: backend)
    return backend
