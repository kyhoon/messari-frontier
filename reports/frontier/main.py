import os
from datetime import datetime

import altair as alt
import datapane as dp

report = dp.Report(
    dp.Text(
        f"""
        Updated at {datetime.now()}
        """
    )
)


if __name__ == "__main__":
    dp.login(token=os.environ["DATAPANE_TOKEN"])
    report.upload(name="test")
