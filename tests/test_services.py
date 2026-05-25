from services.alert_service import AlertService


class FakeAlertRepository:
    def __init__(self):
        self.deleted_ids = []

    def get_image_filenames(self, alert_ids):
        return ["snapshot-a.jpg", "missing.jpg"]

    def delete_by_ids(self, alert_ids):
        self.deleted_ids = list(alert_ids)
        return len(alert_ids)


class FakeLogger:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(message)


def test_alert_service_deletes_snapshot_files_and_records(tmp_path):
    repository = FakeAlertRepository()
    removed_files = []
    service = AlertService(
        repository,
        str(tmp_path),
        FakeLogger(),
        file_exists=lambda path: path.endswith("snapshot-a.jpg"),
        file_remove=removed_files.append,
    )

    deleted_count = service.delete_alerts([1, 2])

    assert deleted_count == 2
    assert removed_files == [str(tmp_path / "snapshot-a.jpg")]
    assert repository.deleted_ids == [1, 2]
