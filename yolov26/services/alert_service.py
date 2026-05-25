import os
from typing import List, Optional


class AlertService:
    def __init__(self, alert_repository, snapshot_dir: str, logger, file_exists=None, file_remove=None):
        self.alert_repository = alert_repository
        self.snapshot_dir = snapshot_dir
        self.logger = logger
        self.file_exists = file_exists or os.path.exists
        self.file_remove = file_remove or os.remove

    def create_alert(self, alert_payload: dict) -> dict:
        return self.alert_repository.create_with_event(alert_payload)

    def list_alerts(self, cam_name: Optional[str] = None):
        return self.alert_repository.list_alerts(cam_name)

    def delete_alerts(self, alert_ids: List[int]) -> int:
        if not alert_ids:
            return 0

        image_filenames = self.alert_repository.get_image_filenames(alert_ids)
        for image_filename in image_filenames:
            file_path = os.path.join(self.snapshot_dir, image_filename)
            if self.file_exists(file_path):
                try:
                    self.file_remove(file_path)
                except OSError:
                    self.logger.warning(f"Failed to remove snapshot file: {file_path}")

        return self.alert_repository.delete_by_ids(alert_ids)
