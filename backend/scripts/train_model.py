import pandas as pd
import numpy as np
import pickle
import os

print("Generating synthetic data...")
np.random.seed(42)
n_samples = 1000
population = np.random.randint(1000, 100000, n_samples)
severity = np.random.uniform(10, 100, n_samples)
buildings = population * np.random.uniform(0.1, 0.4, n_samples)

food = population * (severity / 100) * 1.5
water = population * (severity / 100) * 2.5
medical = population * (severity / 100) * 0.2
shelter = buildings * (severity / 100) * 0.4

df = pd.DataFrame({
    'population': population,
    'severity': severity,
    'buildings': buildings,
    'food': food,
    'water': water,
    'medical': medical,
    'shelter': shelter
})

print("Training RandomForestRegressor...")
from sklearn.ensemble import RandomForestRegressor
X = df[['population', 'severity', 'buildings']]
models = {
    'food': RandomForestRegressor(n_estimators=10, max_depth=5).fit(X, df['food']),
    'water': RandomForestRegressor(n_estimators=10, max_depth=5).fit(X, df['water']),
    'medical': RandomForestRegressor(n_estimators=10, max_depth=5).fit(X, df['medical']),
    'shelter': RandomForestRegressor(n_estimators=10, max_depth=5).fit(X, df['shelter'])
}

os.makedirs('models_pkl', exist_ok=True)
with open('models_pkl/demand_model.pkl', 'wb') as f:
    pickle.dump(models, f)

print("Models saved successfully to models_pkl/demand_model.pkl")
