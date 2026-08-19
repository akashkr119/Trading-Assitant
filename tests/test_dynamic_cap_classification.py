from io import BytesIO

import pandas as pd

from trading_assistant.monitoring.dynamic_cap_classification import _parse_excel


def test_parse_amfi_classification_maps_nse_symbols() -> None:
    frame = pd.DataFrame(
        [
            {"NSE Symbol": "AAA", "ISIN": "INEAAA", "Category": "Large Cap"},
            {"NSE Symbol": "BBB", "ISIN": "INEBBB", "Category": "Mid Cap"},
            {"NSE Symbol": "CCC", "ISIN": "INECCC", "Category": "Small Cap"},
        ]
    )
    payload = BytesIO()
    with pd.ExcelWriter(payload, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False)

    result = _parse_excel(payload.getvalue())

    assert result["AAA"].segment == "Large Cap"
    assert result["BBB"].segment == "Mid Cap"
    assert result["CCC"].segment == "Small Cap"
    assert result["BBB"].isin == "INEBBB"
