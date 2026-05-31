# Add custom query files here

Create any `.txt` file in this folder, for example:

```text
my_custom_query.txt
```

Then run:

```bash
PYTHONPATH=src python scripts/query_document.py --db outputs/legal_lsh.sqlite --threshold 0.30
```

The User Interaction Centre will automatically display the exact `.txt` file name.

Optional: put a friendly title in the first lines of the `.txt` file:

```text
Query Name: My Custom Bail Query

The petitioner seeks post-arrest bail under section 497 Cr.P.C...
```
