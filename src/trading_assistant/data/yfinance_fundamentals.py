"""Yahoo Finance adapter for normalized long-term fundamentals.

The adapter is deliberately isolated behind FundamentalsProvider so another
verified provider can replace it without changing the analysis layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
import subprocess
import sys

import pandas as pd

from trading_assistant.data.fundamentals import FinancialPeriod, FundamentalsSnapshot


class YFinanceUnavailableError(RuntimeError):
    """Raised when the optional Yahoo Finance dependency is unavailable."""


class YFinanceFundamentalsProvider:
    """Fetch normalized company fundamentals from Yahoo Finance."""

    source = "Yahoo Finance via yfinance"
    _bootstrap_attempted = False

    @classmethod
    def is_available(cls) -> bool:
        """Return whether yfinance is importable, repairing the runtime once if needed."""
        if cls._import_available():
            return True
        if cls._bootstrap_attempted:
            return False
        cls._bootstrap_attempted = True
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "yfinance>=0.2,<1",
                    "--disable-pip-version-check",
                    "--no-input",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return cls._import_available()

    @staticmethod
    def _import_available() -> bool:
        try:
            import yfinance  # noqa: F401
        except ImportError:
            return False
        return True

    @classmethod
    def _client(cls):
        """Load yfinance lazily and repair the runtime once if necessary."""
        if not cls.is_available():
            raise YFinanceUnavailableError(
                "yfinance is unavailable in the current runtime. "
                "Install the project dependencies and restart the application."
            )
        try:
            import yfinance as yf
        except ImportError as error:
            raise YFinanceUnavailableError(
                "yfinance is unavailable in the current runtime. "
                "Install the project dependencies and restart the application."
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
        debt_to_equity = self._number(info.get("debtToEquity"))
        if debt_to_equity is None and periods:
            latest = periods[0]
            if latest.debt is not None and latest.equity not in (None, 0):
                debt_to_equity = latest.debt / latest.equity

        return FundamentalsSnapshot(
            symbol=symbol,
            company_name=str(info.get("longName") or info.get("shortName") or symbol),
            as_of=datetime.now(timezone.utc),
            source=self.source,
            periods=periods,
            roe=self._percent(info.get("returnOnEquity")),
            roce=self._roce(income, balance),
            debt_to_equity=debt_to_equity,
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
    def _roce(cls, income: pd.DataFrame, balance: pd.DataFrame) -> float | None:
        """Estimate ROCE from EBIT and average debt-plus-equity capital."""
        if income.empty or balance.empty:
            return None
        columns = [column for column in income.columns if column in balance.columns]
        if not columns:
            return None
        current = columns[0]
        ebit = cls._value(income, ("EBIT", "Operating Income"), current)
        if ebit is None:
            return None

        capital_values: list[float] = []
        for column in columns[:2]:
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
            if debt is not None and equity is not None:
                capital_values.append(debt + equity)
        if not capital_values or sum(capital_values) <= 0:
            return None
        capital_employed = sum(capital_values) / len(capital_values)
        return ebit / capital_employed * 100

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
