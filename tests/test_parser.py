import os
import pandas as pd
from importlib import import_module

def test_bank_parser():
    """Test dynamically imported bank parser against expected CSV."""
    bank = os.environ.get("TARGET_BANK", "icici").lower()

    pdf_path = f"data/{bank}/{bank}_sample.pdf"
    csv_path = f"data/{bank}/{bank}_sample.csv"
    parser_module = import_module(f"custom_parsers.{bank}_parser") #for all type of input banks

    df = parser_module.parse(pdf_path)
    
    expected = pd.read_csv(csv_path)

    print(f"\n Parsed {len(df)} transactions, expected {len(expected)}")
    
    assert len(df) == len(expected), f"Row count mismatch: got {len(df)}, expected {len(expected)}"
    
    # Align column order
    df = df[expected.columns.tolist()]
    
    for col in expected.columns:
        if not df[col].equals(expected[col]):
            print(f"\n X Column '{col}' mismatch:")
            print(f"First few parsed values: {df[col].head().tolist()}")
            print(f"First few expected values: {expected[col].head().tolist()}")
    
    # Final comparison
    assert df.equals(expected), f"Parsed DataFrame does not match expected output for {bank}"
    
    print(f" All {len(df)} transactions match!")

