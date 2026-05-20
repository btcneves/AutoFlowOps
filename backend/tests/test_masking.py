"""Unit tests for the masking service."""

import json

from app.services.masking import mask_sensitive_body, mask_sensitive_headers


def test_mask_headers_sensitive_key():
    result = mask_sensitive_headers({"Authorization": "Bearer abc123"})
    assert result["Authorization"] == "***"


def test_mask_headers_case_insensitive():
    result = mask_sensitive_headers({"AUTHORIZATION": "secret", "X-Api-Key": "key123"})
    assert result["AUTHORIZATION"] == "***"
    assert result["X-Api-Key"] == "***"


def test_mask_headers_passes_non_sensitive():
    result = mask_sensitive_headers(
        {"Content-Type": "application/json", "Accept": "*/*"}
    )
    assert result["Content-Type"] == "application/json"
    assert result["Accept"] == "*/*"


def test_mask_headers_mixed():
    result = mask_sensitive_headers(
        {"Authorization": "Bearer tok", "Content-Type": "application/json"}
    )
    assert result["Authorization"] == "***"
    assert result["Content-Type"] == "application/json"


def test_mask_headers_empty():
    assert mask_sensitive_headers({}) == {}


def test_mask_body_json_sensitive_key():
    body = json.dumps({"password": "s3cr3t", "username": "alice"})
    result = json.loads(mask_sensitive_body(body))  # type: ignore[arg-type]
    assert result["password"] == "***"
    assert result["username"] == "alice"


def test_mask_body_json_nested():
    body = json.dumps({"auth": {"token": "abc", "user": "bob"}})
    result = json.loads(mask_sensitive_body(body))  # type: ignore[arg-type]
    assert result["auth"]["token"] == "***"
    assert result["auth"]["user"] == "bob"


def test_mask_body_json_list():
    body = json.dumps([{"api_key": "k1"}, {"api_key": "k2", "name": "x"}])
    result = json.loads(mask_sensitive_body(body))  # type: ignore[arg-type]
    assert result[0]["api_key"] == "***"
    assert result[1]["api_key"] == "***"
    assert result[1]["name"] == "x"


def test_mask_body_non_json_returned_as_is():
    plain = "name=alice&password=secret"
    assert mask_sensitive_body(plain) == plain


def test_mask_body_none_returns_none():
    assert mask_sensitive_body(None) is None


def test_mask_body_access_token():
    body = json.dumps({"access_token": "tok", "refresh_token": "rtok", "data": 1})
    result = json.loads(mask_sensitive_body(body))  # type: ignore[arg-type]
    assert result["access_token"] == "***"
    assert result["refresh_token"] == "***"
    assert result["data"] == 1
