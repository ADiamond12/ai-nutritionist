# Recipe Pilot Data

This folder contains a small nine-recipe reviewed recipe-backed pilot for AI Nutritionist.

The rows are local, deterministic, and public-safe. They are ingredient-level curated estimates using USDA-style public nutrient references and project-defined portions. They are not clinical nutrition validation, allergy-safe proof, or a production recipe corpus.

Runtime loading projects these recipes back into the existing flat `CATALOG_COLUMNS` schema. Internal recipe IDs, review notes, and ingredient metadata are kept out of public recommendation payloads unless a dedicated ingredient grocery export is explicitly built from selected recipe-backed rows.
