"""The unsupported Explore diagnostic stays bounded and exposes no raw responses."""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from urllib.parse import parse_qs

import pytest

from scripts.probe_explore import probe, request_body


def future_date():
    return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")


def test_probe_request_preserves_upstream_wire_shape():
    departure = future_date()
    envelope = json.loads(parse_qs(request_body("JAX", departure))["f.req"][0])
    outer = json.loads(envelope[1])
    search = outer[3]
    assert search[2] == 2
    assert search[5] == 1
    assert search[6] == [1, 0, 0, 0]
    segment = search[13][0]
    assert segment[0] == [[["JAX", 0]]]
    assert segment[1] == [[["/m/02j71", 6]]]
    assert segment[6] == departure


@pytest.mark.parametrize("extended,posts,gets", [(False, 1, 0), (True, 3, 1)])
def test_rejected_probe_is_bounded_and_sanitized(monkeypatch, extended, posts, gets):
    client = MagicMock()
    response = client.post.return_value
    response.status_code = 200
    response.text = json.dumps([["wrb.fr", None, None, None, "private-id", [13]]])
    monkeypatch.setattr("scripts.probe_explore.get_client", lambda: client)
    results = probe("JAX", future_date(), extended=extended)
    assert client.post.call_count == posts
    assert client.get.call_count == gets
    assert len(results) == posts
    assert all(r["error_type"] == "provider_rejected" for r in results)
    assert all(r["provider_code"] == 13 for r in results)
    assert not any(r["transport_available"] for r in results)
    assert "private-id" not in json.dumps(results)


@pytest.mark.parametrize("body", ["<html>Consent</html>", "[]"])
def test_missing_explore_payload_is_a_parse_error(monkeypatch, body):
    client = MagicMock()
    client.post.return_value.status_code = 200
    client.post.return_value.text = body
    monkeypatch.setattr("scripts.probe_explore.get_client", lambda: client)
    result = probe("JAX", future_date())[0]
    assert result["error_type"] == "parse_error"
    assert result["transport_available"] is False


def test_parseable_chunks_only_establish_transport_availability(monkeypatch):
    client = MagicMock()
    client.post.return_value.status_code = 200
    client.post.return_value.text = json.dumps([["wrb.fr", None, "[]"]])
    monkeypatch.setattr("scripts.probe_explore.get_client", lambda: client)
    result = probe("JAX", future_date())[0]
    assert result["transport_available"] is True
    assert result["payload_chunks"] == 1
    assert "destinations" not in result
