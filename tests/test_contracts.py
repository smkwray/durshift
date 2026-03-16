from __future__ import annotations

import pandas as pd
import pytest

from durshift.data.contracts import validate_required_columns


def test_validate_required_columns_passes_when_present():
    frame = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    validate_required_columns(frame, ["a", "b"], "test_dataset")


def test_validate_required_columns_raises_on_missing():
    frame = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="missing required columns: b, c"):
        validate_required_columns(frame, ["a", "b", "c"], "test_dataset")
