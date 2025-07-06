#!/usr/bin/env python3
"""
Fetch every Teltonika "Data Sending Parameters ID" table from the FMB920 wiki
page and export them all into one CSV.

Usage:
    python fmb920_to_csv.py  [output.csv]

If you omit the filename it defaults to  fmb920_parameters.csv
"""

import sys, re, requests, pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path

URL = "https://wiki.teltonika-gps.com/view/FMB920_Teltonika_Data_Sending_Parameters_ID"
OUTFILE = Path(sys.argv[1] if len(sys.argv) > 1 else "fmb920_parameters.csv")

def tidy(txt) -> str:
    """Return a clean, single-line string.

    Pandas may return tuple / list column labels when the HTML table
    has multi-row headers.  Join such labels into one string first so
    the subsequent regex works without raising ``TypeError``.
    """

    # 1.  Normalise to a string ------------------------------------------------
    if isinstance(txt, (tuple, list)):
        # Flatten multi-level headers, dropping empties (e.g. NaN/None)
        txt = " ".join(str(t) for t in txt if t and str(t).strip())
    else:
        txt = str(txt)

    # 2.  Collapse whitespace + trim -----------------------------------------
    return re.sub(r"\s+", " ", txt).strip()

def main() -> None:
    # --- 1  download --------------------------------------------------------
    html = requests.get(URL, timeout=30).text

    # --- 2  parse -----------------------------------------------------------
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("table.nd-othertables_2")   # same class Teltonika always uses
    if not tables:
        raise RuntimeError("No nd-othertables_2 tables found – layout may have changed.")

    frames = []
    for tbl in tables:
        df = pd.read_html(str(tbl))[0]
        df.columns = [tidy(c) for c in df.columns]   # clean headers
        # Drop stray header rows repeated inside some tables (where first cell
        # should start with a digit).  Ensure the column is treated as string
        # before calling the ``.str`` accessor to avoid dtype issues.
        df = df[df[df.columns[0]].astype(str).str.contains(r"^\d", na=False)]
        frames.append(df.reset_index(drop=True))

    full_df = pd.concat(frames, ignore_index=True)

    # --- 3  save ------------------------------------------------------------
    full_df.to_csv(OUTFILE, index=False, encoding="utf-8")
    print(f"✅  Saved {len(full_df)} rows to {OUTFILE}")

if __name__ == "__main__":
    main()
