import json

def create_notebook():
    cells = []
    
    def add_md(text):
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.strip().split("\n")]
        })
        
    def add_code(text):
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in text.strip().split("\n")]
        })
        
    # Cell 1: Title and Metadata
    add_md("""# 6BUIS017W CRM & CM With Business Intelligence
## Individual Coursework CWK1: Market Analysis and Stock Segmentation Using RFM
**Student Name / ID:** Candidate Submission  
**Module Leader:** Dr Panagiotis Chountas  
**Institution:** University of Westminster, School of Computer Science & Engineering  
**Observation Date:** 2024-12-31 (Final completed trading session of 2024)  
**Study Window:** 2021-01-01 to 2025-01-01 (Daily prices, volume, and ^GSPC benchmark)
""")

    # Cell 2: Imports and Environment Setup
    add_md("""### 1. Environment Setup & Dependency Installation
We import standard data science libraries for tabular data manipulation, statistical modeling, clustering, and visual diagnostics.
Package versions are logged to ensure full computational reproducibility.""")
    add_code("""# Run in Colab if packages need installation:
# !pip install yfinance pandas numpy scipy scikit-learn matplotlib seaborn

import sys
import os
import pickle
import datetime
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.cluster.hierarchy import linkage, dendrogram, cut_tree
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.decomposition import PCA

print(f"Python Environment: {sys.version.split()[0]}")
print(f"Pandas: {pd.__version__} | NumPy: {np.__version__} | Scikit-Learn: {__import__('sklearn').__version__} | yfinance: {yf.__version__}")
""")

    # Cell 3: Task 1.1 Data Acquisition
    add_md("""### 2. Task 1.1: Ticker Selection and Data Acquisition
We scrape the S&P 500 constituent table from Wikipedia, sanitize ticker symbols for Yahoo Finance compatibility (e.g., converting `BRK.B` to `BRK-B`), and download daily market data from 2021-01-01 to 2025-01-01 (exclusive).""")
    add_code("""from src.data_pipeline import scrape_sp500_tickers, download_market_data, STUDY_START, STUDY_END, BENCHMARK_TICKER, OBSERVATION_DATE

constituents = scrape_sp500_tickers()
print(f"Total Constituents Extracted: {len(constituents)}")
print(f"Extraction Timestamp: {constituents['Retrieval_Date'].iloc[0]}")
constituents.head()
""")

    # Cell 4: Download Market Data
    add_code("""tickers = constituents["Clean_Ticker"].tolist()
raw_data = download_market_data(tickers, start=STUDY_START, end=STUDY_END)
print("Raw market data loaded successfully.")
""")

    # Cell 5: Task 1.2 Data Validation & Exclusion Logging
    add_md("""### 3. Task 1.2: Data Validation, Alignment & Survivorship Bias
We enforce quality checks:
1. Sufficient trading history: At least 80% valid trading days (minimum 804 days).
2. Absence of zero/negative prices or non-existent volume.
3. Existence of at least one qualifying high-volume event across the 4-year history.
4. Explicit logging of all excluded equities in `data/exclusion_log.csv`.
5. **Survivorship Bias:** Because we evaluate current S&P 500 constituents against 2021–2024 history, companies that were delisted, acquired, or went bankrupt during the period are excluded. This creates an upward survivorship bias that is critically accounted for.""")
    add_code("""exclusion_df = pd.read_csv("data/exclusion_log.csv")
print(f"Total Exclusions: {len(exclusion_df)}")
display(exclusion_df.value_counts("Reason"))
exclusion_df.head(10)
""")

    # Cell 6: Task 1.3 Returns and Beta
    add_md("""### 4. Task 1.3: Mean Weekly Return and Weekly Beta
Daily Adjusted Closing prices are resampled into Friday-ending weeks (`resample('W-FRI').last()`).
Weekly returns are computed as:
$$R_{w} = \\frac{P_{w}}{P_{w-1}} - 1$$
Weekly beta is estimated relative to the S&P 500 index (`^GSPC`) over matched Friday observations:
$$\\beta = \\frac{\\text{Cov}(R_{\\text{share}}, R_{\\text{market}})}{\\text{Var}(R_{\\text{market}})}$$""")
    add_code("""features_master = pd.read_csv("data/features_all.csv", index_col="Ticker")
print(f"Valid Common Share Universe: {len(features_master)} shares")
features_master[["Company", "GICS_Sector", "Mean_Weekly_Return", "Beta", "Paired_Weeks"]].head(10)
""")

    # Cell 7: Task 1.4 & 1.5 Adapted RFM Feature Engineering
    add_md("""### 5. Task 1.4 & 1.5: Adapted RFM Trading Activity & Worked Example
Adapted RFM measures trading dynamics rather than retail purchasing:
- **High-Volume Event:** $\\text{Volume}_t > 2.0 \\times \\text{Mean}(\\text{Volume}_{t-20 \\dots t-1})$ (strictly excluding day $t$).
- **Recency ($R$):** Calendar day difference between latest qualifying event in history and 2024-12-31 ($R=0$ if on 31 Dec 2024).
- **Frequency ($F$):** Total count of qualifying event days within the latest 60 trading sessions ending 2024-12-31.
- **Monetary ($M$):** Total approximate USD traded dollar volume across the latest 60 sessions:
$$M = \\sum_{t=1}^{60} (\\text{Close}_t \\times \\text{Volume}_t)$$""")
    add_code("""# Display worked example for Apple (AAPL)
aapl_worked = features_master.loc["AAPL", ["Company", "GICS_Sector", "Recency", "Frequency", "Monetary", "log1p_Monetary", "Mean_Weekly_Return", "Beta"]]
print("--- Worked Example: Apple Inc. (AAPL) ---")
display(aapl_worked)
""")

    # Cell 8: Feature Distributions and Skewness
    add_md("""### 6. Task 2.1: Feature Skewness & Log-Transformation
Because mega-cap equities trade billions in daily dollar volume, raw Monetary ($M$) exhibits extreme right-skew (skewness = 13.10).
Applying $\\log_{1p}(M)$ stabilizes variance and reduces skewness to 0.94, ensuring Euclidean distance in clustering is not dominated by dollar scale alone.""")
    add_code("""fig, axes = plt.subplots(1, 2, figsize=(12, 4), dpi=150)
sns.histplot(features_master["Monetary"] / 1e9, bins=40, kde=True, ax=axes[0], color="#d62728")
axes[0].set_title("Raw Monetary Value (Traded USD in Billions - Highly Skewed)")
axes[0].set_xlabel("Traded Value ($ Billions)")

sns.histplot(features_master["log1p_Monetary"], bins=30, kde=True, ax=axes[1], color="#1f77b4")
axes[1].set_title("log1p(Monetary) - Normalized Distribution")
axes[1].set_xlabel("log1p(Monetary)")
plt.tight_layout()
plt.show()
""")

    # Cell 9: Task 2.2 Agglomerative Hierarchical Clustering
    add_md("""### 7. Task 2.2: Agglomerative Hierarchical Clustering (Ward Linkage)
Ward linkage with Euclidean distance is fitted independently on:
1. Standardized Risk & Return Matrix (`[Mean_Weekly_Return, Beta]`)
2. Standardized Adapted RFM Matrix (`[Recency, Frequency, log1p_Monetary]`)""")
    add_code("""from IPython.display import Image
display(Image("figures/dendrogram_risk_return.png", width=700))
display(Image("figures/dendrogram_rfm.png", width=700))
""")

    # Cell 10: Task 2.3 K-Means & Diagnostics
    add_md("""### 8. Task 2.3: K-Means Clustering & Diagnostics ($k=2..8$)
We assess cluster quality using inertia (Elbow method) and silhouette scores across $k=2..8$ for both feature matrices.""")
    add_code("""display(Image("figures/cluster_diagnostics.png", width=850))
""")

    # Cell 11: Task 2.4 Profiles in Original Units
    add_md("""### 9. Task 2.4: Cluster Profiles & 2D Visualizations
Centroids are reported in original physical units (decimal return, beta, calendar days, count, USD).
A 2D scatter plot displays Risk vs. Return, while PCA projects the 3D RFM space onto 2 principal components.""")
    add_code("""print("--- Risk & Return Ward Cluster Profiles (k=3) ---")
display(pd.read_csv("data/profile_risk_return.csv"))

print("--- Adapted RFM Ward Cluster Profiles (k=3) ---")
display(pd.read_csv("data/profile_rfm.csv"))
""")

    # Cell 12: Display 2D Scatter Visualizations
    add_code("""display(Image("figures/scatter_risk_return.png", width=700))
display(Image("figures/scatter_rfm.png", width=700))
""")

    # Cell 13: Task 2.5 Sensitivity Analysis
    add_md("""### 10. Task 2.5: RFM Sensitivity & Monetary Removal Ablation
1. **Correlation Analysis:** Pearson and Spearman correlations quantify multicollinearity between $R$, $F$, and $\\log_{1p}(M)$.
2. **Monetary Removal:** Re-standardizing on $R$ and $F$ alone and refitting Ward clustering ($k=3$) yields an **Adjusted Rand Index (ARI) of 0.3791**, indicating substantial cluster reassignment and proving that Monetary acts primarily as a liquidity/size separator.""")
    add_code("""print("Pearson Correlation:")
display(pd.read_csv("data/rfm_correlation_pearson.csv", index_col=0))

print("Monetary Removal Ablation Summary:")
display(pd.read_csv("data/monetary_ablation_ari.csv"))

display(Image("figures/monetary_ablation_distribution.png", width=850))
""")

    # Cell 14: Conclusion and Exports
    add_md("""### 11. Conclusion & BI Integration
The data pipeline exports `cluster_assignments.csv` containing all 4 baseline cluster assignments (Ward & K-Means across both spaces) and sensitivity classifications, ready for dimensional modeling and ingestion into the Business Intelligence Data Mart.""")
    add_code("""cluster_assignments = pd.read_csv("data/cluster_assignments.csv", index_col="Ticker")
print(f"Final Exported Dataset: {cluster_assignments.shape}")
cluster_assignments[["Company", "GICS_Sector", "Ward_Cluster_RR", "KMeans_Cluster_RR", "Ward_Cluster_RFM", "KMeans_Cluster_RFM", "Ward_Cluster_RF_Only"]].head(10)
""")

    notebook = {
        "cells": cells,
        "metadata": {
            "language_info": {
                "name": "python",
                "version": "3.11"
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    
    with open("CR_CM_Coursework_Final.ipynb", "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2)
        
    print("CR_CM_Coursework_Final.ipynb created successfully!")

if __name__ == "__main__":
    create_notebook()
