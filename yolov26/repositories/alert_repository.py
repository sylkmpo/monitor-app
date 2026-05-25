from typing import Callable, List, Optional


class AlertRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def create_with_event(self, alert: dict) -> dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO alerts (cam_name, alert_type, image_filename) VALUES (%s, %s, %s)",
                    (alert["cam_name"], alert["alert_type"], alert["image_filename"]),
                )
                alert_id = cursor.lastrowid

                event_type = alert.get("event_type") or "person_detected"
                event_name = alert.get("event_name") or alert["alert_type"]
                camera_id = alert.get("camera_id")
                if camera_id is None:
                    cursor.execute("SELECT id FROM cameras WHERE name = %s LIMIT 1", (alert["cam_name"],))
                    camera = cursor.fetchone()
                    camera_id = camera["id"] if camera else None

                cursor.execute(
                    """
                    INSERT INTO alert_events (
                        camera_id, cam_name, event_type, event_name, risk_level, confidence,
                        person_count, image_filename, region_name, event_start_time,
                        event_end_time, duration_seconds
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        camera_id,
                        alert["cam_name"],
                        event_type,
                        event_name,
                        alert.get("risk_level") or "medium",
                        alert.get("confidence") or 0,
                        alert.get("person_count") or 0,
                        alert["image_filename"],
                        alert.get("region_name"),
                        alert.get("event_start_time"),
                        alert.get("event_end_time"),
                        alert.get("duration_seconds") or 0,
                    ),
                )
                event_id = cursor.lastrowid
            conn.commit()
            return {"alert_id": alert_id, "event_id": event_id}
        finally:
            conn.close()

    def list_alerts(self, cam_name: Optional[str] = None):
        query = "SELECT * FROM alerts"
        params = []

        if cam_name:
            query += " WHERE cam_name = %s"
            params.append(cam_name)

        query += " ORDER BY timestamp DESC LIMIT 100"

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, tuple(params))
                alerts = cursor.fetchall()
            for alert in alerts:
                if alert.get("timestamp"):
                    alert["timestamp"] = alert["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            return alerts
        finally:
            conn.close()

    def get_image_filenames(self, alert_ids: List[int]) -> List[str]:
        if not alert_ids:
            return []
        placeholders = ",".join(["%s"] * len(alert_ids))
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT image_filename FROM alerts WHERE id IN ({placeholders})",
                    tuple(alert_ids),
                )
                return [row["image_filename"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def delete_by_ids(self, alert_ids: List[int]) -> int:
        if not alert_ids:
            return 0
        placeholders = ",".join(["%s"] * len(alert_ids))
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"DELETE FROM alerts WHERE id IN ({placeholders})", tuple(alert_ids))
                deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()
