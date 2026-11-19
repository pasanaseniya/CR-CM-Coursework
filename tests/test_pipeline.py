import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.data_pipeline import (
    calculate_weekly_returns,
    calculate_weekly_beta,
    compute_adapted_rfm_for_series,
)

def test_calculate_weekly_returns():
    # Construct 14 days of prices (spanning 2 Friday endpoints)
    dates = pd.date_range("2024-01-01", periods=14, freq="D")
    prices = pd.DataFrame({
        "AAPL": [100.0 + i for i in range(14)]
    }, index=dates)
    
    # Weekly Friday resample:
    # 2024-01-05 (Fri): index 4 -> price 104.0
    # 2024-01-12 (Fri): index 11 -> price 111.0
    # 2024-01-14 (Sun): index 13 -> falls in next week (2024-01-19) -> price 113.0
    w_ret = calculate_weekly_returns(prices)
    
    assert "AAPL" in w_ret.columns
    # Check return between first Friday and second Friday: (111.0 / 104.0) - 1
    expected_ret = (111.0 / 104.0) - 1.0
    assert np.isclose(w_ret.loc["2024-01-12", "AAPL"], expected_ret)

def test_calculate_weekly_beta():
    weeks = pd.date_range("2023-01-06", periods=100, freq="W-FRI")
    np.random.seed(42)
    mkt = pd.Series(np.random.normal(0.002, 0.02, size=100), index=weeks)
    # Construct share with exact beta = 1.5 + noise
    noise = np.random.normal(0, 0.005, size=100)
    share = 1.5 * mkt + noise
    share_df = pd.DataFrame({"TEST": share})
    
    beta_df = calculate_weekly_beta(share_df, mkt, min_weeks=52)
    assert "TEST" in beta_df.index
    est_beta = beta_df.loc["TEST", "Beta"]
    assert np.isclose(est_beta, 1.5, atol=0.1)

def test_compute_adapted_rfm():
    # Generate 100 trading days
    dates = pd.bdate_range("2024-01-01", periods=100)
    # Base volume: constant 1,000,000
    volumes = np.full(100, 1_000_000.0)
    prices = np.full(100, 100.0)
    
    # Put an event at index 80: volume = 2,500,000 (> 2 * 1,000,000 = 2,000,000)
    volumes[80] = 2_500_000.0
    # Put another event at index 95: volume = 3,000,000
    volumes[95] = 3_000_000.0
    
    df = pd.DataFrame({
        "Close": prices,
        "Volume": volumes
    }, index=dates)
    
    obs_date = dates[-1] # index 99
    # The latest 60 sessions are indices 40..99. Both index 80 and index 95 fall in latest 60.
    # Latest event is at index 95 (dates[95]).
    expected_r = (obs_date - dates[95]).days
    expected_f = 2
    # Monetary = sum of Close * Volume over latest 60 sessions (indices 40..99)
    expected_m = (prices[40:] * volumes[40:]).sum()
    
    r, f, m = compute_adapted_rfm_for_series(df, obs_date=obs_date, window=60, baseline_window=20, threshold_mult=2.0)
    
    assert r == expected_r
    assert f == expected_f
    assert np.isclose(m, expected_m)
