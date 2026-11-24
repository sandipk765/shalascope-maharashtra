# ShalaScope – How to use this validated mapping review pack

1. Extract the ZIP into `docs/column_mapping/validated_review/` (keep the existing Draft files unchanged).
2. Copy `src/validation/profile_key_values.py` into your project at `src/validation/profile_key_values.py`.
3. From the project root, run:

   `python src/validation/profile_key_values.py`

4. The script creates:
   - `reports/data_audit/key_value_frequency.csv`
   - `reports/data_audit/key_field_summary.csv`

5. Upload both generated reports for the next review. They show actual distinct values for coded fields and row dimensions such as `item_desc`, `item_group`, and `item_id`.

Important: the review pack is evidence-based, not a final merge config. Do not create the district-year master table until the newer-year codebook and the value profiles have been checked.
