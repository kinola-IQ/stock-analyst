"""Tests for tools.py"""
import pytest
from unittest.mock import Mock, patch
from system.agents.finance_agent.tools import research_agent, analyse_ticker


class TestResearchAgent:
    @patch('system.agents.finance_agent.tools.Ollama')
    @patch('system.agents.finance_agent.tools.Agent')
    @patch('system.agents.finance_agent.tools.google_search')
    def test_research_agent_creation(self, mock_google_search, mock_agent, mock_ollama):
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance

        result = research_agent()

        assert result == mock_agent_instance
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        assert call_args[1]['name'] == 'ResearchAgent'
        assert 'qwen3:4b' in str(call_args[1]['model'])
        assert mock_google_search in call_args[1]['tools']


class TestAnalyseTicker:
    @patch('system.agents.finance_agent.tools.fetch_company_data')
    @patch('system.agents.finance_agent.tools.extract_financial_metrics')
    @patch('system.agents.finance_agent.tools.score_news_sentiment')
    @patch('system.agents.finance_agent.tools.generate_analysis_script')
    @patch('system.agents.finance_agent.tools.decide_action')
    def test_analyse_ticker_success(self, mock_decide, mock_generate, mock_score, mock_extract, mock_fetch):
        mock_fetch.return_value = {'symbol': 'AAPL', 'news': ['news1']}
        mock_extract.return_value = {'current_price': 150.0}
        mock_score.return_value = 0.5
        mock_generate.return_value = 'script'
        mock_decide.return_value = {'verdict': 'BUY', 'score': 3}

        result = analyse_ticker('AAPL')

        assert result['verdict'] == 'BUY'
        assert result['metrics'] == {'current_price': 150.0}
        assert result['sentiment_score'] == 0.5
        mock_fetch.assert_called_with('AAPL')
        mock_extract.assert_called_once()
        mock_score.assert_called_once()
        mock_generate.assert_called_once()
        mock_decide.assert_called_once()

    @patch('system.agents.finance_agent.tools.fetch_company_data')
    def test_analyse_ticker_fetch_failure(self, mock_fetch):
        mock_fetch.side_effect = Exception("Fetch failed")

        result = analyse_ticker('INVALID')

        assert 'error' in result
        assert 'Fetch failed' in result['error']