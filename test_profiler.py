#!/usr/bin/env python
import sys
sys.path.insert(0, "D:/Python/polaryix/apps/api")

from app.data_processing.readers import read_dataset
from app.data_processing.profiling.dataset_profiler import profile_dataframe
import json

file_path = "D:/Python/polaryix/apps/api/storage/quarantine/4d191d20874c42918eab264624283b04.csv"

try:
    df = read_dataset(path=file_path, extension=".csv")
    print("DataFrame shape:", df.shape)
    print("\nDataFrame head:\n", df.head())
    
    profile = profile_dataframe(df)
    print("\nProfile keys:", list(profile.keys()))
    print("\nFull Profile:")
    print(json.dumps(profile, indent=2, ensure_ascii=False, default=str))
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
