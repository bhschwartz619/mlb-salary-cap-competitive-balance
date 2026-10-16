"""
Step 3: correlation matrix, heatmap, and both regressions.
"""
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # save plots without opening a window
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm

import config


def load_data(cols):
    """Load the merged file and drop rows missing any of the given columns."""
    df = pd.read_csv(config.MERGED_FILE)
    clean = df.dropna(subset=cols)
    dropped = len(df) - len(clean)
    if dropped:
        print(f"   Dropped {dropped} of {len(df)} rows with missing values in {cols}")
    return clean


# -----------------------------
# Correlation matrix + heatmap
# -----------------------------
def correlation_analysis():
    print("=== Correlation ===")
    df = load_data(config.CORRELATION_COLS)
    corr = df[config.CORRELATION_COLS].corr()

    corr.to_csv(config.CORRELATION_FILE)
    print(corr.round(2))
    print(f"Correlation matrix saved to: {config.CORRELATION_FILE}")

    plt.figure(figsize=(14, 10))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)
    plt.title("Correlation Heatmap: Positional WAR vs Wins", fontsize=16)
    plt.tight_layout()
    plt.savefig(config.HEATMAP_FILE, dpi=300)
    plt.close()
    print(f"Heatmap saved to: {config.HEATMAP_FILE}")


# -----------------------------
# Regressions
# -----------------------------
def run_regression(predictors, output_path, title):
    print(f"\n=== Regression: {title} ===")
    df = load_data(predictors + ["W"])

    X = sm.add_constant(df[predictors])
    y = df["W"]
    model = sm.OLS(y, X).fit()

    print(model.summary())
    with open(output_path, "w") as f:
        f.write(model.summary().as_text())
    print(f"Regression results saved to: {output_path}")
    return model


def main():
    correlation_analysis()
    run_regression(["TotalWAR"], config.REGRESSION_TOTAL_FILE, "Wins ~ TotalWAR")
    run_regression(config.REGRESSION_POS_COLS, config.REGRESSION_POS_FILE,
                   "Wins ~ positional WAR")


if __name__ == "__main__":
    main()
