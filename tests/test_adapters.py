import pickle
from unittest.mock import MagicMock, patch

import pytest

import requests
import requests.adapters


def test_request_url_trims_leading_path_separators():
    """See also https://github.com/psf/requests/issues/6643."""
    a = requests.adapters.HTTPAdapter()
    p = requests.Request(method="GET", url="http://127.0.0.1:10000//v:h").prepare()
    assert "/v:h" == a.request_url(p, {})


class TestBuildUrlopenKwargs:
    """Tests for _build_urlopen_kwargs method and subclassing pattern."""

    def test_build_urlopen_kwargs_returns_expected_defaults(self) -> None:
        """Test that _build_urlopen_kwargs returns correct default values."""
        adapter = requests.adapters.HTTPAdapter()

        # Mock necessary objects
        from urllib3.util import Timeout as TimeoutSauce

        request = requests.Request("GET", "http://example.com/path").prepare()
        timeout = TimeoutSauce(connect=10, read=20)
        url = "/path"
        chunked = False

        kwargs = adapter._build_urlopen_kwargs(request, timeout, chunked, url)

        # Verify all expected keys are present
        assert kwargs["method"] == "GET"
        assert kwargs["url"] == "/path"
        assert kwargs["body"] == request.body
        assert kwargs["headers"] == request.headers
        assert kwargs["redirect"] is False
        assert kwargs["assert_same_host"] is False
        assert kwargs["preload_content"] is False
        assert kwargs["decode_content"] is False
        assert kwargs["retries"] == adapter.max_retries
        assert kwargs["timeout"] == timeout
        assert kwargs["chunked"] is False

    def test_subclass_can_override_build_urlopen_kwargs(self) -> None:
        """Test that subclasses can override _build_urlopen_kwargs to customize behavior."""

        class CustomAdapter(requests.adapters.HTTPAdapter):
            def _build_urlopen_kwargs(self, request, timeout, chunked, url):
                kwargs = super()._build_urlopen_kwargs(request, timeout, chunked, url)
                kwargs["enforce_content_length"] = False
                return kwargs

        adapter = CustomAdapter()

        # Mock the connection's urlopen method
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.reason = "OK"

        with patch.object(
            adapter, "get_connection_with_tls_context"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.urlopen.return_value = mock_response
            mock_get_conn.return_value = mock_conn

            # Prepare and send a request
            request = requests.Request("GET", "http://example.com").prepare()
            adapter.send(request)

            # Verify urlopen was called with the custom kwarg
            call_kwargs = mock_conn.urlopen.call_args[1]
            assert "enforce_content_length" in call_kwargs
            assert call_kwargs["enforce_content_length"] is False

    def test_subclass_can_override_default_kwargs(self) -> None:
        """Test that subclasses can override default urlopen arguments."""

        class CustomAdapter(requests.adapters.HTTPAdapter):
            def _build_urlopen_kwargs(self, request, timeout, chunked, url):
                kwargs = super()._build_urlopen_kwargs(request, timeout, chunked, url)
                kwargs["preload_content"] = True
                kwargs["decode_content"] = True
                return kwargs

        adapter = CustomAdapter()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.reason = "OK"

        with patch.object(
            adapter, "get_connection_with_tls_context"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.urlopen.return_value = mock_response
            mock_get_conn.return_value = mock_conn

            request = requests.Request("GET", "http://example.com").prepare()
            adapter.send(request)

            # Verify the overrides were applied
            call_kwargs = mock_conn.urlopen.call_args[1]
            assert call_kwargs["preload_content"] is True
            assert call_kwargs["decode_content"] is True

    def test_subclass_adapter_works_with_session(self) -> None:
        """Test that custom adapter works with Session."""

        class CustomAdapter(requests.adapters.HTTPAdapter):
            def _build_urlopen_kwargs(self, request, timeout, chunked, url):
                kwargs = super()._build_urlopen_kwargs(request, timeout, chunked, url)
                kwargs["enforce_content_length"] = False
                return kwargs

        session = requests.Session()
        adapter = CustomAdapter()

        # Mount for both http and https
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Verify the adapter is installed
        assert isinstance(session.get_adapter("http://example.com"), CustomAdapter)
        assert isinstance(session.get_adapter("https://example.com"), CustomAdapter)

    def test_subclass_can_add_multiple_custom_kwargs(self) -> None:
        """Test that subclasses can add multiple custom kwargs."""

        class CustomAdapter(requests.adapters.HTTPAdapter):
            def _build_urlopen_kwargs(self, request, timeout, chunked, url):
                kwargs = super()._build_urlopen_kwargs(request, timeout, chunked, url)
                kwargs.update(
                    {
                        "enforce_content_length": False,
                        "custom_arg1": "value1",
                        "custom_arg2": 42,
                        "custom_arg3": True,
                    }
                )
                return kwargs

        adapter = CustomAdapter()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.reason = "OK"

        with patch.object(
            adapter, "get_connection_with_tls_context"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.urlopen.return_value = mock_response
            mock_get_conn.return_value = mock_conn

            request = requests.Request("GET", "http://example.com").prepare()
            adapter.send(request)

            # Verify all custom kwargs were passed
            call_kwargs = mock_conn.urlopen.call_args[1]
            assert call_kwargs["enforce_content_length"] is False
            assert call_kwargs["custom_arg1"] == "value1"
            assert call_kwargs["custom_arg2"] == 42
            assert call_kwargs["custom_arg3"] is True

    def test_default_kwargs_still_present_in_subclass(self) -> None:
        """Test that default kwargs are still present when adding custom ones via subclass."""

        class CustomAdapter(requests.adapters.HTTPAdapter):
            def _build_urlopen_kwargs(self, request, timeout, chunked, url):
                kwargs = super()._build_urlopen_kwargs(request, timeout, chunked, url)
                kwargs["enforce_content_length"] = False
                return kwargs

        adapter = CustomAdapter()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {}
        mock_response.reason = "OK"

        with patch.object(
            adapter, "get_connection_with_tls_context"
        ) as mock_get_conn:
            mock_conn = MagicMock()
            mock_conn.urlopen.return_value = mock_response
            mock_get_conn.return_value = mock_conn

            request = requests.Request("GET", "http://example.com").prepare()
            adapter.send(request)

            # Verify default kwargs are still present
            call_kwargs = mock_conn.urlopen.call_args[1]
            assert "method" in call_kwargs
            assert "url" in call_kwargs
            assert "headers" in call_kwargs
            assert "redirect" in call_kwargs
            assert call_kwargs["redirect"] is False
            assert "assert_same_host" in call_kwargs
            assert call_kwargs["assert_same_host"] is False
            assert "retries" in call_kwargs
            assert "timeout" in call_kwargs
