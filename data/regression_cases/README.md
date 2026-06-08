# Regression Cases

Put exactly 8 real product-on-model images in `data/regression_cases/default/`.

Run:

```powershell
python scripts\run_regression_batch.py
```

The script creates a fixed batch under `data/batches/regression_<timestamp>/`.
Use the same 8 images after every matting, lighting, background, or model-edit change.
