import pytest
from unittest import mock

from .. import sync_geonode_publications_job as job


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setattr(job, "geonode_url", "http://test.geonode.com")
    monkeypatch.setattr(job, "username", "testuser")
    monkeypatch.setattr(job, "password", "secret")
    monkeypatch.setattr(job, "hub_url", "http://test.hub.com")
    monkeypatch.setattr(job, "hub_api_key", "test-key")


def resource(**overrides):
    base = {
        "pk": 42,
        "title": "CDI_202401",
        "date": "2024-01-01T00:00:00Z",
        "detail_url": "http://test.geonode.com/datasets/42",
        "embed_url": "",
        "thumbnail_url": None,
        "download_url": "http://test.geonode.com/download/42",
        "filesize": 1234,
    }
    base.update(overrides)
    return base


def test_build_payload_maps_fields_and_drops_blanks():
    payload = job.build_payload(resource(), "cdi-raster-map")
    assert payload == {
        "geonode_id": 42,
        "category": "cdi-raster-map",
        "title": "CDI_202401",
        "year_month": "2024-01-01",
        "detail_url": "http://test.geonode.com/datasets/42",
        "download_url": "http://test.geonode.com/download/42",
        "file_size": 1234,
    }


def test_build_payload_normalises_day_and_rejects_bad_input():
    assert job.build_payload(
        resource(date="2024-03-17"), "spi-raster-map"
    )["year_month"] == "2024-03-01"
    assert job.build_payload(resource(date=""), "spi-raster-map") is None
    assert job.build_payload(resource(title=None), "spi-raster-map") is None


def test_parse_targets_single_host_strips_trailing_slash(monkeypatch):
    monkeypatch.setattr(job, "hub_url", "https://cdie.ndrma.org.sz/")
    assert job.parse_targets() == [("https://cdie.ndrma.org.sz", "test-key")]


def test_parse_targets_pairs_comma_separated_hosts(monkeypatch):
    monkeypatch.setattr(
        job, "hub_url", "https://staging.example.org,https://prod.example.org"
    )
    monkeypatch.setattr(job, "hub_api_key", "staging-key,prod-key")
    assert job.parse_targets() == [
        ("https://staging.example.org", "staging-key"),
        ("https://prod.example.org", "prod-key"),
    ]


def test_parse_targets_refuses_count_mismatch(monkeypatch):
    """A short key list must abort, never zip one host onto another's key."""
    monkeypatch.setattr(
        job, "hub_url", "https://staging.example.org,https://prod.example.org"
    )
    monkeypatch.setattr(job, "hub_api_key", "only-one-key")
    with pytest.raises(SystemExit):
        job.parse_targets()


def test_parse_targets_empty_when_unset(monkeypatch):
    monkeypatch.setattr(job, "hub_url", None)
    assert job.parse_targets() == []
    monkeypatch.setattr(job, "hub_url", "https://prod.example.org")
    monkeypatch.setattr(job, "hub_api_key", "")
    assert job.parse_targets() == []


def test_push_publication_sends_api_key():
    with mock.patch("requests.post") as post:
        post.return_value = mock.Mock(status_code=201)
        target = ("http://test.hub.com", "test-key")
        assert job.push_publication({"geonode_id": 42}, target) is True
    args, kwargs = post.call_args
    assert args[0] == "http://test.hub.com/api/v1/geonode/publications"
    assert kwargs["headers"] == {"X-API-Key": "test-key"}
    assert kwargs["verify"] is True


def test_push_publication_reports_failure():
    with mock.patch("requests.post") as post:
        post.return_value = mock.Mock(status_code=403, text="Forbidden")
        target = ("http://test.hub.com", "test-key")
        assert job.push_publication({"geonode_id": 42}, target) is False


def test_sync_category_pages_until_total_reached():
    pages = [
        {"resources": [resource(pk=i + 1) for i in range(job.PAGE_SIZE)],
         "total": job.PAGE_SIZE + 1},
        {"resources": [resource(pk=99)], "total": job.PAGE_SIZE + 1},
    ]
    targets = [("http://test.hub.com", "test-key")]
    with mock.patch.object(job, "fetch_resources", side_effect=pages) as fetch:
        with mock.patch.object(job, "push_publication", return_value=True):
            synced, failed = job.sync_category("cdi-raster-map", targets)
    assert (synced, failed) == (job.PAGE_SIZE + 1, 0)
    assert fetch.call_count == 2


def test_sync_category_pushes_each_resource_to_every_target():
    page = {"resources": [resource(pk=1), resource(pk=2)], "total": 2}
    targets = [("http://staging", "key-a"), ("http://prod", "key-b")]
    with mock.patch.object(job, "fetch_resources", return_value=page):
        with mock.patch.object(
            job, "push_publication", return_value=True
        ) as push:
            synced, failed = job.sync_category("cdi-raster-map", targets)
    assert (synced, failed) == (4, 0)
    assert [call.args[1] for call in push.call_args_list] == targets * 2


def test_sync_category_keeps_going_when_one_target_fails():
    """A dead staging host must not stop the push to production."""
    page = {"resources": [resource(pk=1)], "total": 1}
    targets = [("http://staging", "key-a"), ("http://prod", "key-b")]
    outcomes = [job.requests.exceptions.ConnectionError("down"), True]
    with mock.patch.object(job, "fetch_resources", return_value=page):
        with mock.patch.object(
            job, "push_publication", side_effect=outcomes
        ) as push:
            synced, failed = job.sync_category("cdi-raster-map", targets)
    assert (synced, failed) == (1, 1)
    assert push.call_count == 2


def test_main_skips_when_hub_not_configured(monkeypatch, capfd):
    monkeypatch.setattr(job, "hub_url", None)
    with mock.patch.object(job, "sync_category") as sync:
        job.main()
    sync.assert_not_called()
    assert "skipping portal sync" in capfd.readouterr().out
