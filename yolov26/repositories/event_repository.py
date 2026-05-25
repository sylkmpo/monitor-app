from typing import Callable, Optional


class EventRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def today_count(self) -> int:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM alert_events WHERE DATE(created_at) = CURDATE()")
                return cursor.fetchone()["total"] or 0
        finally:
            conn.close()

    def stats(self) -> dict:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total_events FROM alert_events")
                total = cursor.fetchone()["total_events"] or 0

                cursor.execute("SELECT COUNT(*) AS today_events FROM alert_events WHERE DATE(created_at) = CURDATE()")
                today = cursor.fetchone()["today_events"] or 0

                cursor.execute("SELECT risk_level, COUNT(*) AS count FROM alert_events GROUP BY risk_level")
                risk_counts = {row["risk_level"]: row["count"] for row in cursor.fetchall()}

                cursor.execute(
                    "SELECT event_type, COUNT(*) AS count FROM alert_events GROUP BY event_type ORDER BY count DESC LIMIT 10"
                )
                top_event_types = cursor.fetchall()

            return {
                "total_events": total,
                "today_events": today,
                "critical_events": risk_counts.get("critical", 0),
                "high_events": risk_counts.get("high", 0),
                "risk_counts": risk_counts,
                "top_event_types": top_event_types,
            }
        finally:
            conn.close()

    def list_events(
        self,
        camera_id: Optional[int] = None,
        event_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        status_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        conditions = []
        params = []

        if camera_id:
            conditions.append("camera_id = %s")
            params.append(camera_id)
        if event_type:
            conditions.append("event_type = %s")
            params.append(event_type)
        if risk_level:
            conditions.append("risk_level = %s")
            params.append(risk_level)
        if status_filter:
            conditions.append("status = %s")
            params.append(status_filter)

        where_sql = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size

        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT COUNT(*) AS total FROM alert_events{where_sql}", tuple(params))
                total = cursor.fetchone()["total"] or 0

                cursor.execute(
                    f"SELECT * FROM alert_events{where_sql} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    tuple(params + [page_size, offset]),
                )
                rows = cursor.fetchall()

            for row in rows:
                for field in ("event_start_time", "event_end_time", "created_at"):
                    if row.get(field):
                        row[field] = row[field].strftime("%Y-%m-%d %H:%M:%S")

            return {"total": total, "page": page, "page_size": page_size, "items": rows}
        finally:
            conn.close()

    def update_status(self, event_id: int, status: str) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE alert_events SET status=%s WHERE id=%s", (status, event_id))
                updated = cursor.rowcount
            conn.commit()
            return updated > 0
        finally:
            conn.close()
