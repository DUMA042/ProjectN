import pandas as pd
from sqlalchemy import text
from owl.load.database import get_session


def run_query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with get_session() as session:
        result = session.execute(text(sql), params or {})
        rows = result.fetchall()
        columns = list(result.keys())
        return pd.DataFrame(rows, columns=columns)
