import time
from typing import Callable, Optional


class CameraRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def list_all(self):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM cameras")
                return cursor.fetchall()
        finally:
            conn.close()

    def input_source_exists(self, input_source: str, exclude_id: Optional[int] = None) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                if exclude_id is None:
                    cursor.execute("SELECT id FROM cameras WHERE input_source = %s", (input_source,))
                else:
                    cursor.execute(
                        "SELECT id FROM cameras WHERE input_source = %s AND id != %s",
                        (input_source, exclude_id),
                    )
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def create(self, name: str, model: str, input_source: str) -> int:
        auto_stream_path = f"cam_{int(time.time())}"
        final_name = name.strip() if name.strip() else f"未命名_{auto_stream_path[-4:]}"
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO cameras (name, model, input_source, stream_path) VALUES (%s, %s, %s, %s)",
                    (final_name, model, input_source, auto_stream_path),
                )
                camera_id = cursor.lastrowid
            conn.commit()
            return camera_id
        finally:
            conn.close()

    def update(self, camera_id: int, name: str, model: str, input_source: str) -> None:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM cameras WHERE id = %s", (camera_id,))
                old_cam = cursor.fetchone()
                old_name = old_cam["name"] if old_cam else None

                cursor.execute(
                    "UPDATE cameras SET name=%s, model=%s, input_source=%s WHERE id=%s",
                    (name, model, input_source, camera_id),
                )

                if old_name and old_name != name:
                    cursor.execute("UPDATE alerts SET cam_name=%s WHERE cam_name=%s", (name, old_name))

            conn.commit()
        finally:
            conn.close()

    def delete(self, camera_id: int) -> None:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM cameras WHERE id = %s", (camera_id,))
            conn.commit()
        finally:
            conn.close()

    def update_status(self, camera_id: int, status: str) -> None:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE cameras SET status=%s WHERE id=%s", (status, camera_id))
            conn.commit()
        finally:
            conn.close()

    def count_summary(self) -> dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total, SUM(status = 'online') AS online_count FROM cameras")
                row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "online_count": row["online_count"] or 0,
            }
        finally:
            conn.close()
