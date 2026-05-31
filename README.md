# Run steps only

```bash
cd legal_similarity_system
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run these one-time stages in order:

```bash
python scripts/corpus_status.py
PYTHONPATH=src python scripts/process_corpus.py
PYTHONPATH=src python scripts/make_shingles.py
PYTHONPATH=src python scripts/build_minhash.py
```

Then run the main user interaction centre:

```bash
PYTHONPATH=src python main.py
```

Add your own sample query:

```text
data/sample_queries/my_query.txt
```

Run again:

```bash
PYTHONPATH=src python main.py
```

Optional direct selection without typing:

```bash
PYTHONPATH=src python main.py --sample-index 1 --threshold 0.30
```

Output folders made by the one-time stages:

```text
outputs/processed/processed_docs.jsonl
outputs/shingles/shingles.jsonl
outputs/legal_lsh.sqlite
```
