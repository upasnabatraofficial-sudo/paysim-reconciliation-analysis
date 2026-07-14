"""
Transaction Reconciliation & Discrepancy Detection
----------------------------------------------------
Dataset: PaySim Financial Fraud Detection Dataset (Kaggle)
Source: https://www.kaggle.com/datasets/sriharshaeedala/financial-fraud-detection-dataset
(Search "PaySim" on Kaggle if that link changes — several mirrors exist.)

Goal: Simulate an Operations-style reconciliation check — verify that each
transaction's before/after balances tie out correctly, flag and categorize
breaks, and summarize findings in a format suitable for an Excel/Power BI
dashboard.

HOW TO RUN:
1. Download the dataset CSV from Kaggle (free account required) and place
   it in this same folder as "transactions.csv"
2. pip install pandas numpy --break-system-packages   (if not already installed)
3. python reconciliation_analysis.py
"""

import pandas as pd
import numpy as np

# ----------------------------------------------------------------------
# 1. LOAD DATA
# ----------------------------------------------------------------------
df = pd.read_csv("transactions.csv")

# Expected columns from PaySim: step, type, amount, nameOrig, oldbalanceOrg,
# newbalanceOrig, nameDest, oldbalanceDest, newbalanceDest, isFraud, isFlaggedFraud
print(f"Loaded {len(df):,} transactions.")
print(df.head())

# ----------------------------------------------------------------------
# 2. RECONCILIATION CHECK — ORIGINATOR SIDE
#    Expected: oldbalanceOrg - amount = newbalanceOrig
# ----------------------------------------------------------------------
df["expected_new_orig"] = df["oldbalanceOrg"] - df["amount"]
df["orig_diff"] = (df["newbalanceOrig"] - df["expected_new_orig"]).round(2)
df["orig_break"] = df["orig_diff"].abs() > 0.01   # tolerance for float rounding

# ----------------------------------------------------------------------
# 3. RECONCILIATION CHECK — DESTINATION SIDE
#    Expected: oldbalanceDest + amount = newbalanceDest
#    (Skip merchant accounts, which start with 'M' — PaySim doesn't track
#    their balances, so this isn't a real break, just missing data.)
# ----------------------------------------------------------------------
is_merchant_dest = df["nameDest"].str.startswith("M")
df["expected_new_dest"] = df["oldbalanceDest"] + df["amount"]
df["dest_diff"] = (df["newbalanceDest"] - df["expected_new_dest"]).round(2)
df["dest_break"] = (df["dest_diff"].abs() > 0.01) & (~is_merchant_dest)

# ----------------------------------------------------------------------
# 4. CATEGORIZE BREAK TYPE
#    This mirrors how an Ops analyst would triage discrepancies:
#    - Clean: reconciles exactly
#    - Zero-balance break: account had 0 before and after (common with
#      merchant/edge accounts — usually a data-quality issue, not a real break)
#    - Genuine break: real mismatch worth investigating
# ----------------------------------------------------------------------
def classify(row):
    if not row["orig_break"] and not row["dest_break"]:
        return "Clean — Reconciled"
    if row["oldbalanceOrg"] == 0 and row["newbalanceOrig"] == 0:
        return "Zero-Balance Break (likely data quality)"
    if row["isFlaggedFraud"] == 1:
        return "Flagged Fraud — Large Transfer"
    return "Genuine Break — Needs Investigation"

df["break_category"] = df.apply(classify, axis=1)

# ----------------------------------------------------------------------
# 5. SUMMARY STATS (this is your dashboard's source data)
# ----------------------------------------------------------------------
summary = df["break_category"].value_counts(normalize=True).mul(100).round(2)
print("\n--- Reconciliation Summary (% of transactions) ---")
print(summary)

by_type = df.groupby(["type", "break_category"]).size().unstack(fill_value=0)
print("\n--- Breaks by Transaction Type ---")
print(by_type)

# ----------------------------------------------------------------------
# 6. EXPORT FLAGGED TRANSACTIONS FOR EXCEL DASHBOARD / ROOT-CAUSE SAMPLE
# ----------------------------------------------------------------------
flagged = df[df["break_category"] == "Genuine Break — Needs Investigation"]
flagged.to_csv("flagged_transactions.csv", index=False)
print(f"\nExported {len(flagged):,} genuine breaks to flagged_transactions.csv")

# Also export a clean summary table for your dashboard
summary_df = df["break_category"].value_counts().reset_index()
summary_df.columns = ["Break Category", "Count"]
summary_df.to_csv("reconciliation_summary.csv", index=False)
print("Exported reconciliation_summary.csv for Excel/Power BI dashboard.")
