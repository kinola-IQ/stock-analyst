import requests
import re
import json
from datetime import date, timedelta
from typing import Optional, Any, Sequence

from .tools_config.ticker_tools import (
    fetch_company_data,
    extract_financial_metrics,
    score_news_sentiment,
    decide_action)

from .tools_config.local_ticker_tools import (
    _validate_symbol,
    _validate_date,
    _request_json,
    _build_tool_result,
    _error,
    DEFAULT_HISTORY_DAYS,
    FinancialDataset,
    _validate_country_code,
    _validate_year,
)

from ...utility.utils import get_env

# foreign ticker tool
def analyse_ticker(symbol: str) -> str:
    """Execute a comprehensive financial analysis pipeline for a given stock ticker.
    
    This is a high-level wrapper function that orchestrates a complete research and
    analysis workflow for a stock. It fetches current company data, extracts financial
    metrics, analyzes news sentiment, and produces a
    buy/sell/hold verdict.
    
    The analysis steps are executed in sequence:
    1. Fetch company data and financials from yfinance
    2. Extract key financial metrics (P/E ratios, revenue, debt, etc.)
    3. Retrieve and analyze recent news headlines for sentiment
    4. Apply decision rules to produce a buy/sell/hold recommendation
    
    Args:
        symbol (str): The stock ticker symbol to analyze (e.g., "AAPL", "MSFT", "GOOGL").
                     Will be converted to uppercase. Must be a valid ticker symbol
                     recognized by yfinance.
    
    Returns:
        Dict[str, Any]: A comprehensive analysis result containing:
            - symbol (str): The stock ticker symbol in uppercase
            - company (str): The company name or long name
            - metrics (Dict): Financial metrics including:
                * current_price (float): Current stock price
                * trailing_pe (float): Trailing price-to-earnings ratio
                * forward_pe (float): Forward P/E ratio
                * market_cap (float): Market capitalization
                * revenue (float): Annual revenue
                * net_income (float): Annual net income
                * revenue_growth_pct (float): Year-over-year revenue growth percentage
                * total_debt (float): Total company debt
                * total_equity (float): Total stockholder equity
                * debt_to_equity (float): Debt-to-equity ratio
            - headlines (List[str]): Recent news headlines for the company
            - sentiment_score (float): Aggregate sentiment score (-1.0 to 1.0)
                                      where positive indicates bullish sentiment
            - verdict (str): Investment decision: "BUY", "SELL", or "HOLD"
            - verdict_details (Dict): Detailed reasoning for the decision including:
                * score (int): Net score from decision rules
                * reasons (List[str]): List of factors that influenced the decision
                * recommendation (str): Full recommendation text
    
    Raises:
        Exception: May raise various exceptions if yfinance fails to fetch data,
                  if the ticker symbol is invalid, or if network issues occur.
                  These are logged but may propagate up.
    
    Example:
        result = analyse_ticker("AAPL")
        print(f"Verdict for {result['symbol']}: {result['verdict']}")
        print(f"Current Price: ${result['metrics']['current_price']}")
        print(f"Sentiment: {result['sentiment_score']}")
    """
    try:
        data = fetch_company_data(symbol)
    except Exception as exc:
        return json.dumps({
            "symbol": symbol.upper(),
            "error": f"Fetch failed: {exc}"
        })

    metrics = extract_financial_metrics(data)
    headlines = []
    for item in data.get("news", []):
        if isinstance(item, dict):
            headlines.append(item.get("title", ""))
        elif isinstance(item, str):
            headlines.append(item)
        else:
            headlines.append(str(item))

    sentiment = score_news_sentiment(headlines)
    decision = decide_action(metrics, sentiment)
    result = json.dumps({
        "symbol": symbol.upper(),
        "company": data.get("company"),
        "metrics": metrics,
        "headlines": headlines,
        "sentiment_score": sentiment,
        "verdict": decision["verdict"],
        "verdict_details": decision,
    })
    return result

# local ticker tools

# Financial data tool

def financial_data_tool(
    symbol: str,
    include: Sequence[FinancialDataset] = (
        "historical",
        "fundamentals",
    ),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    fundamentals_filter: Optional[str] = None,
    news_limit: int = 5,
) -> dict[str, Any]:
    """
    Retrieve issuer-specific financial data for a market instrument from
    EOD Historical Data (EODHD).

    PURPOSE
        Use this tool when the agent needs information directly related to
        a company/security rather than country-level macroeconomic context.

    SUPPORTED DATASETS
        historical:
            Daily end-of-day OHLCV observations. When dates are omitted, the
            tool intentionally limits the request to approximately the most
            recent 365 calendar days to avoid returning an unnecessarily large
            dataset.

        fundamentals:
            Company profile, valuation, technical metrics, earnings,
            dividends/splits, ownership, and/or financial statements,
            depending on EODHD coverage and the `fundamentals_filter`.
            EODHD may return missing fields for securities whose underlying
            issuer does not report them.

        news:
            Recent financial-news articles associated with the requested
            ticker. Each article may contain title, publication date, link,
            mentioned symbols, tags, and sentiment fields.

        sentiment:
            EODHD daily aggregated sentiment observations for the requested
            ticker over the requested date range.

    SYMBOL FORMAT
        Pass EODHD's exchange-qualified symbol, not merely the local ticker.
        Example for AIICO on the Nigerian Exchange:
            "AIICO.XNSA"

    DATE SEMANTICS
        Dates must use YYYY-MM-DD.
        `start_date` and `end_date` apply to historical, news, and sentiment
        requests.
        If historical data is requested and no dates are supplied, the tool
        uses the previous 365 calendar days.
        If only `start_date` is supplied, `end_date` defaults to today.
        If only `end_date` is supplied, `start_date` is one year before it.

    FUNDAMENTALS FILTER
        `fundamentals_filter` is passed directly to EODHD's `filter`
        parameter. Omit it to request EODHD's complete fundamentals object.
        Use filters to reduce response size, for example:
            "General"
            "Highlights,Valuation,Technicals"
            "Financials::Income_Statement::yearly"
            "Financials::Balance_Sheet::yearly"
            "General,Highlights,Valuation,Earnings"

    ERROR SEMANTICS
        This function NEVER raises an HTTP/API error to the agent.
        Instead, it returns an `errors` array containing:
            code
            message
            source
            endpoint
            retryable
            http_status (when available)
            details (when available)

        `status` is:
            "success"  -> every requested dataset succeeded.
            "partial"  -> at least one dataset succeeded and at least one
                          dataset failed.
            "error"    -> all requested datasets failed.

        When `status` is "partial", the agent must use only the successfully
        returned datasets and must not infer missing information.

    RETURNS
        A JSON-serializable dictionary with:
            tool
            status
            ok
            request
            data
            errors
    """
    try:
        normalized_symbol = _validate_symbol(symbol)

        allowed_datasets = {
            "historical",
            "fundamentals",
            "news",
            "sentiment",
        }

        requested_datasets = list(dict.fromkeys(include))

        invalid = set(requested_datasets) - allowed_datasets

        if invalid:
            raise ValueError(
                f"Unsupported financial dataset(s): "
                f"{sorted(invalid)}. "
                f"Allowed values: {sorted(allowed_datasets)}."
            )

        if not requested_datasets:
            raise ValueError(
                "`include` must contain at least one dataset."
            )

        if not 1 <= news_limit <= 100:
            raise ValueError("news_limit must be between 1 and 100.")

        normalized_start = _validate_date(start_date, "start_date")
        normalized_end = _validate_date(end_date, "end_date")

        # Determine the bounded historical/news/sentiment window.
        today = date.today()

        if "historical" in requested_datasets:
            if normalized_start is None and normalized_end is None:
                historical_start = (
                    today - timedelta(days=DEFAULT_HISTORY_DAYS)
                ).isoformat()
                historical_end = today.isoformat()

            elif normalized_start is None:
                historical_end_date = date.fromisoformat(normalized_end)  # type: ignore[arg-type]
                historical_start = (
                    historical_end_date - timedelta(days=DEFAULT_HISTORY_DAYS)
                ).isoformat()
                historical_end = normalized_end

            elif normalized_end is None:
                historical_start = normalized_start
                historical_end = today.isoformat()

            else:
                historical_start = normalized_start
                historical_end = normalized_end

            if historical_start > historical_end:  # type: ignore[operator]
                raise ValueError(
                    "start_date cannot be later than end_date."
                )
        else:
            historical_start = normalized_start
            historical_end = normalized_end

        api_key = get_env("EODHD_API_KEY")

        if not api_key:
            return _build_tool_result(
                tool_name="financial_data_tool",
                request={
                    "symbol": normalized_symbol,
                    "include": requested_datasets,
                },
                data={},
                errors=[
                    _error(
                        code="CONFIGURATION_ERROR",
                        message=(
                            "EODHD_API_KEY is not configured. "
                            "Set it as an environment variable before "
                            "calling financial_data_tool."
                        ),
                        source="EODHD",
                        endpoint=get_env('EODHD_BASE_URL'),
                        retryable=False,
                    )
                ],
            )

        session = requests.Session()

        data: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []

        # Historical prices

        if "historical" in requested_datasets:
            endpoint = f"/eod/{normalized_symbol}"

            payload, error = _request_json(
                session=session,
                source="EODHD",
                endpoint=endpoint,
                url=f"{get_env('EODHD_BASE_URL')}{endpoint}",
                params={
                    "api_token": api_key,
                    "fmt": "json",
                    "from": historical_start,
                    "to": historical_end,
                },
            )

            if error:
                errors.append(error)
            else:
                data["historical"] = {
                    "symbol": normalized_symbol,
                    "from": historical_start,
                    "to": historical_end,
                    "records": payload,
                    "record_count": (
                        len(payload)
                        if isinstance(payload, list)
                        else None
                    ),
                }

        # Fundamentals

        if "fundamentals" in requested_datasets:
            endpoint = f"/v1.1/fundamentals/{normalized_symbol}"

            params: dict[str, Any] = {
                "api_token": api_key,
                "fmt": "json",
            }

            if fundamentals_filter:
                params["filter"] = fundamentals_filter

            payload, error = _request_json(
                session=session,
                source="EODHD",
                endpoint=endpoint,
                url=f"{get_env('EODHD_BASE_URL')}{endpoint}",
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["fundamentals"] = {
                    "symbol": normalized_symbol,
                    "filter": fundamentals_filter,
                    "records": payload,
                }

        # News

        if "news" in requested_datasets:
            endpoint = "/news"

            params = {
                "api_token": api_key,
                "fmt": "json",
                "s": normalized_symbol,
                "limit": news_limit,
                "offset": 0,
            }

            if normalized_start:
                params["from"] = normalized_start

            if normalized_end:
                params["to"] = normalized_end

            payload, error = _request_json(
                session=session,
                source="EODHD",
                endpoint=endpoint,
                url=f"{get_env('EODHD_BASE_URL')}{endpoint}",
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["news"] = {
                    "symbol": normalized_symbol,
                    "records": payload,
                    "record_count": (
                        len(payload)
                        if isinstance(payload, list)
                        else None
                    ),
                }

        # Sentiment

        if "sentiment" in requested_datasets:
            endpoint = "/sentiments"

            params = {
                "api_token": api_key,
                "fmt": "json",
                "s": normalized_symbol,
            }

            if normalized_start:
                params["from"] = normalized_start

            if normalized_end:
                params["to"] = normalized_end

            payload, error = _request_json(
                session=session,
                source="EODHD",
                endpoint=endpoint,
                url=f"{get_env('EODHD_BASE_URL')}{endpoint}",
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["sentiment"] = {
                    "symbol": normalized_symbol,
                    "from": normalized_start,
                    "to": normalized_end,
                    "records": payload,
                }

        return _build_tool_result(
            tool_name="financial_data_tool",
            request={
                "symbol": normalized_symbol,
                "include": requested_datasets,
                "start_date": normalized_start,
                "end_date": normalized_end,
                "historical_effective_start": historical_start,
                "historical_effective_end": historical_end,
                "fundamentals_filter": fundamentals_filter,
                "news_limit": news_limit,
            },
            data=data,
            errors=errors,
        )

    except ValueError as exc:
        return _build_tool_result(
            tool_name="financial_data_tool",
            request={
                "symbol": symbol,
                "include": list(include),
            },
            data={},
            errors=[
                _error(
                    code="INVALID_ARGUMENT",
                    message=str(exc),
                    source="financial_data_tool",
                    endpoint="local_validation",
                    retryable=False,
                )
            ],
        )


# Macro context tool

def macro_context_tool(
    country_code: str = "ng",
    *,
    include_signals: bool = True,
    include_fx: bool = True,
    include_indicators: bool = False,
    include_trade: bool = False,
    base_currency: str = "USD",
    quote_currencies: Sequence[str] = ("NGN",),
    metric_keys: Optional[Sequence[str]] = None,
    indicator_category: Optional[str] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
    latest: bool = True,
    trade_top_limit: int = 5,
) -> dict[str, Any]:
    """
    Retrieve country-level macroeconomic and market-context data from
    Africa API.

    PURPOSE
        Use this tool when the agent needs contextual information about the
        economic environment surrounding a company or market. This tool does
        not provide issuer-specific financial statements; those belong in
        `financial_data_tool`.

    COUNTRY
        `country_code` is a two-letter country code.
        The default "ng" means Nigeria.

    SIGNALS
        `include_signals=True` requests:
            GET /v1/countries/{country_code}/signals

        Country signals can contain current/selected observations such as
        policy rates, inflation, official exchange rates, FX observations,
        market snapshots, commodity benchmarks, trade summaries, and other
        country-linked records depending on the country's available coverage.

        The returned records can have different frequencies and reporting
        periods. The agent must inspect their dates/freshness rather than
        assuming every value represents today's condition.

    FX
        `include_fx=True` requests the latest FX rates through:
            GET /v1/markets/fx-rates

        `base_currency` defaults to USD.
        `quote_currencies` defaults to ("NGN",).

    INDICATORS
        `include_indicators=True` queries:
            GET /v1/data

        Use `metric_keys` when the agent needs specific metrics, for example:
            "gdp_current_usd"
            "trade_balance_usd"
            "exports_goods_services_usd"
            "imports_goods_services_usd"
            "policy_rate_pct"

        `indicator_category` may be used to request a category such as
        "economy" when specific metric keys are not supplied.

        `latest=True` means "latest stored observation available from the
        provider"; it does NOT mean "measured today."

    TRADE
        `include_trade=True` requests:
            GET /v1/trade/overview/{country_code}

        This can return aggregate trade series, latest snapshots, leading
        export/import partners, and leading product categories where coverage
        exists.

    ERROR SEMANTICS
        This function NEVER raises an API/HTTP error to the agent.
        It returns structured errors with:
            code
            message
            source
            endpoint
            retryable
            http_status (when available)
            details (when available)

        `status` is:
            "success"  -> all requested datasets succeeded.
            "partial"  -> some datasets succeeded and some failed.
            "error"    -> all requested datasets failed.

        If an optional dataset fails, the agent must not fabricate or infer
        its missing values from another dataset.

    IMPORTANT DATA-PROVENANCE RULE
        Africa API aggregates observations from external sources. Every
        returned indicator should be interpreted using its source, reporting
        year/period, frequency, and freshness when those fields are present.

    RETURNS
        A JSON-serializable dictionary with:
            tool
            status
            ok
            request
            data
            errors
    """
    try:
        normalized_country = _validate_country_code(country_code)

        normalized_base_currency = base_currency.strip().upper()

        if not re.fullmatch(r"[A-Z]{3}", normalized_base_currency):
            raise ValueError(
                "base_currency must be a three-letter currency code, "
                f"received {base_currency!r}."
            )

        normalized_quotes = tuple(
            currency.strip().upper()
            for currency in quote_currencies
        )

        if not normalized_quotes:
            raise ValueError(
                "quote_currencies must contain at least one currency."
            )

        for currency in normalized_quotes:
            if not re.fullmatch(r"[A-Z]{3}", currency):
                raise ValueError(
                    f"Invalid quote currency {currency!r}. "
                    "Expected a three-letter currency code."
                )

        if not (
            include_signals
            or include_fx
            or include_indicators
            or include_trade
        ):
            raise ValueError(
                "At least one macro dataset must be enabled."
            )

        normalized_start_year = _validate_year(
            start_year,
            "start_year",
        )

        normalized_end_year = _validate_year(
            end_year,
            "end_year",
        )

        if (
            normalized_start_year is not None
            and normalized_end_year is not None
            and normalized_start_year > normalized_end_year
        ):
            raise ValueError(
                "start_year cannot be later than end_year."
            )

        if include_indicators and not metric_keys and not indicator_category:
            raise ValueError(
                "When include_indicators=True, provide either "
                "metric_keys or indicator_category. "
                "This prevents an accidental broad indicator download."
            )

        if not 1 <= trade_top_limit <= 50:
            raise ValueError(
                "trade_top_limit must be between 1 and 50."
            )

        api_key = get_env("AFRICA_API_KEY")

        if not api_key:
            return _build_tool_result(
                tool_name="macro_context_tool",
                request={
                    "country_code": normalized_country,
                },
                data={},
                errors=[
                    _error(
                        code="CONFIGURATION_ERROR",
                        message=(
                            "AFRICA_API_KEY is not configured. "
                            "Set it as an environment variable before "
                            "calling macro_context_tool."
                        ),
                        source="Africa API",
                        endpoint=get_env('AFRICA_API_BASE_URL'),
                        retryable=False,
                    )
                ],
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }

        session = requests.Session()

        data: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []

        # Country signals

        if include_signals:
            endpoint = (
                f"/countries/{normalized_country}/signals"
            )

            payload, error = _request_json(
                session=session,
                source="Africa API",
                endpoint=endpoint,
                url=f"{get_env('AFRICA_API_BASE_URL')}{endpoint}",
                headers=headers,
            )

            if error:
                errors.append(error)
            else:
                data["signals"] = {
                    "country_code": normalized_country,
                    "records": payload,
                }

        # FX


        if include_fx:
            endpoint = "/markets/fx-rates"

            params = {
                "base_currency": normalized_base_currency,
                "quote_currencies": ",".join(normalized_quotes),
                "country_code": normalized_country,
                "limit": min(len(normalized_quotes) * 5, 500),
            }

            payload, error = _request_json(
                session=session,
                source="Africa API",
                endpoint=endpoint,
                url=f"{get_env('AFRICA_API_BASE_URL')}{endpoint}",
                headers=headers,
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["fx"] = {
                    "base_currency": normalized_base_currency,
                    "quote_currencies": normalized_quotes,
                    "records": payload,
                }

        # Indicators

        if include_indicators:
            endpoint = "/data"

            params: dict[str, Any] = {
                "country_code": normalized_country,
                "limit": 1000,
            }

            if metric_keys:
                params["metric_keys"] = ",".join(
                    key.strip()
                    for key in metric_keys
                    if key.strip()
                )

            if indicator_category:
                params["category"] = indicator_category.strip()

            if normalized_start_year is not None:
                params["start_year"] = normalized_start_year

            if normalized_end_year is not None:
                params["end_year"] = normalized_end_year

            if latest:
                params["latest"] = "true"

            payload, error = _request_json(
                session=session,
                source="Africa API",
                endpoint=endpoint,
                url=f"{get_env('AFRICA_API_BASE_URL')}{endpoint}",
                headers=headers,
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["indicators"] = {
                    "country_code": normalized_country,
                    "metric_keys": list(metric_keys)
                    if metric_keys
                    else None,
                    "category": indicator_category,
                    "latest": latest,
                    "records": payload,
                }

        # Trade

        if include_trade:
            endpoint = (
                f"/trade/overview/{normalized_country}"
            )

            params = {
                "top_limit": trade_top_limit,
            }

            if normalized_start_year is not None:
                params["start_year"] = normalized_start_year

            if normalized_end_year is not None:
                params["end_year"] = normalized_end_year

            payload, error = _request_json(
                session=session,
                source="Africa API",
                endpoint=endpoint,
                url=f"{get_env('AFRICA_API_BASE_URL')}{endpoint}",
                headers=headers,
                params=params,
            )

            if error:
                errors.append(error)
            else:
                data["trade"] = {
                    "country_code": normalized_country,
                    "records": payload,
                }

        return _build_tool_result(
            tool_name="macro_context_tool",
            request={
                "country_code": normalized_country,
                "include_signals": include_signals,
                "include_fx": include_fx,
                "include_indicators": include_indicators,
                "include_trade": include_trade,
                "base_currency": normalized_base_currency,
                "quote_currencies": normalized_quotes,
                "metric_keys": (
                    list(metric_keys) if metric_keys else None
                ),
                "indicator_category": indicator_category,
                "start_year": normalized_start_year,
                "end_year": normalized_end_year,
                "latest": latest,
                "trade_top_limit": trade_top_limit,
            },
            data=data,
            errors=errors,
        )

    except ValueError as exc:
        return _build_tool_result(
            tool_name="macro_context_tool",
            request={
                "country_code": country_code,
            },
            data={},
            errors=[
                _error(
                    code="INVALID_ARGUMENT",
                    message=str(exc),
                    source="macro_context_tool",
                    endpoint="local_validation",
                    retryable=False,
                )
            ],
        )
    