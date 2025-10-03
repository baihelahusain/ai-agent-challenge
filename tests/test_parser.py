import os
import pandas as pd
from importlib import import_module

def test_bank_parser():
    # Detect target bank from environment variable (set by agent.py when calling pytest)
    bank = os.environ.get("TARGET_BANK", "icici").lower()

    pdf_path = f"data/{bank}/{bank}_sample.pdf"
    csv_path = f"data/{bank}/{bank}_sample.csv"

    # Dynamically import the parser for this bank
    parser_module = import_module(f"custom_parsers.{bank}_parser")

    df = parser_module.parse(pdf_path)
    expected = pd.read_csv(csv_path)

    # Align column order before comparison
    df = df[expected.columns.tolist()]

    assert df.equals(expected), f"Parsed DataFrame does not match for {bank}"

