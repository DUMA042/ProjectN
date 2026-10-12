"""Day-first date rule: ambiguous strings read DD/MM, ISO stays stable."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from owl.transform.dates import coerce_dayfirst, parse_dayfirst


def test_ambiguous_strings_read_day_first():
    assert parse_dayfirst("01/05/2026") == date(2026, 5, 1)
    assert parse_dayfirst("02/03/2026") == date(2026, 3, 2)
    assert parse_dayfirst("11/12/2026") == date(2026, 12, 11)


def test_iso_and_unambiguous_stable():
    assert parse_dayfirst("2026-05-01") == date(2026, 5, 1)
    assert parse_dayfirst("2026-08-03 06:05:35") == date(2026, 8, 3)
    assert parse_dayfirst("15/01/2026") == date(2026, 1, 15)
    assert parse_dayfirst(date(2026, 5, 1)) == date(2026, 5, 1)
    assert parse_dayfirst(datetime(2026, 5, 1, 8, 30)) == date(2026, 5, 1)


def test_garbage_gives_none_never_raises():
    assert parse_dayfirst("PENDING") is None
    assert parse_dayfirst("") is None
    assert parse_dayfirst(None) is None
    assert parse_dayfirst(pd.NaT) is None
    assert parse_dayfirst(float("nan")) is None


def test_coerce_dayfirst_mixed_column():
    s = pd.Series(["01/05/2026", "2026-06-01", "not-a-date", "15/01/2026"])
    out = coerce_dayfirst(s)
    assert out.iloc[0].date() == date(2026, 5, 1)
    assert out.iloc[1].date() == date(2026, 6, 1)
    assert pd.isna(out.iloc[2])
    assert out.iloc[3].date() == date(2026, 1, 15)
