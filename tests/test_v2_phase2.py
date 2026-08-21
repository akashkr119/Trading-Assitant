from trading_assistant.v2.backtesting import BacktestTrade, run_backtest
from trading_assistant.v2.paper_trading import PaperPortfolio, PaperPosition
from trading_assistant.v2.trade_journal import JournalEntry, summarize_journal


def test_backtest_reports_expectancy_and_drawdown() -> None:
    result = run_backtest(
        [
            BacktestTrade("AAA", "BUY", 100, 110, 95, 115),
            BacktestTrade("BBB", "BUY", 100, 95, 90, 120),
        ]
    )
    assert result.total_trades == 2
    assert result.winning_trades == 1
    assert result.losing_trades == 1
    assert result.total_r == 1.5
    assert result.max_drawdown_r > 0


def test_backtest_empty_input_is_safe() -> None:
    result = run_backtest([])
    assert result.total_trades == 0
    assert result.win_rate == 0.0
    assert result.profit_factor is None


def test_paper_portfolio_marks_positions_without_broker_execution() -> None:
    portfolio = PaperPortfolio(100_000)
    portfolio.open_position(
        PaperPosition("AAA", "BUY", 100, 100, 95, 110)
    )
    assert portfolio.realized_free_cash == 90_000
    assert portfolio.mark_to_market({"AAA": 105}) == 100_500


def test_paper_portfolio_rejects_excessive_position() -> None:
    portfolio = PaperPortfolio(10_000)
    try:
        portfolio.open_position(PaperPosition("AAA", "BUY", 200, 100, 95, 110))
    except ValueError as error:
        assert "insufficient" in str(error)
    else:
        raise AssertionError("Expected insufficient paper cash error")


def test_journal_identifies_best_setup() -> None:
    summary = summarize_journal(
        [
            JournalEntry("AAA", "IT", "breakout", "BULLISH", "BUY", 2.0, "WIN"),
            JournalEntry("BBB", "IT", "breakout", "BULLISH", "BUY", 1.0, "WIN"),
            JournalEntry("CCC", "BANK", "reversal", "NEUTRAL", "BUY", -1.0, "LOSS"),
        ]
    )
    assert summary["total_trades"] == 3
    assert summary["best_setup"] == "breakout"
    assert summary["expectancy_r"] == 2 / 3
