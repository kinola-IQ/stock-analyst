"""Tests for tools.py"""
import pytest
from unittest.mock import Mock, patch
from system.agents.finance_agent.agent import root_agent
from system.agents.finance_agent import tools as finance_tools
from system.agents.finance_agent.tools import analyse_ticker
from system.agents.finance_agent.tools_config import ticker_tools


class TestResearchAgent:
    @patch('system.agents.finance_agent.tools.model.get_model')
    @patch('system.agents.finance_agent.tools.Agent')
    @patch('system.agents.finance_agent.tools.google_search')
    def test_research_agent_creation(self, mock_google_search, mock_agent, mock_get_model):
        mock_agent_instance = Mock()
        mock_agent.return_value = mock_agent_instance
        mock_get_model.return_value = 'fake-model'

        result = finance_tools.research_agent()

        assert result == mock_agent_instance
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args
        assert call_args[1]['name'] == 'ResearchAgent'
        assert call_args[1]['model'] == 'fake-model'
        assert mock_google_search in call_args[1]['tools']


class TestRootAgent:
    @patch('system.agents.finance_agent.agent.research_agent')
    @patch('system.agents.finance_agent.agent.FunctionTool')
    @patch('system.agents.finance_agent.agent.LlmAgent')
    @patch('system.agents.finance_agent.agent.model.get_model')
    def test_root_agent_does_not_register_log_tool(self, mock_get_model, mock_llm_agent, mock_function_tool, mock_research_agent):
        mock_get_model.return_value = 'fake-model'
        mock_llm_agent.return_value = Mock()
        mock_function_tool.side_effect = lambda func: func
        mock_research_agent.return_value = Mock()

        root_agent()

        tool_names = [call.args[0].__name__ for call in mock_function_tool.call_args_list]
        assert 'log_tool' not in tool_names
        assert 'analyse_ticker' in tool_names
        assert 'save_findings' in tool_names


class TestResearchResultStorage:
    def test_save_findings_and_plot_store_values(self):
        finance_tools.clear_research_results()

        assert finance_tools.save_findings('findings') == 'saved'
        assert finance_tools.save_plot('plot') == 'saved'
        assert finance_tools.research_result['findings'] == 'findings'
        assert finance_tools.research_result['plot'] == 'plot'


class TestSkillLoading:
    def test_read_skills_loads_existing_skill_file(self):
        skill_text = finance_tools.read_skills('standard guide')

        assert isinstance(skill_text, str)
        assert skill_text.strip()


class TestNewsAndResearchPersistence:
    def test_parse_news_extracts_titles_from_nested_content_payload(self):
        class FakeTicker:
            news = [
                {
                    "content": {
                        "title": "Apple launches new product",
                        "summary": "A launch summary",
                    }
                }
            ]

        news = ticker_tools._parse_news(FakeTicker(), top_n=5)

        assert len(news) == 1
        assert news[0]["title"] == "Apple launches new product"
        assert news[0]["publisher"] == ""

    def test_save_findings_persists_research_text(self):
        finance_tools.clear_research_results()

        status = finance_tools.save_findings("research summary")

        assert status == "saved"
        assert finance_tools.research_result["findings"] == "research summary"


class TestAnalyseTicker:
    def test_extract_financial_metrics_uses_info_fallback_when_financials_missing(self):
        data = {
            "info": {
                "currentPrice": 100.0,
                "trailingPE": 20.0,
                "forwardPE": 18.0,
                "marketCap": 1000000000,
                "totalRevenue": 500000000,
                "revenueGrowth": 12.5,
                "netIncomeToCommon": 80000000,
                "debtToEquity": 0.75,
            },
            "financials": None,
            "balance_sheet": None,
        }

        metrics = finance_tools.extract_financial_metrics(data)

        assert metrics['current_price'] == 100.0
        assert metrics['revenue'] == 500000000.0
        assert metrics['revenue_growth_pct'] == 12.5
        assert metrics['net_income'] == 80000000.0
        assert metrics['debt_to_equity'] == 0.75

    @patch('system.agents.finance_agent.tools.fetch_company_data')
    @patch('system.agents.finance_agent.tools.extract_financial_metrics')
    @patch('system.agents.finance_agent.tools.score_news_sentiment')
    @patch('system.agents.finance_agent.tools.generate_analysis_script')
    @patch('system.agents.finance_agent.tools.decide_action')
    def test_analyse_ticker_success(self, mock_decide, mock_generate, mock_score, mock_extract, mock_fetch):
        mock_fetch.return_value = {'symbol': 'AAPL', 'news': [{'title': 'news1'}]}
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