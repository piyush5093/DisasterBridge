import pandas as pd
import numpy as np
import os

def generate_csv():
    np.random.seed(42)
    n = 1000
    df = pd.DataFrame({
        'severity_score': np.random.uniform(10, 100, n),
        'population_exposed': np.random.randint(100, 100000, n),
        'buildings_affected': np.random.randint(10, 5000, n),
        'demand_food': 0.0, 'demand_water': 0.0, 'demand_medical': 0.0, 'demand_shelter': 0.0
    })
    
    # Baseline relations
    df['demand_food'] = df['population_exposed'] * (df['severity_score'] / 100) * 1.5
    df['demand_water'] = df['population_exposed'] * (df['severity_score'] / 100) * 2.0
    df['demand_medical'] = df['buildings_affected'] * (df['severity_score'] / 100) * 0.5
    df['demand_shelter'] = df['buildings_affected'] * (df['severity_score'] / 100) * 0.2
    
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/synth_data.csv', index=False)
    print("Generated data/synth_data.csv")

if __name__ == '__main__':
    generate_csv()
