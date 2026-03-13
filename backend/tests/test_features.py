import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.features import extract_features


def test_extract_features_basic():
    df = extract_features("https://example.com/path?x=1&y=2", "<html><body><form><input/></form></body></html>")
    assert "length" in df.columns
    assert "tld" in df.columns
    assert df.iloc[0]["count_query_params"] == 2