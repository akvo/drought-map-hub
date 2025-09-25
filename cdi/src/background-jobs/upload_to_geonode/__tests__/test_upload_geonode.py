import os
import pytest
from unittest import mock
from ..upload_to_geonode_job import (
    write_failure_message,
    upload_to_geonode,
    get_all_dataset_files,
    update_dataset_metadata,
    tracking_upload_progress,
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
