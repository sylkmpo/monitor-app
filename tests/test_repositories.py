from datetime import datetime

from repositories.rule_repository import RuleRepository
from repositories.user_repository import UserRepository


class FakeUserCursor:
    def __init__(self, state):
        self.state = state
        self._result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        if "SELECT * FROM users WHERE username" in sql:
            self._result = self.state["users"].get(params[0])
        elif "SELECT password_hash FROM users WHERE username" in sql:
            user = self.state["users"].get(params[0])
            self._result = {"password_hash": user["password_hash"]} if user else None
        elif "UPDATE users SET password_hash" in sql:
            password_hash, username = params
            self.state["users"][username]["password_hash"] = password_hash
            self._result = None
        else:
            raise AssertionError(f"Unexpected SQL: {sql}")

    def fetchone(self):
        return self._result


class FakeUserConnection:
    def __init__(self, state):
        self.state = state
        self.committed = False
        self.closed = False

    def cursor(self):
        return FakeUserCursor(self.state)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_user_repository_reads_and_updates_password_hash():
    state = {
        "users": {
            "admin": {"id": 1, "username": "admin", "password_hash": "old", "role": "admin"}
        }
    }
    repo = UserRepository(lambda: FakeUserConnection(state))

    assert repo.find_by_username("admin")["role"] == "admin"
    assert repo.get_password_hash("admin") == "old"

    repo.update_password_hash("admin", "new")

    assert repo.get_password_hash("admin") == "new"


def test_rule_repository_normalizes_config_and_datetimes():
    repo = RuleRepository(lambda: None)
    row = {
        "id": 1,
        "enabled": 1,
        "config_json": '{"threshold": 3}',
        "created_at": datetime(2026, 5, 10, 9, 30, 0),
        "updated_at": datetime(2026, 5, 10, 9, 31, 0),
    }

    normalized = repo._normalize_rule(row)

    assert normalized["enabled"] is True
    assert normalized["config"] == {"threshold": 3}
    assert normalized["created_at"] == "2026-05-10 09:30:00"
    assert "config_json" not in normalized
