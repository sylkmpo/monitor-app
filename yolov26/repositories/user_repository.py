from typing import Callable, Optional


class UserRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def find_by_username(self, username: str) -> Optional[dict]:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                return cursor.fetchone()
        finally:
            conn.close()

    def get_password_hash(self, username: str) -> Optional[str]:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                return user["password_hash"] if user else None
        finally:
            conn.close()

    def update_password_hash(self, username: str, password_hash: str) -> None:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE users SET password_hash = %s WHERE username = %s",
                    (password_hash, username),
                )
            conn.commit()
        finally:
            conn.close()
