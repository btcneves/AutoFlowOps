import pytest
from fastapi import HTTPException

from app.services.ssrf_guard import check_url


def test_blocks_localhost():
    with pytest.raises(HTTPException) as exc:
        check_url("http://localhost/api/internal")
    assert exc.value.status_code == 403


def test_blocks_loopback_ip():
    with pytest.raises(HTTPException) as exc:
        check_url("http://127.0.0.1/secret")
    assert exc.value.status_code == 403


def test_blocks_private_10():
    with pytest.raises(HTTPException) as exc:
        check_url("http://10.0.0.1/internal")
    assert exc.value.status_code == 403


def test_blocks_private_172():
    with pytest.raises(HTTPException) as exc:
        check_url("http://172.16.0.1/internal")
    assert exc.value.status_code == 403


def test_blocks_private_192():
    with pytest.raises(HTTPException) as exc:
        check_url("http://192.168.1.1/")
    assert exc.value.status_code == 403


def test_blocks_link_local():
    with pytest.raises(HTTPException) as exc:
        check_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.status_code == 403


def test_blocks_ipv6_loopback():
    with pytest.raises(HTTPException) as exc:
        check_url("http://[::1]/")
    assert exc.value.status_code == 403


def test_blocks_zero_host():
    with pytest.raises(HTTPException) as exc:
        check_url("http://0.0.0.0/")
    assert exc.value.status_code == 403


def test_allows_public_url():
    # Should not raise — example.com is a public address
    check_url("https://example.com/api/data")


def test_rejects_url_with_no_host():
    with pytest.raises(HTTPException) as exc:
        check_url("not-a-url")
    assert exc.value.status_code in (403, 422)
