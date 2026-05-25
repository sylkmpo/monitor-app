import json
from typing import Callable


class RuleRepository:
    def __init__(self, get_connection: Callable):
        self.get_connection = get_connection

    def _normalize_rule(self, row):
        if not row:
            return row
        try:
            config = json.loads(row.get("config_json") or "{}")
        except Exception:
            config = {}
        row["enabled"] = bool(row.get("enabled"))
        row["config"] = config
        row.pop("config_json", None)
        for field in ("created_at", "updated_at"):
            if row.get(field):
                row[field] = row[field].strftime("%Y-%m-%d %H:%M:%S")
        return row

    def list_by_camera(self, camera_id: int):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM camera_rules WHERE camera_id = %s ORDER BY id DESC",
                    (camera_id,),
                )
                return [self._normalize_rule(rule) for rule in cursor.fetchall()]
        finally:
            conn.close()

    def camera_exists(self, camera_id: int) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM cameras WHERE id = %s", (camera_id,))
                return cursor.fetchone() is not None
        finally:
            conn.close()

    def create(self, camera_id: int, rule_type: str, enabled: bool, rule_name: str, risk_level: str, config: dict) -> int:
        final_rule_name = rule_name.strip() if rule_name.strip() else rule_type
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO camera_rules (camera_id, rule_type, enabled, rule_name, risk_level, config_json)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        camera_id,
                        rule_type,
                        int(enabled),
                        final_rule_name,
                        risk_level,
                        json.dumps(config, ensure_ascii=False),
                    ),
                )
                rule_id = cursor.lastrowid
            conn.commit()
            return rule_id
        finally:
            conn.close()

    def update(self, rule_id: int, rule_type: str, enabled: bool, rule_name: str, risk_level: str, config: dict) -> bool:
        final_rule_name = rule_name.strip() if rule_name.strip() else rule_type
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE camera_rules
                    SET rule_type=%s, enabled=%s, rule_name=%s, risk_level=%s, config_json=%s
                    WHERE id=%s
                    """,
                    (
                        rule_type,
                        int(enabled),
                        final_rule_name,
                        risk_level,
                        json.dumps(config, ensure_ascii=False),
                        rule_id,
                    ),
                )
                updated = cursor.rowcount
            conn.commit()
            return updated > 0
        finally:
            conn.close()

    def delete(self, rule_id: int) -> bool:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM camera_rules WHERE id = %s", (rule_id,))
                deleted = cursor.rowcount
            conn.commit()
            return deleted > 0
        finally:
            conn.close()

    def active_count(self) -> int:
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) AS total FROM camera_rules WHERE enabled = 1")
                return cursor.fetchone()["total"] or 0
        finally:
            conn.close()
