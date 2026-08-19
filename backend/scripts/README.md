# Scripts

## `create_dataset_users.py`

Adds synthetic `name`, `email`, and `password` columns to
`data/library_combined_dataset.csv`.

## `import_dataset.py`

Imports the combined dataset into Neon:

```bash
# from backend/
python scripts/import_dataset.py
```

Mapping:

- `user_id` → `users.roll_number`
- `isbn10` → `books.isbn10` (primary key)
- ratings keep `rating = 0` rows as stored in the CSV
