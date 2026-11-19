"""
Stock Segmentation and Sensitivity Analysis Module
Module: 6BUIS017W CRM & CM With Business Intelligence (University of Westminster)
Coursework Specification: Task 2

Implements:
1. Two separate standardized feature matrices:
   - Matrix 1: Risk & Return (Mean Weekly Return, Weekly Beta)
   - Matrix 2: Trading Activity (Recency, Frequency, log1p(Monetary))
2. Agglomerative Hierarchical Clustering (Ward linkage, Euclidean distance) with dendrograms.
3. K-Means Clustering with multiple initializations (n_init=30, random_state=42) and k=2..8 evaluation.
4. Cluster diagnostic profiles in original physical units and 2D visualizations.
5. Sensitivity Analysis:
   - 2.5.1 Correlation matrix among R, F, and log1p(M).
   - 2.5.2 Removal of Monetary: refit Ward on [R, F] alone, Adjusted Rand Index (ARI), and traded value analysis.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import linkage, dendrogram, cut_tree
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.decomposition import PCA

def prepare_matrices(features_df):
    """
    Constructs and standardizes the two separate feature matrices:
    Matrix 1: [Mean_Weekly_Return, Beta]
    Matrix 2: [Recency, Frequency, log1p_Monetary]
    """
    df = features_df.copy()
    
    # Check skewness
    skew_report = {
        "Mean_Weekly_Return": float(df["Mean_Weekly_Return"].skew()),
        "Beta": float(df["Beta"].skew()),
        "Recency": float(df["Recency"].skew()),
        "Frequency": float(df["Frequency"].skew()),
        "Raw_Monetary": float(df["Monetary"].skew()),
        "log1p_Monetary": float(df["log1p_Monetary"].skew()),
    }
    
    scaler_rr = StandardScaler()
    X_rr = scaler_rr.fit_transform(df[["Mean_Weekly_Return", "Beta"]])
    
    scaler_rfm = StandardScaler()
    X_rfm = scaler_rfm.fit_transform(df[["Recency", "Frequency", "log1p_Monetary"]])
    
    return X_rr, X_rfm, scaler_rr, scaler_rfm, skew_report

def fit_agglomerative_ward(X, k_range=range(2, 9), selected_k=3):
    """
    Fits Ward linkage agglomerative hierarchical clustering with Euclidean distance.
    Evaluates silhouette scores across k_range and cuts the tree at selected_k.
    """
    Z = linkage(X, method="ward", metric="euclidean")
    
    sil_scores = {}
    for k in k_range:
        labels = cut_tree(Z, n_clusters=k).ravel()
        sil_scores[k] = float(silhouette_score(X, labels))
        
    final_labels = cut_tree(Z, n_clusters=selected_k).ravel()
    return Z, final_labels, sil_scores

def fit_kmeans_models(X, k_range=range(2, 9), random_state=42, n_init=30):
    """
    Fits K-Means clustering across candidate cluster counts k in k_range.
    Uses multiple initializations and fixed seed for reproducibility.
    Returns dictionary of fitted models, inertias, and silhouette scores.
    """
    models = {}
    inertias = {}
    sil_scores = {}
    
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=n_init)
        labels = km.fit_predict(X)
        models[k] = km
        inertias[k] = float(km.inertia_)
        sil_scores[k] = float(silhouette_score(X, labels))
        
    return models, inertias, sil_scores

def plot_dendrogram(Z, labels, title, save_path, truncate_mode="lastp", p=30):
    """
    Plots and saves a publication-quality hierarchical clustering dendrogram.
    """
    plt.figure(figsize=(10, 5), dpi=300)
    plt.title(title, fontsize=12, fontweight="bold")
    plt.xlabel("Cluster Size / Leaf Groupings", fontsize=10)
    plt.ylabel("Ward Euclidean Distance", fontsize=10)
    dendrogram(
        Z,
        truncate_mode=truncate_mode,
        p=p,
        leaf_rotation=90,
        leaf_font_size=9,
        show_contracted=True
    )
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved dendrogram to {save_path}")

def plot_clustering_diagnostics(rr_inertias, rr_sils, rfm_inertias, rfm_sils, save_path):
    """
    Plots elbow inertia and silhouette scores across k=2..8 for both feature spaces.
    """
    ks = list(rr_inertias.keys())
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), dpi=300)
    
    # 1. Risk/Return Inertia
    axes[0, 0].plot(ks, [rr_inertias[k] for k in ks], marker="o", color="#1f77b4", lw=2)
    axes[0, 0].set_title("Risk & Return: K-Means Inertia (Elbow Curve)", fontsize=11, fontweight="bold")
    axes[0, 0].set_xlabel("Number of Clusters (k)")
    axes[0, 0].set_ylabel("Inertia (SSE)")
    axes[0, 0].grid(True, linestyle="--", alpha=0.5)
    
    # 2. Risk/Return Silhouette
    axes[0, 1].plot(ks, [rr_sils[k] for k in ks], marker="s", color="#2ca02c", lw=2)
    axes[0, 1].set_title("Risk & Return: K-Means Silhouette Scores", fontsize=11, fontweight="bold")
    axes[0, 1].set_xlabel("Number of Clusters (k)")
    axes[0, 1].set_ylabel("Silhouette Score")
    axes[0, 1].grid(True, linestyle="--", alpha=0.5)
    
    # 3. RFM Inertia
    axes[1, 0].plot(ks, [rfm_inertias[k] for k in ks], marker="o", color="#ff7f0e", lw=2)
    axes[1, 0].set_title("Adapted RFM: K-Means Inertia (Elbow Curve)", fontsize=11, fontweight="bold")
    axes[1, 0].set_xlabel("Number of Clusters (k)")
    axes[1, 0].set_ylabel("Inertia (SSE)")
    axes[1, 0].grid(True, linestyle="--", alpha=0.5)
    
    # 4. RFM Silhouette
    axes[1, 1].plot(ks, [rfm_sils[k] for k in ks], marker="s", color="#d62728", lw=2)
    axes[1, 1].set_title("Adapted RFM: K-Means Silhouette Scores", fontsize=11, fontweight="bold")
    axes[1, 1].set_xlabel("Number of Clusters (k)")
    axes[1, 1].set_ylabel("Silhouette Score")
    axes[1, 1].grid(True, linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved diagnostic plots to {save_path}")

def plot_2d_scatter(df, cluster_col, x_col, y_col, x_label, y_label, title, save_path):
    """
    Plots a labelled 2D scatter plot in original units.
    """
    plt.figure(figsize=(9, 6), dpi=300)
    palette = sns.color_palette("tab10", n_colors=df[cluster_col].nunique())
    
    sns.scatterplot(
        data=df,
        x=x_col,
        y=y_col,
        hue=cluster_col,
        palette=palette,
        alpha=0.85,
        s=60,
        edgecolor="k",
        linewidth=0.5
    )
    plt.title(title, fontsize=12, fontweight="bold")
    plt.xlabel(x_label, fontsize=10)
    plt.ylabel(y_label, fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="Cluster", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved scatter plot to {save_path}")

def plot_rfm_pca_scatter(df, cluster_col, X_rfm, title, save_path):
    """
    Projects 3D standardized RFM space onto 2 principal components for visualization.
    """
    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(X_rfm)
    var_exp = pca.explained_variance_ratio_ * 100
    
    plot_df = df.copy()
    plot_df["PC1"] = coords[:, 0]
    plot_df["PC2"] = coords[:, 1]
    
    plt.figure(figsize=(9, 6), dpi=300)
    palette = sns.color_palette("Set1", n_colors=plot_df[cluster_col].nunique())
    
    sns.scatterplot(
        data=plot_df,
        x="PC1",
        y="PC2",
        hue=cluster_col,
        palette=palette,
        alpha=0.85,
        s=60,
        edgecolor="k",
        linewidth=0.5
    )
    plt.title(f"{title} (PCA 2D Projection: {var_exp[0]:.1f}% + {var_exp[1]:.1f}% var)", fontsize=12, fontweight="bold")
    plt.xlabel(f"Principal Component 1 ({var_exp[0]:.1f}% variance)", fontsize=10)
    plt.ylabel(f"Principal Component 2 ({var_exp[1]:.1f}% variance)", fontsize=10)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="Cluster", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(save_path)
    plt.close()
    print(f"Saved RFM PCA scatter to {save_path}")

def compute_rfm_correlation(df):
    """
    Calculates Pearson and Spearman correlations among R, F, and log1p(M).
    """
    rfm_subset = df[["Recency", "Frequency", "log1p_Monetary"]].copy()
    pearson_corr = rfm_subset.corr(method="pearson")
    spearman_corr = rfm_subset.corr(method="spearman")
    
    return pearson_corr, spearman_corr

def run_monetary_ablation(df, selected_k=3):
    """
    Section 2.5.2 Removal of Monetary:
    1. Re-standardize using ONLY Recency and Frequency.
    2. Refit Ward hierarchical clustering with the same k on identical shares.
    3. Compute Adjusted Rand Index (ARI) against the 3-feature RFM Ward solution.
    4. Compare cluster traded value distributions.
    """
    scaler_rf = StandardScaler()
    X_rf = scaler_rf.fit_transform(df[["Recency", "Frequency"]])
    
    Z_rf = linkage(X_rf, method="ward", metric="euclidean")
    labels_rf = cut_tree(Z_rf, n_clusters=selected_k).ravel()
    
    ari = adjusted_rand_score(df["Ward_Cluster_RFM"], labels_rf)
    
    df_ablation = df.copy()
    df_ablation["Ward_Cluster_RF_Only"] = labels_rf
    
    # Traded value comparison by cluster
    tv_rfm = df_ablation.groupby("Ward_Cluster_RFM")["Monetary"].agg(["mean", "median", "std", "count"])
    tv_rf = df_ablation.groupby("Ward_Cluster_RF_Only")["Monetary"].agg(["mean", "median", "std", "count"])
    
    # Save boxplot of monetary distribution across the two clusterings
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), dpi=300)
    sns.boxplot(ax=axes[0], data=df_ablation, x="Ward_Cluster_RFM", y="log1p_Monetary", palette="Pastel1")
    axes[0].set_title("Traded Value: 3-Feature RFM Ward Clusters", fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Cluster ID")
    axes[0].set_ylabel("log1p(Monetary in USD)")
    axes[0].grid(True, linestyle="--", alpha=0.5)
    
    sns.boxplot(ax=axes[1], data=df_ablation, x="Ward_Cluster_RF_Only", y="log1p_Monetary", palette="Pastel2")
    axes[1].set_title("Traded Value: 2-Feature RF-Only Ward Clusters", fontsize=11, fontweight="bold")
    axes[1].set_xlabel("Cluster ID")
    axes[1].set_ylabel("log1p(Monetary in USD)")
    axes[1].grid(True, linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    plt.savefig("figures/monetary_ablation_distribution.png")
    plt.close()
    print("Saved monetary ablation distribution plot to figures/monetary_ablation_distribution.png")
    
    return ari, labels_rf, tv_rfm, tv_rf

def execute_task2_pipeline():
    """
    Executes all Task 2 workflows and writes summary tables and plots.
    """
    os.makedirs("figures", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    print("Loading features_all.csv...")
    df = pd.read_csv("data/features_all.csv", index_col="Ticker")
    
    print("\n--- 2.1 Feature Preparation & Skewness Analysis ---")
    X_rr, X_rfm, scaler_rr, scaler_rfm, skew_report = prepare_matrices(df)
    print("Feature Skewness Diagnostics:")
    for k, v in skew_report.items():
        print(f"  {k:20s}: {v:8.4f}")
        
    print("\n--- 2.2 Agglomerative Hierarchical Clustering (Ward Linkage) ---")
    # Evaluate k=2..8
    k_range = list(range(2, 9))
    Z_rr, ward_labels_rr, ward_sils_rr = fit_agglomerative_ward(X_rr, k_range=k_range, selected_k=3)
    Z_rfm, ward_labels_rfm, ward_sils_rfm = fit_agglomerative_ward(X_rfm, k_range=k_range, selected_k=3)
    
    plot_dendrogram(Z_rr, df.index, "Ward Dendrogram: S&P 500 Risk & Return (Mean Return & Beta)", "figures/dendrogram_risk_return.png")
    plot_dendrogram(Z_rfm, df.index, "Ward Dendrogram: S&P 500 Adapted RFM Trading Activity", "figures/dendrogram_rfm.png")
    
    print("Ward Silhouette Scores across k=2..8:")
    for k in k_range:
        print(f"  k={k}: Risk/Return = {ward_sils_rr[k]:.4f} | RFM = {ward_sils_rfm[k]:.4f}")
        
    print("\n--- 2.3 K-Means Clustering ---")
    km_models_rr, km_inertias_rr, km_sils_rr = fit_kmeans_models(X_rr, k_range=k_range, random_state=42, n_init=30)
    km_models_rfm, km_inertias_rfm, km_sils_rfm = fit_kmeans_models(X_rfm, k_range=k_range, random_state=42, n_init=30)
    
    plot_clustering_diagnostics(km_inertias_rr, km_sils_rr, km_inertias_rfm, km_sils_rfm, "figures/cluster_diagnostics.png")
    
    print("K-Means Silhouette Scores across k=2..8:")
    for k in k_range:
        print(f"  k={k}: Risk/Return = {km_sils_rr[k]:.4f} (Inertia: {km_inertias_rr[k]:.1f}) | RFM = {km_sils_rfm[k]:.4f} (Inertia: {km_inertias_rfm[k]:.1f})")
        
    # Select k=3 for both as optimal trade-off of silhouette, elbow, and financial interpretability
    chosen_k_rr = 3
    chosen_k_rfm = 3
    
    df["Ward_Cluster_RR"] = cut_tree(Z_rr, n_clusters=chosen_k_rr).ravel()
    df["KMeans_Cluster_RR"] = km_models_rr[chosen_k_rr].labels_
    df["Ward_Cluster_RFM"] = cut_tree(Z_rfm, n_clusters=chosen_k_rfm).ravel()
    df["KMeans_Cluster_RFM"] = km_models_rfm[chosen_k_rfm].labels_
    
    print("\n--- 2.4 Cluster Profiles in Original Units ---")
    rr_profile = df.groupby("Ward_Cluster_RR").agg({
        "Mean_Weekly_Return": ["mean", "std"],
        "Beta": ["mean", "std"],
        "Company": "count"
    })
    rr_profile.columns = ["Return_Mean", "Return_Std", "Beta_Mean", "Beta_Std", "Share_Count"]
    
    rfm_profile = df.groupby("Ward_Cluster_RFM").agg({
        "Recency": ["mean", "std"],
        "Frequency": ["mean", "std"],
        "Monetary": ["mean", "std"],
        "Company": "count"
    })
    rfm_profile.columns = ["Recency_Days_Mean", "Recency_Days_Std", "Frequency_Mean", "Frequency_Std", "Traded_Value_USD_Mean", "Traded_Value_USD_Std", "Share_Count"]
    
    print("\nRisk/Return Ward Cluster Profiles (Original Units):")
    print(rr_profile)
    print("\nAdapted RFM Ward Cluster Profiles (Original Units):")
    print(rfm_profile)
    
    # Save profiles
    rr_profile.to_csv("data/profile_risk_return.csv")
    rfm_profile.to_csv("data/profile_rfm.csv")
    
    # Visualizations
    plot_2d_scatter(
        df,
        cluster_col="Ward_Cluster_RR",
        x_col="Beta",
        y_col="Mean_Weekly_Return",
        x_label="Weekly Beta (vs. ^GSPC)",
        y_label="Mean Weekly Return (Decimal)",
        title="S&P 500 Risk & Return Clusters (Ward Linkage, k=3)",
        save_path="figures/scatter_risk_return.png"
    )
    
    plot_rfm_pca_scatter(
        df,
        cluster_col="Ward_Cluster_RFM",
        X_rfm=X_rfm,
        title="S&P 500 Adapted RFM Trading Clusters (Ward Linkage, k=3)",
        save_path="figures/scatter_rfm.png"
    )
    
    # Cross-algorithm agreement on same shares
    ari_rr = adjusted_rand_score(df["Ward_Cluster_RR"], df["KMeans_Cluster_RR"])
    ari_rfm = adjusted_rand_score(df["Ward_Cluster_RFM"], df["KMeans_Cluster_RFM"])
    print(f"\nCross-Algorithm Agreement (Adjusted Rand Index):")
    print(f"  Risk/Return (Ward vs. K-Means): ARI = {ari_rr:.4f}")
    print(f"  Adapted RFM (Ward vs. K-Means): ARI = {ari_rfm:.4f}")
    
    print("\n--- 2.5 RFM Sensitivity and Correlated Inputs ---")
    p_corr, s_corr = compute_rfm_correlation(df)
    print("Pearson Correlation (R, F, log1p_M):")
    print(p_corr)
    print("\nSpearman Rank Correlation (R, F, log1p_M):")
    print(s_corr)
    
    p_corr.to_csv("data/rfm_correlation_pearson.csv")
    s_corr.to_csv("data/rfm_correlation_spearman.csv")
    
    # 2.5.2 Monetary Removal Ablation
    ari_ablation, labels_rf, tv_rfm, tv_rf = run_monetary_ablation(df, selected_k=chosen_k_rfm)
    df["Ward_Cluster_RF_Only"] = labels_rf
    
    print(f"\nMonetary Removal Ablation:")
    print(f"  Adjusted Rand Index between 3-feature RFM and 2-feature RF: ARI = {ari_ablation:.4f}")
    print("\nTraded Value (Monetary in USD) by 3-Feature RFM Cluster:")
    print(tv_rfm)
    print("\nTraded Value (Monetary in USD) by 2-Feature RF-Only Cluster:")
    print(tv_rf)
    
    ablation_summary = pd.DataFrame([{
        "Comparison": "RFM (3-feature) vs RF (2-feature)",
        "Adjusted_Rand_Index": ari_ablation,
        "Selected_k": chosen_k_rfm,
        "Total_Shares": len(df)
    }])
    ablation_summary.to_csv("data/monetary_ablation_ari.csv", index=False)
    
    # Export full cluster assignments
    df.to_csv("data/cluster_assignments.csv")
    print(f"\nExported complete cluster assignments to data/cluster_assignments.csv ({len(df)} shares).")
    
    return df, skew_report, ari_ablation

if __name__ == "__main__":
    execute_task2_pipeline()
