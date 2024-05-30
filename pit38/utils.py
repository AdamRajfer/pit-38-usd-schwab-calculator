from typing import Any, Optional

import pandas as pd


def try_to_cast_string_to_float(x: Any) -> Optional[float]:
    try:
        assert "," in x
        return float(x.replace(",", "."))
    except (AttributeError, ValueError, AssertionError, TypeError):
        return None


def to_zero_if_null(x: Any) -> float:
    return 0.0 if pd.isnull(x) else x
