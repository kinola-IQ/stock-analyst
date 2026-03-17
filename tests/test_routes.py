"""Tests for routes.py"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from Interface.routes import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAnalyzeStock:
    @patch('Interface.routes.runner')
    @patch('Interface.routes.ResultStorage')
    def test_analyze_stock_success(self, mock_storage, mock_runner):
        # Mock the async runner
        mock_event = Mock()
        mock_event.is_final_response.return_value = True
        mock_event.content.parts = [Mock()]
        mock_event.content.parts[0].text = "BUY recommendation"

        mock_runner.run_async = AsyncMock(return_value=[mock_event])

        client = TestClient(app)
        response = client.post("/v1/analyze-stock/", json={"ticker": "AAPL"})

        assert response.status_code == 200
        data = response.json()
        assert data['final_summary'] == "BUY recommendation"
        mock_storage.save.assert_called()

    @patch('Interface.routes.runner')
    def test_analyze_stock_no_final_response(self, mock_runner):
        mock_event = Mock()
        mock_event.is_final_response.return_value = False

        mock_runner.run_async = AsyncMock(return_value=[mock_event])

        client = TestClient(app)
        response = client.post("/v1/analyze-stock/", json={"ticker": "AAPL"})

        assert response.status_code == 200
        data = response.json()
        assert data['final_summary'] == "Agent did not produce a final response."

    @patch('Interface.routes.runner')
    def test_analyze_stock_exception(self, mock_runner):
        mock_runner.run_async.side_effect = Exception("Runner error")

        client = TestClient(app)
        response = client.post("/v1/analyze-stock/", json={"ticker": "AAPL"})

        assert response.status_code == 500
        assert "Runner error" in response.json()['detail']

    def test_analyze_stock_invalid_input(self, client):
        response = client.post("/v1/analyze-stock/", json={})

        assert response.status_code == 422  # Validation error