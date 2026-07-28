import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
import joblib

np.random.seed(42)

n = 400

# Simulate features with wider, more realistic spread
transaction_count = np.random.poisson(6, n)
avg_transaction = np.random.normal(18000, 10000, n).clip(500, None)
sacco_months = np.random.exponential(10, n).clip(0, 60)
sacco_contribution = np.random.normal(12000, 9000, n).clip(0, None)
trade_frequency = np.random.poisson(5, n)
trade_volume = np.random.normal(25000, 18000, n).clip(0, None)

# Standardize features before combining, so no single raw scale dominates
raw = np.column_stack([
    transaction_count, avg_transaction, sacco_months,
    sacco_contribution, trade_frequency, trade_volume
])
scaler_temp = StandardScaler()
raw_scaled = scaler_temp.fit_transform(raw)

weights = np.array([0.25, 0.10, 0.25, 0.10, 0.20, 0.10])
raw_score = raw_scaled @ weights

# More noise relative to signal = more realistic, less saturated separation
raw_score += np.random.normal(0, 0.8, n)

creditworthy = (raw_score > np.median(raw_score)).astype(int)

df = pd.DataFrame({
    "transaction_count": transaction_count,
    "avg_transaction": avg_transaction,
    "sacco_months": sacco_months,
    "sacco_contribution": sacco_contribution,
    "trade_frequency": trade_frequency,
    "trade_volume": trade_volume,
    "creditworthy": creditworthy
})

X = df.drop("creditworthy", axis=1)
y = df["creditworthy"]

# Scale features properly and keep the scaler for later use in the app
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter=1000, C=0.5)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("Accuracy:", accuracy_score(y_test, y_pred))
print("AUC-ROC:", roc_auc_score(y_test, y_prob))
print("\nFeature Importance (coefficients):")
for feature, coef in zip(X.columns, model.coef_[0]):
    print(f"  {feature}: {coef:.4f}")

joblib.dump(model, "finher_model.pkl")
joblib.dump(scaler, "finher_scaler.pkl")
print("\nModel and scaler saved")