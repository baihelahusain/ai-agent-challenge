import pandas as pd
from custom_parsers.icici_parser import parse

def test_icici_parser():
    """
    Test the ICICI parser against the ground truth CSV.
    """
    # Path to the sample PDF and CSV
    pdf_path = "data/icici/icici_sample.pdf"
    csv_path = "data/icici/icici_sample.csv"

    # Run parser
    df = parse(pdf_path)

    # Load expected CSV
    expected = pd.read_csv(csv_path)

    # Ensure DataFrame equality
    assert df.equals(expected), "Parsed DataFrame does not match expected output"
