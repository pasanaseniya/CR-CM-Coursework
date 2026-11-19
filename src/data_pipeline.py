"""
Data Acquisition, Validation, and Feature Pipeline for S&P 500 Equity Analysis
Module: 6BUIS017W CRM & CM With Business Intelligence (University of Westminster)
Coursework Specification: Market Analysis and Stock Segmentation Using RFM

Features Engineered:
1. Mean Weekly Return (arithmetic mean across Friday-ending weeks, 2021-2024)
2. Weekly Beta (vs. ^GSPC benchmark over aligned Friday returns)
3. Adapted RFM (Trading Activity):
   - Recency (R): Calendar days between latest qualifying high-volume day in history and 2024-12-31.
   - Frequency (F): Count of high-volume days in latest 60 trading sessions ending on 2024-12-31.
   - Monetary (M): Sum of daily dollar traded value (Close * Volume) across latest 60 sessions.
   - High-Volume Day: Volume > 2 * Mean(Volume of preceding 20 trading sessions, excluding current day).
"""

import os
import pickle
import datetime
import pandas as pd
import numpy as np
import yfinance as yf

STUDY_START = "2021-01-01"
STUDY_END = "2025-01-01" # Exclusive end date per spec
BENCHMARK_TICKER = "^GSPC"
OBSERVATION_DATE = "2024-12-31" # Last common trading day in 2024

def scrape_sp500_tickers():
    """
    Scrapes S&P 500 constituents from Wikipedia, cleans ticker symbols,
    records retrieval date, and captures GICS sector metadata.
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WestminsterUni/6BUIS017W"}
    
    # Read tables with custom User-Agent
    tables = pd.read_html(url, storage_options=headers)
    sp500_table = tables[0]
    
    # Standardize column names
    sp500_table = sp500_table.rename(columns={
        "Symbol": "Ticker",
        "Security": "Company",
        "GICS Sector": "GICS_Sector",
        "GICS Sub-Industry": "GICS_Sub_Industry"
    })
    
    # Clean ticker symbols: replace dots with hyphens (e.g. BRK.B -> BRK-B)
    sp500_table["Clean_Ticker"] = sp500_table["Ticker"].astype(str).str.replace(".", "-", regex=False)
    sp500_table["Retrieval_Date"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    return sp500_table

def download_market_data(tickers, start=STUDY_START, end=STUDY_END, cache_path="data/market_data_raw.pkl"):
    """
    Downloads daily price and volume data for tickers and the ^GSPC benchmark.
    Caches to disk to ensure reproducibility and guard against rate limiting.
    """
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if os.path.exists(cache_path):
        print(f"Loading cached raw market data from {cache_path}...")
        with open(cache_path, "rb") as f:
            return pickle.load(f)
            
    print(f"Downloading market data for {len(tickers)} tickers + benchmark ({BENCHMARK_TICKER})...")
    all_tickers = sorted(list(set(tickers + [BENCHMARK_TICKER])))
    
    # Download with auto_adjust=False to preserve both Close and Adj Close
    raw_df = yf.download(
        all_tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=True,
        group_by="ticker"
    )
    
    with open(cache_path, "wb") as f:
        pickle.dump(raw_df, f)
        
    print(f"Downloaded and saved market data to {cache_path}")
    return raw_df

def calculate_weekly_returns(prices_df):
    """
    Resamples daily prices into Friday-ending weeks (W-FRI) using the last available
    trading price in each week. Calculates percentage change: (P_t / P_{t-1}) - 1.
    """
    prices = prices_df.copy()
    if not isinstance(prices.index, pd.DatetimeIndex):
        prices.index = pd.to_datetime(prices.index)
    prices = prices.sort_index()
    
    # Resample to Friday-ending weeks, taking the last available trading price
    weekly_prices = prices.resample("W-FRI").last()
    
    # Weekly percentage return
    weekly_returns = weekly_prices.pct_change(fill_method=None)
    return weekly_returns

def calculate_weekly_beta(weekly_returns_df, market_returns_series, min_weeks=52):
    """
    Calculates weekly beta = Cov(share, market) / Var(market)
    over aligned Friday return dates for the full study period.
    """
    results = []
    market_clean = market_returns_series.replace([np.inf, -np.inf], np.nan)
    
    for col in weekly_returns_df.columns:
        share_clean = weekly_returns_df[col].replace([np.inf, -np.inf], np.nan)
        paired = pd.concat([share_clean.rename("share"), market_clean.rename("market")], axis=1).dropna()
        
        paired_count = len(paired)
        market_var = paired["market"].var(ddof=1) if paired_count > 1 else 0.0
        
        if paired_count >= min_weeks and market_var > 0:
            beta = paired["share"].cov(paired["market"]) / market_var
            mean_ret = paired["share"].mean()
        else:
            beta = np.nan
            mean_ret = np.nan
            
        results.append({
            "Ticker": col,
            "Beta": beta,
            "Mean_Weekly_Return": mean_ret,
            "Paired_Weeks": paired_count
        })
        
    return pd.DataFrame(results).set_index("Ticker")

def compute_adapted_rfm_for_series(df, obs_date=OBSERVATION_DATE, window=60, baseline_window=20, threshold_mult=2.0):
    """
    Computes Adapted RFM for a single stock's daily DataFrame (index: DatetimeIndex, cols: Close, Volume):
    1. Rolling 20-session baseline volume (excluding the evaluated day).
    2. High-volume event: Volume > threshold_mult * baseline.
    3. Recency (R): Calendar days between observation date and latest high-volume event in entire study history.
       (R = 0 if event on observation date; np.nan if no event in history).
    4. Frequency (F): Count of high-volume events in latest 60 sessions ending on obs_date.
    5. Monetary (M): Sum of (Close * Volume) across latest 60 sessions ending on obs_date.
    """
    data = df.sort_index().copy()
    if not isinstance(data.index, pd.DatetimeIndex):
        data.index = pd.to_datetime(data.index)
        
    obs_dt = pd.to_datetime(obs_date)
    # Filter to history up to obs_dt
    hist_data = data[data.index <= obs_dt].dropna(subset=["Close", "Volume"]).copy()
    
    if len(hist_data) < (baseline_window + window):
        return np.nan, np.nan, np.nan
        
    # Calculate rolling baseline: shift(1) excludes current day
    rolling_baseline = hist_data["Volume"].shift(1).rolling(window=baseline_window, min_periods=baseline_window).mean()
    event_mask = hist_data["Volume"] > (threshold_mult * rolling_baseline)
    
    # 1. Recency: search entire valid study history up to observation date
    qualifying_dates = hist_data.index[event_mask]
    if len(qualifying_dates) == 0:
        recency = np.nan
    else:
        latest_event_date = qualifying_dates[-1]
        recency = (obs_dt - latest_event_date).days
        
    # Slice latest 60 trading sessions ending on observation date
    latest_60 = hist_data.tail(window)
    if len(latest_60) < window:
        return np.nan, np.nan, np.nan
        
    # 2. Frequency: count within latest 60 trading sessions
    latest_60_events = event_mask.loc[latest_60.index]
    frequency = int(latest_60_events.sum())
    
    # 3. Monetary: sum of Close * Volume across latest 60 trading sessions
    monetary = float((latest_60["Close"] * latest_60["Volume"]).sum())
    
    return recency, frequency, monetary

def process_full_feature_pipeline():
    """
    Executes the entire Task 1 pipeline:
    - Scrapes Wikipedia constituents
    - Downloads/loads cached daily data
    - Filters and logs exclusions
    - Resamples and aligns weekly returns
    - Estimates weekly beta against ^GSPC
    - Computes adapted RFM features
    - Exports clean CSVs for Task 2 and the assignment report.
    """
    os.makedirs("data", exist_ok=True)
    os.makedirs("figures", exist_ok=True)
    
    print("--- 1.1 Ticker Selection and Data Acquisition ---")
    constituents = scrape_sp500_tickers()
    constituents.to_csv("data/sp500_constituents.csv", index=False)
    print(f"Acquired {len(constituents)} constituents from Wikipedia on {constituents['Retrieval_Date'].iloc[0]}.")
    
    tickers = constituents["Clean_Ticker"].tolist()
    raw_data = download_market_data(tickers)
    
    print("--- 1.2 Data Validation and Exclusion Logging ---")
    exclusion_records = []
    valid_tickers = []
    
    # Extract benchmark daily prices
    try:
        bmk_series = raw_data[BENCHMARK_TICKER]["Adj Close"].dropna()
    except KeyError:
        bmk_series = raw_data["Adj Close"][BENCHMARK_TICKER].dropna()
        
    bmk_weekly_ret = bmk_series.resample("W-FRI").last().pct_change(fill_method=None)
    
    # Build daily price, adj price, and volume containers
    adj_close_dict = {}
    rfm_dict = {}
    
    total_expected_days = len(bmk_series)
    min_required_days = int(0.80 * total_expected_days)
    
    for ticker in tickers:
        try:
            if isinstance(raw_data.columns, pd.MultiIndex):
                # multi-index columns: (Ticker, Field) or (Field, Ticker)
                if ticker in raw_data.columns.levels[0]:
                    t_df = raw_data[ticker].dropna(how="all")
                elif ticker in raw_data.columns.levels[1]:
                    t_df = raw_data.xs(ticker, axis=1, level=1).dropna(how="all")
                else:
                    exclusion_records.append({"Ticker": ticker, "Reason": "Missing from download response"})
                    continue
            else:
                exclusion_records.append({"Ticker": ticker, "Reason": "Unexpected raw data format"})
                continue
        except Exception as e:
            exclusion_records.append({"Ticker": ticker, "Reason": f"Data extraction error: {str(e)}"})
            continue
            
        if len(t_df) == 0:
            exclusion_records.append({"Ticker": ticker, "Reason": "Empty price history"})
            continue
            
        # Check coverage
        if len(t_df) < min_required_days:
            exclusion_records.append({
                "Ticker": ticker,
                "Reason": f"Insufficient trading history ({len(t_df)} days < {min_required_days} required 80% threshold)"
            })
            continue
            
        # Check nonpositive prices or zero volume
        if (t_df["Close"] <= 0).any() or (t_df["Adj Close"] <= 0).any():
            exclusion_records.append({"Ticker": ticker, "Reason": "Nonpositive price anomaly detected"})
            continue
            
        # Check RFM features
        r, f, m = compute_adapted_rfm_for_series(t_df[["Close", "Volume"]])
        if np.isnan(r):
            exclusion_records.append({"Ticker": ticker, "Reason": "No qualifying high-volume event found in study history"})
            continue
            
        if np.isnan(f) or np.isnan(m):
            exclusion_records.append({"Ticker": ticker, "Reason": "Insufficient history for 60-session RFM window"})
            continue
            
        adj_close_dict[ticker] = t_df["Adj Close"]
        rfm_dict[ticker] = {"Recency": r, "Frequency": f, "Monetary": m}
        valid_tickers.append(ticker)
        
    exclusion_df = pd.DataFrame(exclusion_records)
    exclusion_df.to_csv("data/exclusion_log.csv", index=False)
    print(f"Validated tickers: {len(valid_tickers)} retained, {len(exclusion_df)} excluded.")
    print("Exclusion summary:\n", exclusion_df["Reason"].value_counts())
    
    print("--- 1.3 Mean Weekly Return and Weekly Beta ---")
    prices_df = pd.DataFrame(adj_close_dict)
    weekly_returns = calculate_weekly_returns(prices_df)
    
    # Calculate weekly beta and mean weekly return
    beta_df = calculate_weekly_beta(weekly_returns, bmk_weekly_ret, min_weeks=52)
    
    print("--- 1.4 & 1.5 Compiling Feature Matrices ---")
    rfm_df = pd.DataFrame.from_dict(rfm_dict, orient="index")
    rfm_df.index.name = "Ticker"
    
    # Merge all features into master dataframe
    features_master = beta_df.join(rfm_df, how="inner")
    
    # Attach GICS Sector from Wikipedia constituents
    sector_map = constituents.set_index("Clean_Ticker")["GICS_Sector"].to_dict()
    company_map = constituents.set_index("Clean_Ticker")["Company"].to_dict()
    features_master["GICS_Sector"] = features_master.index.map(sector_map)
    features_master["Company"] = features_master.index.map(company_map)
    
    # Drop any remaining NaN across the required features
    features_master = features_master.dropna(subset=[
        "Mean_Weekly_Return", "Beta", "Recency", "Frequency", "Monetary"
    ]).copy()
    
    # Log-transformed Monetary
    features_master["log1p_Monetary"] = np.log1p(features_master["Monetary"])
    
    # Export full feature table
    features_master.to_csv("data/features_all.csv")
    print(f"Master features successfully compiled for {len(features_master)} common shares.")
    print(features_master.head())
    
    # Worked example for AAPL (or first available mega-cap)
    example_ticker = "AAPL" if "AAPL" in features_master.index else features_master.index[0]
    print(f"\nWorked Example for {example_ticker}:")
    print(features_master.loc[example_ticker])
    
    return features_master, exclusion_df

if __name__ == "__main__":
    process_full_feature_pipeline()
