"""Yahoo Finance adapter for normalized long-term fundamentals.

The adapter is deliberately isolated behind FundamentalsProvider so another
verified provider can replace it without changing the analysis layer.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


class YFinanceUnavailableError(RuntimeError):
    """Raised when the optional Yahoo Finance dependency is unavailable."""


class YFinanceFundamentalsProvider:
    """Fetch normalized company fundamentals from Yahoo Finance."""

    source = "Yahoo Finance via yfinance"

    @staticmethod
    def is_available() -> bool:
        """Return whether yfinance can be imported in the current runtime."""
        try:
            import yfinance  # noqa: F401
        except ImportError:
            return False
        return True

    @staticmethod
    def _client():
        """Load yfinance lazily so the dashboard can start without it."""
        try:
            import yfinance as yf
        except ImportError as error:
            raise YFinanceUnavailableError(
                "yfinance is not installed in the current runtime. "
                "Yahoo Finance fundamentals are unavailable."
            ) from error
        return yf

    def get_fundamentals(self, symbol: str) -> FundamentalsSnapshot:
        """Fetch one company's fundamentals or raise a provider error."""
        yf = self._client()
        ticker = yf.Ticker(symbol)
        info = ticker.info
        income = ticker.financials
        cashflow = ticker.cashflow
        balance = ticker.balance_sheet
        periods = self._periods(income, cashflow, balance)
        return FundamentalsSnapshot(
            symbol=symbol,
            company_name=str(info.get("longName") or info.get("shortName") or symbol),
            as_of=datetime.now(timezone.utc),
            source=self.source,
            periods=periods,
            roe=self._percent(info.get("returnOnEquity")),
            roce=None,
            debt_to_equity=self._number(info.get("debtToEquity")),
            market_cap=self._number(info.get("marketCap")),
            pe_ratio=self._number(info.get("trailingPE")),
            pb_ratio=self._number(info.get("priceToBook")),
            ev_to_ebitda=self._number(info.get("enterpriseToEbitda")),
        )

    @staticmethod
    def _number(value: object) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    @staticmethod
    def _percent(value: object) -> float | None:
        number = YFinanceFundamentalsProvider._number(value)
        return number * 100 if number is not None and abs(number) <= 1 else number

    @staticmethod
    def _value(frame: pd.DataFrame, names: tuple[str, ...], column: object) -> float | None:
        if frame.empty:
            return None
        for name in names:
            if name in frame.index and column in frame.columns:
                return YFinanceFundamentalsProvider._number(frame.loc[name, column])
        return None

    @classmethod
    def _periods(
        cls,
        income: pd.DataFrame,
        cashflow: pd.DataFrame,
        balance: pd.DataFrame,
    ) -> tuple[FinancialPeriod, ...]:
        columns = [column for column in income.columns if column in balance.columns]
        periods: list[FinancialPeriod] = []
        for column in columns:
            period_end = pd.Timestamp(column).date()
            revenue = cls._value(income, ("Total Revenue", "Operating Revenue"), column)
            earnings = cls._value(
                income,
                ("Net Income", "Net Income Common Stockholders"),
                column,
            )
            eps = cls._value(income, ("Diluted EPS", "Basic EPS"), column)
            operating_cash_flow = cls._value(
                cashflow,
                ("Operating Cash Flow", "Total Cash From Operating Activities"),
                column,
            )
            free_cash_flow = cls._value(cashflow, ("Free Cash Flow",), column)
            debt = cls._value(
                balance,
                ("Total Debt", "Long Term Debt And Capital Lease Obligation"),
                column,
            )
            equity = cls._value(
                balance,
                ("Stockholders Equity", "Common Stock Equity"),
                column,
            )
            periods.append(
                FinancialPeriod(
                    period_end=period_end,
                    revenue=revenue,
                    earnings=earnings,
                    eps=eps,
                    operating_cash_flow=operating_cash_flow,
                    free_cash_flow=free_cash_flow,
                    debt=debt,
                    equity=equity,
                )
            )
        return tuple(sorted(periods, key=lambda item: item.period_end, reverse=True))
