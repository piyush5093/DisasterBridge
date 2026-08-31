import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import json
import os

df = pd.read_csv('data/synth_data.csv')
features_v1 = ['severity_score', 'population_exposed', 'buildings_affected']
# Feature engineering for v2
df['pop_per_bldg'] = df['population_exposed'] / (df['buildings_affected'] + 1)
df['severity_sq'] = df['severity_score'] ** 2
features_v2 = features_v1 + ['pop_per_bldg', 'severity_sq']

def train(version, features):
    models = {}
    metrics = {}
    for target in ['demand_food', 'demand_water', 'demand_medical', 'demand_shelter']:
        rf = RandomForestRegressor(n_estimators=50 if version=='v1' else 100, random_state=42)
        rf.fit(df[features], df[target])
        preds = rf.predict(df[features])
        metrics[target] = {
            "mae": mean_absolute_error(df[target], preds),
            "rmse": mean_squared_error(df[target], preds)**0.5
        }
        models[target] = rf
    
    os.makedirs(f'models_{version}', exist_ok=True)
    joblib.dump(models, f'models_{version}/demand_model.pkl')
    with open(f'models_{version}/metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved {version}")

train('v1', features_v1)
train('v2', features_v2)
