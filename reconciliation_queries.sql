-- ============================================================
-- Transaction Reconciliation & Discrepancy Detection — SQL
-- Dataset: PaySim (load transactions.csv into a table named `transactions`)
-- ============================================================

-- 1. Flag originator-side balance breaks
--    Expected: oldbalanceOrg - amount = newbalanceOrig
SELECT
    step,
    type,
    nameOrig,
    amount,
    oldbalanceOrg,
    newbalanceOrig,
    ROUND(oldbalanceOrg - amount, 2) AS expected_new_orig,
    ROUND(newbalanceOrig - (oldbalanceOrg - amount), 2) AS orig_diff
FROM transactions
WHERE ABS(newbalanceOrig - (oldbalanceOrg - amount)) > 0.01;

-- 2. Flag destination-side balance breaks (excluding merchant accounts,
--    which PaySim doesn't track balances for — those start with 'M')
SELECT
    step,
    type,
    nameDest,
    amount,
    oldbalanceDest,
    newbalanceDest,
    ROUND(oldbalanceDest + amount, 2) AS expected_new_dest,
    ROUND(newbalanceDest - (oldbalanceDest + amount), 2) AS dest_diff
FROM transactions
WHERE nameDest NOT LIKE 'M%'
  AND ABS(newbalanceDest - (oldbalanceDest + amount)) > 0.01;

-- 3. Summary: % of transactions that reconcile cleanly vs. break, by type
SELECT
    type,
    COUNT(*) AS total_transactions,
    SUM(CASE
        WHEN ABS(newbalanceOrig - (oldbalanceOrg - amount)) <= 0.01
        THEN 1 ELSE 0
    END) AS clean_count,
    SUM(CASE
        WHEN ABS(newbalanceOrig - (oldbalanceOrg - amount)) > 0.01
        THEN 1 ELSE 0
    END) AS break_count,
    ROUND(100.0 * SUM(CASE
        WHEN ABS(newbalanceOrig - (oldbalanceOrg - amount)) > 0.01
        THEN 1 ELSE 0
    END) / COUNT(*), 2) AS break_pct
FROM transactions
GROUP BY type
ORDER BY break_pct DESC;

-- 4. Cross-check against known fraud flags — do flagged-fraud transactions
--    also show up as reconciliation breaks? (Interesting finding for your
--    write-up: are Ops-style breaks a useful early signal for fraud?)
SELECT
    isFlaggedFraud,
    isFraud,
    COUNT(*) AS total,
    SUM(CASE
        WHEN ABS(newbalanceOrig - (oldbalanceOrg - amount)) > 0.01
        THEN 1 ELSE 0
    END) AS also_break
FROM transactions
GROUP BY isFlaggedFraud, isFraud;
