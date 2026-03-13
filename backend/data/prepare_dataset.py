import pandas as pd
from pathlib import Path


def load_sample(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def main():
    src = "backend/sample_data/sample.csv"
    dst_dir = Path("backend/data")
    dst_dir.mkdir(parents=True, exist_ok=True)
    df = load_sample(src)
    df.to_csv(dst_dir / "raw.csv", index=False)


if __name__ == "__main__":
    main()