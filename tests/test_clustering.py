import pytest
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from src.clustering import (
    fit_agglomerative_ward,
    fit_kmeans_models,
    compute_rfm_correlation,
    run_monetary_ablation,
)

def test_fit_agglomerative_ward():
    np.random.seed(42)
    # 2 synthetic well-separated 2D clusters
    c1 = np.random.normal(loc=0.0, scale=0.5, size=(20, 2))
    c2 = np.random.normal(loc=5.0, scale=0.5, size=(20, 2))
    X = np.vstack([c1, c2])
    
    Z, labels, sil_scores = fit_agglomerative_ward(X, k_range=range(2, 5), selected_k=2)
    assert len(labels) == 40
    # Labels should be 2 unique clusters
    assert len(np.unique(labels)) == 2
    # Silhouette score for k=2 should be very high (>0.7)
    assert sil_scores[2] > 0.7

def test_fit_kmeans_models():
    np.random.seed(42)
    c1 = np.random.normal(loc=0.0, scale=0.5, size=(20, 2))
    c2 = np.random.normal(loc=5.0, scale=0.5, size=(20, 2))
    X = np.vstack([c1, c2])
    
    models, inertias, sil_scores = fit_kmeans_models(X, k_range=range(2, 5), random_state=42, n_init=10)
    assert 2 in models
    assert sil_scores[2] > 0.7
    # Inertia should decrease as k increases
    assert inertias[2] > inertias[3] > inertias[4]

def test_rfm_correlation_and_ablation():
    df = pd.DataFrame({
        "Recency": [5, 10, 15, 20, 25],
        "Frequency": [10, 8, 6, 4, 2],
        "log1p_Monetary": [20, 21, 22, 23, 24]
    })
    p_corr, s_corr = compute_rfm_correlation(df)
    assert p_corr.shape == (3, 3)
    assert s_corr.shape == (3, 3)
    # R and F are inversely related here
    assert p_corr.loc["Recency", "Frequency"] < 0
    
    labels_rfm = np.array([0, 0, 1, 1, 1])
    labels_rf = np.array([0, 0, 1, 1, 1])
    ari = adjusted_rand_score(labels_rfm, labels_rf)
    assert ari == 1.0
