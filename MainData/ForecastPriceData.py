import os
import pandas as pd
import numpy as np
import inputs
from inputs import YEAR_START, electricity_tax, margin_tradingcompany_energy
from .TariffPeriod import TariffPeriod


class ForecastPriceData:
    """
    Loads electricity price forecast and target CSV files and builds hourly price
    DataFrames compatible with ElectricityPriceData for use in Operations.

    Expected CSV format for both forecast and target files:
        - 'window_start': start datetime of the forecasting window (e.g. '2024-01-01')
        - Rows within each window_start group are in chronological order (hour 0, 1, 2, ...)
        - Each row represents one hour offset from window_start
        - 168h file: 168 rows per window_start (one week)
        - 24h file: 24 rows per window_start (one day)
        - Columns include the forecast/target price columns specified in inputs

    Provides:
        - decision_price_df:   Spot_Price1 replaced with forecast values (for trading decisions)
        - settlement_price_df: Spot_Price1 and Spot_Price2 replaced with target actuals (for cashflow settlement)
    """

    def __init__(self, base_electricity_price_df, project_life):
        """
        Parameters
        ----------
        base_electricity_price_df : pd.DataFrame
            The fully-processed electricity price DataFrame from ElectricityPriceData
            (already extended to project_life). Used as the structural base and for
            columns not related to price (TariffPeriod, DateTime, EnergyTermTolls, etc.).
        project_life : int
            Number of years in the project lifetime.
        """
        self._base_df = base_electricity_price_df.copy()
        self._project_life = project_life
        self._year_start = YEAR_START

        self._forecast_filepath = os.path.join("MainData", inputs.forecast_file)
        self._targets_filepath = os.path.join("MainData", inputs.targets_file)
        self._forecast_column = inputs.forecast_column
        self._target_column = inputs.target_column

        self._decision_price_df = self._build_decision_price_df()
        self._settlement_price_df = self._build_settlement_price_df()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_decision_price_df(self):
        """Return hourly price DataFrame with Spot_Price1 = DA forecast prices."""
        return self._decision_price_df

    def get_settlement_price_df(self):
        """Return hourly price DataFrame with Spot_Price1/Spot_Price2 = actual target prices."""
        return self._settlement_price_df

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_window_file(self, filepath, value_column):
        """
        Parse a windowed forecast/target CSV into an hourly price Series indexed by
        (Year, Month, Day, Hour).

        The file must have a 'window_start' column. Rows within each group of the
        same window_start are assumed to be consecutive hours (offset 0, 1, 2, …).

        Returns
        -------
        pd.DataFrame with columns [Year, Month, Day, Hour, 'price']
        """
        df = pd.read_csv(filepath)

        if 'window_start' not in df.columns:
            raise ValueError(
                f"Forecast/target file '{filepath}' must contain a 'window_start' column."
            )
        if value_column not in df.columns:
            raise ValueError(
                f"Column '{value_column}' not found in '{filepath}'. "
                f"Available columns: {df.columns.tolist()}"
            )

        df['window_start'] = pd.to_datetime(df['window_start'])
        df = df.sort_values('window_start').reset_index(drop=True)

        # Vectorised: compute hour-offset within each window_start group
        df['_hour_offset'] = df.groupby('window_start').cumcount()
        df['_datetime'] = df['window_start'] + pd.to_timedelta(df['_hour_offset'], unit='h')

        df['Year'] = df['_datetime'].dt.year
        df['Month'] = df['_datetime'].dt.month
        df['Day'] = df['_datetime'].dt.day
        df['Hour'] = df['_datetime'].dt.hour

        result = df[['Year', 'Month', 'Day', 'Hour', value_column]].copy()
        result = result.rename(columns={value_column: 'price'})

        # Drop duplicate timestamps — keep last occurrence (latest available forecast)
        result = result.drop_duplicates(subset=['Year', 'Month', 'Day', 'Hour'], keep='last')
        result = result.reset_index(drop=True)
        return result

    def _align_to_base(self, price_series_df, price_col_name):
        """
        Left-join a (Year, Month, Day, Hour, price) DataFrame onto the base
        electricity price DataFrame, returning a column aligned to the base index.

        Missing hours (NaN after join) are forward-filled then back-filled so that
        gaps in forecast coverage are handled gracefully.
        """
        merged = self._base_df[['Year', 'Month', 'Day', 'Hour']].copy()
        merged = merged.merge(
            price_series_df.rename(columns={'price': price_col_name}),
            on=['Year', 'Month', 'Day', 'Hour'],
            how='left'
        )
        merged[price_col_name] = (
            merged[price_col_name].ffill().bfill()
        )
        return merged[price_col_name].values

    def _apply_tolls_and_taxes(self, raw_price_series, base_df):
        """
        Apply energy-term tolls, other charges, trading margin and electricity tax
        to a raw spot-price series — mirroring ElectricityPriceData logic.
        """
        tolls = base_df.get('EnergyTermTolls', pd.Series(0.0, index=base_df.index))
        other = base_df.get('EnergyTermOtherCharges', pd.Series(0.0, index=base_df.index))
        adjusted = (
            raw_price_series
            + tolls.values * 1000
            + other.values * 1000
            + margin_tradingcompany_energy * 1000
        ) * (1 + electricity_tax / 100)
        return adjusted

    def _build_decision_price_df(self):
        """
        Build a price DataFrame for trading decisions.
        Spot_Price1 is replaced with the DA forecast column.
        Spot_Price2 is kept from the base (actual prices) — it is not used during
        the optimisation itself, only in cashflow settlement which uses settlement_price_df.
        """
        forecast_series = self._load_window_file(self._forecast_filepath, self._forecast_column)
        forecast_raw = self._align_to_base(forecast_series, 'forecast_price')

        decision_df = self._base_df.copy()
        # Replace Spot_Price1 with forecast values (with tolls/taxes applied)
        decision_df['Spot_Price1'] = self._apply_tolls_and_taxes(
            pd.Series(forecast_raw, index=decision_df.index), decision_df
        )
        return decision_df

    def _build_settlement_price_df(self):
        """
        Build a price DataFrame for cashflow settlement.
        Both Spot_Price1 and Spot_Price2 come from the target (actual) column,
        so that buying and selling costs/revenues are settled at actual market prices.
        """
        target_series = self._load_window_file(self._targets_filepath, self._target_column)
        target_raw = self._align_to_base(target_series, 'target_price')

        settlement_df = self._base_df.copy()

        # Spot_Price1 (buy settlement): apply tolls and taxes
        settlement_df['Spot_Price1'] = self._apply_tolls_and_taxes(
            pd.Series(target_raw, index=settlement_df.index), settlement_df
        )
        # Spot_Price2 (sell settlement): raw actual price (no tolls for selling)
        settlement_df['Spot_Price2'] = target_raw

        return settlement_df
