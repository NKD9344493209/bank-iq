.PHONY: setup run test samples shots docker data train train-fast eda notebooks
setup: ; pip install -r requirements-dev.txt && python scripts/make_samples.py && python scripts/make_passbook_image.py
run: ; uvicorn api.main:app --reload --port 8000
test: ; python -m pytest -q
samples: ; python scripts/make_samples.py && python scripts/make_passbook_image.py
shots: ; python scripts/ui_walkthrough.py http://localhost:8000
docker: ; docker compose up --build
data: ; python -c "from bankiq.data.generator import load; load(regenerate=True)"
train: ; python -m bankiq.experiments.run_all
train-fast: ; python -m bankiq.experiments.run_all eda classification regression clustering
eda: ; python -m bankiq.experiments.eda
notebooks: ; jupyter nbconvert --to notebook --execute --inplace notebooks/*.ipynb
