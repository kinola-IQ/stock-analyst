"""Tests for ticker_tools.py"""
import pandas as pd
import pytest
from unittest.mock import Mock, patch, MagicMock
from system.agents.finance_agent.tools_config.ticker_tools import (
    fetch_company_data,
    extract_financial_metrics,
    score_news_sentiment,
    generate_analysis_script,
    decide_action
)


class TestFetchCompanyData:
    @patch('system.agents.finance_agent.tools_config.ticker_tools.yf')
    def test_fetch_company_data_success(self, mock_yf):
        # Mock ticker
        mock_ticker = Mock()
        mock_ticker.info = {
            'longName': 'Apple Inc.',
            'currentPrice': 150.0
        }
        mock_ticker.financials = Mock()
        mock_ticker.balance_sheet = Mock()
        mock_ticker.cashflow = Mock()
        mock_ticker.news = [
            {'title': 'Apple news', 'link': 'http://example.com', 'publisher': 'Publisher', 'providerPublishTime': 1234567890}
        ]
        mock_ticker.history.return_value = Mock()  # Mock DataFrame

        mock_yf.Ticker.return_value = mock_ticker

        result = fetch_company_data('AAPL')

        assert result['symbol'] == 'AAPL'
        assert result['company'] == 'Apple Inc.'
        assert result['info']['currentPrice'] == 150.0
        assert len(result['news']) == 1
        mock_yf.Ticker.assert_called_with('AAPL')

    @patch('system.agents.finance_agent.tools_config.ticker_tools.yf')
    def test_fetch_company_data_exception(self, mock_yf):
        mock_yf.Ticker.side_effect = Exception("API error")

        result = fetch_company_data('INVALID')

        assert result['symbol'] == 'INVALID'
        assert result['error'] == 'API error'

    @patch('system.agents.finance_agent.tools_config.ticker_tools.yf')
    def test_fetch_company_data_keeps_financial_dataframes(self, mock_yf):
        mock_ticker = Mock()
        mock_ticker.info = {}
        mock_ticker.financials = pd.DataFrame({'2023': [1]}, index=['Revenue'])
        mock_ticker.balance_sheet = pd.DataFrame({'2023': [1]}, index=['Total Debt'])
        mock_ticker.news = []
        mock_ticker.history.return_value = pd.DataFrame({'Close': [100.0]})
        mock_yf.Ticker.return_value = mock_ticker

        result = fetch_company_data('AAPL')

        assert result['financials'] is mock_ticker.financials
        assert result['balance_sheet'] is mock_ticker.balance_sheet


class TestExtractFinancialMetrics:
    def test_extract_financial_metrics(self):
        data = {
            'info': {
                'currentPrice': 150.0,
                'trailingPE': 20.0,
                'forwardPE': 18.0,
                'debtToEquity': 1.5
            },
            'financials': Mock(),  # Mock DataFrame
            'balance_sheet': Mock(),
            'cashflow': Mock()
        }

        # Mock the DataFrame operations
        data['financials'].iloc = Mock()
        data['financials'].iloc.__getitem__ = Mock(return_value=Mock())
        data['financials'].iloc.__getitem__().get = Mock(return_value=1000000)  # netIncome

        result = extract_financial_metrics(data)

        assert 'current_price' in result
        assert 'trailing_pe' in result
        assert result['current_price'] == 150.0

    def test_extract_financial_metrics_missing_data(self):
        data = {'info': {}}

        result = extract_financial_metrics(data)

        assert result['current_price'] is None


class TestScoreNewsSentiment:
    @patch('system.agents.finance_agent.tools_config.ticker_tools.SentimentIntensityAnalyzer')
    def test_score_news_sentiment(self, mock_analyzer):
        mock_instance = Mock()
        mock_instance.polarity_scores.return_value = {'compound': 0.5}
        mock_analyzer.return_value = mock_instance

        headlines = ['Good news', 'Bad news']

        result = score_news_sentiment(headlines)

        assert result == 0.5
        mock_instance.polarity_scores.assert_called()

    @patch('system.agents.finance_agent.tools_config.ticker_tools.SentimentIntensityAnalyzer')
    def test_score_news_sentiment_fallback(self, mock_analyzer):
        mock_analyzer.side_effect = ImportError

        headlines = ['Good news']

        result = score_news_sentiment(headlines)

        # Should return fallback score
        assert isinstance(result, float)


class TestGenerateAnalysisScript:
    def test_generate_analysis_script(self):
        metrics = {'current_price': 150.0}
        headlines = ['News 1']
        sentiment_score = 0.5
        symbol = 'AAPL'

        result = generate_analysis_script(metrics, headlines, sentiment_score, symbol)

        assert 'symbol = \'AAPL\'' in result
        assert 'print(\'Generated metrics snapshot:\')' in result
        assert isinstance(result, str)


class TestDecideAction:
    def test_decide_action_buy(self):
        metrics = {
            'net_income': 1000000,
            'revenue_growth_pct': 10.0,
            'debt_to_equity': 0.5,
            'trailing_pe': 10.0
        }
        sentiment_score = 0.5

        result = decide_action(metrics, sentiment_score, "script")

        assert result['verdict'] == 'BUY'
        assert result['score'] >= 2
        assert 'reasons' in result

    def test_decide_action_sell(self):
        metrics = {
            'net_income': -1000000,
            'revenue_growth_pct': -10.0,
            'debt_to_equity': 3.0,
            'trailing_pe': 50.0
        }
        sentiment_score = -0.5

        result = decide_action(metrics, sentiment_score, "script")

        assert result['verdict'] == 'SELL'
        assert result['score'] <= -2

    def test_decide_action_hold(self):
        metrics = {
            'net_income': 100000,
            'revenue_growth_pct': 2.0,
            'debt_to_equity': 1.0,
            'trailing_pe': 20.0
        }
        sentiment_score = 0.0

        result = decide_action(metrics, sentiment_score, "script")

        assert result['verdict'] == 'HOLD'
        assert -2 < result['score'] < 2