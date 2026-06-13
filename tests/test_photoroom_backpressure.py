from app.agent import pipeline
from app.api_clients.photoroom import PhotoRoomClient


def test_photoroom_provider_enables_batch_parallelism(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "matting_provider", "photoroom")
    monkeypatch.setattr(pipeline.settings, "compositing_provider", "local")
    monkeypatch.setattr(pipeline.settings, "photoroom_max_concurrency", 8)

    assert pipeline._max_parallel_items(50) == 8


def test_local_provider_keeps_batch_serial(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "matting_provider", "local")
    monkeypatch.setattr(pipeline.settings, "compositing_provider", "local")
    monkeypatch.setattr(pipeline.settings, "photoroom_max_concurrency", 8)

    assert pipeline._max_parallel_items(50) == 1


def test_photoroom_status_exposes_backpressure_defaults(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "photoroom_max_requests_per_minute", 55)
    monkeypatch.setattr(pipeline.settings, "photoroom_max_concurrency", 8)
    monkeypatch.setattr(pipeline.settings, "photoroom_429_max_retries", 4)

    status = PhotoRoomClient().status()

    assert status["rate_limits"] == {
        "max_requests_per_minute": 55,
        "max_concurrency": 8,
        "too_many_requests_retries": 4,
    }
