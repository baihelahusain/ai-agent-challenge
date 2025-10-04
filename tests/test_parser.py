import os
import pandas as pd
from importlib import import_module

def test_bank_parser():
    """Test parser output against expected CSV, ignoring debit/credit columns."""

    bank = os.environ.get("TARGET_BANK", "icici").lower()
    pdf_path = f"data/{bank}/{bank}_sample.pdf"
    generated_csv_path = f"data/{bank}/{bank}_sample.csv"
    result_csv_path = "data/icici/result.csv"  # company-provided expected file

    parser_module = import_module(f"custom_parsers.{bank}_parser")
    df_generated = pd.read_csv(generated_csv_path)
    df_expected = pd.read_csv(result_csv_path)

    # Compare only key logical columns
    cols_to_compare = ["Date", "Description", "Balance"]

    # Ensure both have required columns
    for col in cols_to_compare:
        assert col in df_generated.columns, f"{col} missing in generated CSV"
        assert col in df_expected.columns, f"{col} missing in expected CSV"

    # Merge and compare selected columns
    merged = df_generated.merge(df_expected, on=cols_to_compare, how="outer", indicator=True)
    only_left = merged[merged["_merge"] == "left_only"]
    only_right = merged[merged["_merge"] == "right_only"]

    print(f"\n Matched {len(merged) - len(only_left) - len(only_right)} rows out of {len(merged)} total.")

    assert only_left.empty and only_right.empty, (
        f" Mismatch detected in key columns. "
        f"{len(only_left)} rows only in generated, {len(only_right)} rows only in expected."
    )
