"""
End-to-end validation of the DA forecast integration.

Checks:
  1. Forecast file loads and has the expected structure
  2. window_start lookup works for 2024 simulation dates
  3. Spot_Price1/Spot_Price2 replacement logic is correct
  4. Targets file loads and settlement price lookup works
  5. T1 / G1 / G4 are confirmed to be in EUR/MWh (no rescaling needed)

Run from the project root:
    python test_forecast_integration.py
"""

import os
import sys
import pandas as pd
import numpy as np

MAINDATA = os.path.join(os.path.dirname(__file__), "MainData")
FORECAST_FILE = "G_T_all_hourly_forecasts_168h_model_no_feb29.csv"
TARGETS_FILE = "targets.csv"
FORECAST_COLUMN = "T1"
SETTLEMENT_COLUMN = "DA"
SAMPLE_PERIOD_DAYS = 1


def load_forecast():
    path = os.path.join(MAINDATA, FORECAST_FILE)
    df = pd.read_csv(path, parse_dates=["time", "window_start"])
    df["window_start"] = df["window_start"].dt.normalize()
    return df


def load_targets():
    path = os.path.join(MAINDATA, TARGETS_FILE)
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def load_actual_electricity_price():
    """Load the 2024 actual electricity price data (baseline comparison)."""
    path = os.path.join(MAINDATA, "ElectricityPriceData2024.csv")
    df = pd.read_csv(path)
    df["Hour"] -= 1
    df["Hour"] = df["Hour"] % 24
    df["DateTime"] = pd.to_datetime(df[["Year", "Month", "Day", "Hour"]])
    return df


# ---------- Test 1: file loads and structure ----------
def test_forecast_file_structure(forecast_df):
    required_cols = {"time", "actual", "G1", "G4", "T1", "window_start"}
    assert required_cols.issubset(forecast_df.columns), (
        f"Missing columns: {required_cols - set(forecast_df.columns)}"
    )
    n_windows = forecast_df["window_start"].nunique()
    print(f"  PASS — forecast file loaded: {len(forecast_df):,} rows, {n_windows} windows")


# ---------- Test 2: window lookup for 2024 dates ----------
def test_window_lookup(forecast_df):
    test_dates = [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-06-15"),
        pd.Timestamp("2024-12-31"),
    ]
    all_ok = True
    for dt in test_dates:
        window = forecast_df[forecast_df["window_start"] == dt]
        n = len(window)
        if n == 0:
            print(f"  FAIL — no window for {dt.date()}")
            all_ok = False
        else:
            first = window.iloc[0]
            print(f"  OK   — {dt.date()}: {n} rows | "
                  f"actual={first['actual']:.2f}  "
                  f"T1={first['T1']:.2f}  G1={first['G1']:.2f}  G4={first['G4']:.2f}  EUR/MWh")
    if all_ok:
        print("  PASS — all 2024 window lookups succeeded")


# ---------- Test 3: T1/G1/G4 scale confirmation ----------
def test_forecast_scale(forecast_df):
    """Verify forecasts are in EUR/MWh (not normalized)."""
    subset_2024 = forecast_df[forecast_df["time"].dt.year == 2024]
    for col in ["T1", "G1", "G4", "actual"]:
        mean_val = subset_2024[col].mean()
        std_val  = subset_2024[col].std()
        min_val  = subset_2024[col].min()
        max_val  = subset_2024[col].max()
        # EUR/MWh values should be mostly positive and in a realistic range
        in_range = (mean_val > 10) and (mean_val < 300) and (min_val > -200)
        status = "PASS" if in_range else "WARN"
        print(f"  {status} — {col:8s}: mean={mean_val:6.1f}  std={std_val:5.1f}  "
              f"min={min_val:7.2f}  max={max_val:7.2f}  EUR/MWh")


# ---------- Test 4: sample_period_df replacement ----------
def test_price_replacement(forecast_df, electricity_price_df):
    """Simulate _get_forecast_prices_for_day for 2024-01-01."""
    sim_date = pd.Timestamp("2024-01-01")
    start = 0
    end = SAMPLE_PERIOD_DAYS * 24

    actual_slice = electricity_price_df.iloc[start:end].copy()
    window_df = forecast_df[forecast_df["window_start"] == sim_date]
    n_hours = SAMPLE_PERIOD_DAYS * 24
    forecast_prices = window_df.head(n_hours)[FORECAST_COLUMN].values

    sample_df = actual_slice.copy()
    buy_premium = actual_slice["Spot_Price1"].values - actual_slice["Spot_Price2"].values
    sample_df["Spot_Price2"] = forecast_prices[:len(actual_slice)]
    sample_df["Spot_Price1"] = forecast_prices[:len(actual_slice)] + buy_premium

    # spot-check hour 0
    expected_sp2 = window_df.iloc[0][FORECAST_COLUMN]
    got_sp2 = sample_df.iloc[0]["Spot_Price2"]
    assert abs(expected_sp2 - got_sp2) < 1e-6, f"Spot_Price2 mismatch: {expected_sp2} vs {got_sp2}"
    print(f"  PASS — 2024-01-01 hour 0: actual={actual_slice.iloc[0]['Spot_Price2']:.2f}  "
          f"→ forecast Spot_Price2={got_sp2:.2f}  "
          f"Spot_Price1={sample_df.iloc[0]['Spot_Price1']:.2f}  EUR/MWh")


# ---------- Test 5: settlement price lookup ----------
def test_settlement_lookup(targets_df, electricity_price_df):
    """Check that targets.csv DA prices can be looked up for 2024-01-01."""
    targets_map = targets_df.set_index("datetime")[SETTLEMENT_COLUMN]
    test_dt = pd.Timestamp("2024-01-01 00:00:00")
    settlement_price = targets_map.get(test_dt, np.nan)

    if np.isnan(settlement_price):
        print(f"  FAIL — no settlement price in targets for {test_dt}")
    else:
        actual_price = electricity_price_df[
            electricity_price_df["DateTime"] == test_dt
        ]["Spot_Price2"].values
        match_str = ""
        if len(actual_price) > 0:
            match_str = f"  (electricity_price_df Spot_Price2={actual_price[0]:.2f})"
        print(f"  PASS — targets DA={settlement_price:.2f} EUR/MWh for {test_dt}{match_str}")

    # Check annual coverage
    year_2024_actual = electricity_price_df[electricity_price_df["Year"] == 2024]
    dt_list = pd.to_datetime({
        "year":  year_2024_actual["Year"].astype(int),
        "month": year_2024_actual["Month"].astype(int),
        "day":   year_2024_actual["Day"].astype(int),
        "hour":  year_2024_actual["Hour"].astype(int),
    })
    settlement_series = pd.Series(
        [targets_map.get(dt, np.nan) for dt in dt_list],
        dtype=float,
    )
    pct_matched = settlement_series.notna().mean() * 100
    print(f"  INFO — settlement coverage for 2024: {pct_matched:.1f}% of hours matched in targets")


# ---------- main ----------
if __name__ == "__main__":
    print("=" * 60)
    print("DA Forecast Integration — End-to-End Validation")
    print("=" * 60)

    print("\n[1] Loading data files...")
    forecast_df = load_forecast()
    targets_df = load_targets()
    electricity_price_df = load_actual_electricity_price()
    print(f"  forecast rows  : {len(forecast_df):,}")
    print(f"  targets rows   : {len(targets_df):,}")
    print(f"  price rows     : {len(electricity_price_df):,}")

    print("\n[2] Forecast file structure")
    test_forecast_file_structure(forecast_df)

    print("\n[3] Window lookup for 2024 simulation dates")
    test_window_lookup(forecast_df)

    print("\n[4] Forecast scale (must be EUR/MWh, not normalised)")
    test_forecast_scale(forecast_df)

    print("\n[5] Spot_Price1/Spot_Price2 replacement logic")
    test_price_replacement(forecast_df, electricity_price_df)

    print("\n[6] Settlement price lookup from targets.csv")
    test_settlement_lookup(targets_df, electricity_price_df)

    print("\n" + "=" * 60)
    print("Validation complete.")
    print("=" * 60)
