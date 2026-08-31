import pickle, os
with open('models_pkl/demand_model.pkl', 'rb') as f:
    m = pickle.load(f)
print('Model keys:', list(m.keys()))
print('Type:', type(m))
