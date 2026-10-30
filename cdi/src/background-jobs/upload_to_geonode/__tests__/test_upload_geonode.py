import os
import pytest
from unittest import mock
from ..upload_to_geonode_job import (
    write_failure_message,
    upload_to_geonode,
    get_all_dataset_files,
    update_dataset_metadata,
    tracking_upload_progress,
    process_batch,
    order_retries_first,
    load_failed_uploads,
    save_failed_uploads,
    UploadCircuitBreaker,
    MAX_CONSECUTIVE_FAILURES,
)
from .. import upload_to_geonode_job


# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    mock_url = "http://test.geonode.com/"
    mock_username = "testuser"
    mock_password = "secret"
    monkeypatch.setenv("GEONODE_URL", mock_url)
    monkeypatch.setenv("GEONODE_USERNAME", mock_username)
    monkeypatch.setenv("GEONODE_PASSWORD", mock_password)
    upload_to_geonode_job.geonode_url = mock_url
    upload_to_geonode_job.username = mock_username
    upload_to_geonode_job.password = mock_password


# Mock open function to avoid actual file operations
@pytest.fixture
def mock_open():
    with mock.patch(
        "builtins.open",
        mock.mock_open(read_data="data")
    ) as mock_file:
        yield mock_file


# Mock requests.post and requests.get
@pytest.fixture
def mock_requests():
    with mock.patch("requests.post") as mock_post, mock.patch(
        "requests.get"
    ) as mock_get, mock.patch("requests.patch") as mock_patch:
        yield mock_post, mock_get, mock_patch


def test_write_failure_message(capfd):
    response = mock.Mock(status_code=400, text="Bad Request")
    write_failure_message(response)
    captured = capfd.readouterr()
    assert "Request failed." in captured.out
    assert "Status Code: 400" in captured.out
    assert "Response: Bad Request" in captured.out


def test_upload_to_geonode(mock_open, mock_requests):
    mock_post, _, _ = mock_requests
    mock_response = mock.Mock(
        status_code=201, json=mock.Mock(return_value={"execution_id": "123"})
    )
    mock_post.return_value = mock_response

    execution_id = upload_to_geonode("/path/to/file.tif")
    assert execution_id == "123"


def test_get_all_dataset_files(monkeypatch):
    def mock_os_walk(path):
        return [("/path/to/datasets", [], ["file1.tif", "file2.tif"])]

    monkeypatch.setattr(os, "walk", mock_os_walk)
    files = get_all_dataset_files()
    assert files == [
        "/path/to/datasets/file1.tif",
        "/path/to/datasets/file2.tif"
    ]


def test_update_dataset_metadata(mock_requests):
    _, _, mock_patch = mock_requests
    mock_response = mock.Mock(status_code=200)
    mock_patch.return_value = mock_response

    update_dataset_metadata(
        "dataset_id",
        {
            "advertised": False,
            "is_published": False
        }
    )


def test_tracking_upload_progress(mock_requests):
    _, mock_get, mock_patch = mock_requests
    mock_response = mock.Mock(
        status_code=200,
        json=mock.Mock(
            return_value={
                "request": {
                    "status": "finished",
                    "output_params": {"resources": [{"id": "dataset_id"}]},
                }
            }
        ),
    )
    mock_get.return_value = mock_response
    mock_patch.return_value = mock.Mock(status_code=200)

    tracking_upload_progress("123")


def test_tracking_upload_progress_polls_until_finished(mock_requests):
    """A pending import is polled in a loop, not by recursing."""
    _, mock_get, mock_patch = mock_requests

    def response(status):
        return mock.Mock(
            status_code=200,
            json=mock.Mock(
                return_value={
                    "request": {
                        "status": status,
                        "output_params": {
                            "resources": [{"id": "dataset_id"}]
                        },
                    }
                }
            ),
        )

    mock_get.side_effect = [
        response("running"),
        response("running"),
        response("finished"),
    ]
    mock_patch.return_value = mock.Mock(status_code=200)

    with mock.patch("time.sleep"):
        tracking_upload_progress("123", interval=0)

    assert mock_get.call_count == 3
    assert mock_patch.call_count == 1


def test_tracking_upload_progress_times_out(mock_requests):
    """A never-finishing import raises instead of spinning forever."""
    _, mock_get, _ = mock_requests
    mock_get.return_value = mock.Mock(
        status_code=200,
        json=mock.Mock(return_value={"request": {"status": "running"}}),
    )

    with mock.patch("time.sleep"):
        with pytest.raises(TimeoutError):
            tracking_upload_progress("123", timeout=0.1, interval=0)


def test_process_batch_trips_circuit_breaker(monkeypatch):
    """A sustained outage aborts instead of churning through every file."""
    monkeypatch.setattr(
        upload_to_geonode_job,
        "upload_to_geonode",
        mock.Mock(side_effect=RuntimeError("Connection refused")),
    )
    failed = set()
    batch = [f"/data/CDI/f_{i}.tif" for i in range(20)]

    with pytest.raises(UploadCircuitBreaker):
        process_batch(batch, {}, failed)

    # Stopped at the limit rather than attempting all 20 files.
    assert len(failed) == MAX_CONSECUTIVE_FAILURES


def test_process_batch_success_resets_failure_streak(monkeypatch):
    """An intermittent failure must not trip the breaker."""
    outcomes = [RuntimeError("boom"), None, RuntimeError("boom"), None]

    def upload(path):
        outcome = outcomes.pop(0)
        if outcome:
            raise outcome
        return "exec-id"

    monkeypatch.setattr(upload_to_geonode_job, "upload_to_geonode", upload)
    monkeypatch.setattr(
        upload_to_geonode_job, "tracking_upload_progress", mock.Mock()
    )
    failed = set()
    batch = [f"/data/CDI/f_{i}.tif" for i in range(4)]

    streak = process_batch(batch, {}, failed)

    # Streak reset by the trailing success, so the breaker never trips.
    assert streak == 0
    assert failed == {"/data/CDI/f_0.tif", "/data/CDI/f_2.tif"}


def test_order_retries_first():
    """Previously failed files are uploaded before the rest."""
    files = ["/d/a.tif", "/d/b.tif", "/d/c.tif"]
    assert order_retries_first(files, {"/d/c.tif"}) == [
        "/d/c.tif", "/d/a.tif", "/d/b.tif"
    ]


def test_failure_log_roundtrip(tmp_path):
    """Failures survive to the next run; a missing log is not an error."""
    log_path = str(tmp_path / "nested" / "upload_failures.json")
    assert load_failed_uploads(log_path) == set()

    save_failed_uploads({"/d/b.tif", "/d/a.tif"}, log_path)
    assert load_failed_uploads(log_path) == {"/d/a.tif", "/d/b.tif"}


def test_failure_log_tolerates_corruption(tmp_path, capfd):
    """A truncated log is reported, not fatal."""
    log_path = tmp_path / "upload_failures.json"
    log_path.write_text("{not json")
    assert load_failed_uploads(str(log_path)) == set()
    assert "Could not read failure log" in capfd.readouterr().out


def test_main(mock_open, mock_requests, monkeypatch):
    mock_post, mock_get, mock_patch = mock_requests

    def mock_os_walk(path):
        return [("/path/to/datasets", [], ["file1.tif", "file2.tif"])]

    monkeypatch.setattr(os, "walk", mock_os_walk)
    mock_response = mock.Mock(
        status_code=201, json=mock.Mock(return_value={"execution_id": "123"})
    )
    mock_post.return_value = mock_response
    mock_get.return_value = mock.Mock(
        status_code=200,
        json=mock.Mock(
            return_value={
                "request": {
                    "status": "finished",
                    "output_params": {"resources": [{"id": "dataset_id"}]},
                }
            }
        ),
    )
    mock_patch.return_value = mock.Mock(status_code=200)


def test_every_http_call_sets_a_timeout(mock_requests, tmp_path):
    """No request may block forever.

    requests defaults to no timeout, so a server that stops answering hangs the
    job indefinitely. That silently defeats both POLL_TIMEOUT_SECONDS (checked
    only between requests) and the circuit breaker (which needs an exception to
    count a failure), so an outage becomes a stalled run instead of an abort.
    """
    mock_post, mock_get, mock_patch = mock_requests
    mock_post.return_value = mock.Mock(
        status_code=201, json=mock.Mock(return_value={"execution_id": 7})
    )
    mock_get.return_value = mock.Mock(
        status_code=200,
        json=mock.Mock(return_value={
            "request": {
                "status": "finished",
                "output_params": {"resources": [{"id": 1}]},
            },
            "objects": [],
        }),
    )
    mock_patch.return_value = mock.Mock(status_code=200)

    # A real file, not the mock_open fixture: that fixture patches
    # builtins.open globally, which would break get_categories' JSON read.
    raster = tmp_path / "f.tif"
    raster.write_bytes(b"not-a-real-raster")

    upload_to_geonode(str(raster))
    tracking_upload_progress(execution_id=7, taxonomy="cdi", categories={})
    update_dataset_metadata(1, {})
    upload_to_geonode_job.get_categories(
        "http://example.test/api/categories/",
        file_name=str(tmp_path / "categories.json"),
    )

    for verb, mocked in (
        ("post", mock_post), ("get", mock_get), ("patch", mock_patch),
    ):
        assert mocked.call_args_list, "requests.{} was never called".format(verb)
        for call in mocked.call_args_list:
            assert call.kwargs.get("timeout") is not None, (
                "requests.{} called without a timeout: {}".format(verb, call))
