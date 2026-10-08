from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
REQUIRED_DATA_FILES = (
    "train-test.csv",
    "validation.csv",
    "december-chart-inputs.csv",
    "validation-predictions-template.csv",
)


# ---------------------------------------------------------
# Data ingestion
# ---------------------------------------------------------

def ensure_data_directory() -> Path:
    """Ensure the project data directory exists and return its path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def load_csv(file_name: str) -> pd.DataFrame:
    """
    Load a CSV file from the project's data directory.

    Parameters
    ----------
    file_name : str
        Name of the CSV file inside the data directory.

    Returns
    -------
    pd.DataFrame
        Loaded dataset.
    """

    data_dir = ensure_data_directory()
    file_path = data_dir / file_name

    if not file_path.exists():
        missing_files = [
            f"{dataset_name} in {data_dir}"
            for dataset_name in REQUIRED_DATA_FILES
            if not (data_dir / dataset_name).exists()
        ]
        message = (
            f"CSV file not found: {file_path}. "
            f"Place the required files in {data_dir}. "
            f"Missing files: {', '.join(missing_files) if missing_files else file_name}"
        )
        raise FileNotFoundError(message)

    df = pd.read_csv(file_path)

    if df.empty:
        raise ValueError(
            f"Data file is empty: {file_path}"
        )

    print(f"\nLoaded: {file_name}")
    print(f"Shape: {df.shape}")

    return df


# ---------------------------------------------------------
# Basic data validation
# ---------------------------------------------------------

def validate_dataframe(df: pd.DataFrame, name: str) -> None:
    """
    Perform basic validation checks on a DataFrame.
    """

    print(f"\n{'=' * 60}")
    print(f"VALIDATION: {name}")
    print(f"{'=' * 60}")

    # Shape
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    # Duplicate rows
    duplicate_count = df.duplicated().sum()
    print(f"Duplicate rows: {duplicate_count}")

    # Missing values
    missing_values = df.isnull().sum()
    missing_values = missing_values[missing_values > 0]

    if missing_values.empty:
        print("Missing values: None")
    else:
        print("\nMissing values:")
        print(missing_values.sort_values(ascending=False))

    # Data types
    print("\nData types:")
    print(df.dtypes)

    # Columns
    print("\nColumns:")
    print(list(df.columns))


# ---------------------------------------------------------
# Dataset inspection
# ---------------------------------------------------------

def inspect_dataframe(df: pd.DataFrame, name: str) -> None:
    """
    Display a basic overview of the dataset.
    """

    print(f"\n{'=' * 60}")
    print(f"INSPECTION: {name}")
    print(f"{'=' * 60}")

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nLast 5 rows:")
    print(df.tail())

    print("\nStatistical summary:")
    print(df.describe(include="all").transpose())


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------

def run_pipeline():
    """
    Execute the initial data pipeline.

    Currently this pipeline performs:
    1. Data ingestion
    2. Basic validation
    3. Dataset inspection

    EDA, feature engineering and model training
    will be added in later stages.
    """

    ensure_data_directory()
    missing_files = [
        file_name for file_name in REQUIRED_DATA_FILES
        if not (DATA_DIR / file_name).exists()
    ]
    if missing_files:
        raise FileNotFoundError(
            "Missing required dataset files in "
            f"{DATA_DIR}: {', '.join(missing_files)}"
        )

    print("\n" + "=" * 60)
    print("SPOTTER FREIGHT RATE ML PIPELINE")
    print("=" * 60)

    # -----------------------------------------------------
    # 1. Load development/training data
    # -----------------------------------------------------

    train_df = load_csv("train-test.csv")

    # -----------------------------------------------------
    # 2. Load validation data
    # -----------------------------------------------------

    validation_df = load_csv("validation.csv")

    # -----------------------------------------------------
    # 3. Load December chart input data
    # -----------------------------------------------------

    december_df = load_csv("december-chart-inputs.csv")

    # -----------------------------------------------------
    # 4. Load prediction template
    # -----------------------------------------------------

    template_df = load_csv(
        "validation-predictions-template.csv"
    )

    # -----------------------------------------------------
    # 5. Validate datasets
    # -----------------------------------------------------

    validate_dataframe(
        train_df,
        "Training / Development Data"
    )

    validate_dataframe(
        validation_df,
        "Validation Data"
    )

    validate_dataframe(
        december_df,
        "December Chart Input Data"
    )

    validate_dataframe(
        template_df,
        "Validation Prediction Template"
    )

    # -----------------------------------------------------
    # 6. Basic inspection
    # -----------------------------------------------------

    inspect_dataframe(
        train_df,
        "Training / Development Data"
    )

    # -----------------------------------------------------
    # 7. Return datasets for future stages
    # -----------------------------------------------------

    return {
        "train": train_df,
        "validation": validation_df,
        "december": december_df,
        "template": template_df,
    }


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    datasets = run_pipeline()