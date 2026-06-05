# Screenshots

This folder stores public-safe screenshots used by the GitHub README and portfolio site.

Current captures:

- `streamlit-meal-plan.png`: generated daily meal-plan tab with meal title, nutrition metrics, and item table.
- `streamlit-weekly-plan.png`: generated weekly Mediterranean-style rotation with day tabs and meal cards.
- `streamlit-daily-nutrition.png`: generated macro and nutrient progress view.
- `streamlit-alternatives.png`: generated swap alternatives for meal components.
- `streamlit-mobile-day-detail.png`: mobile generated day-detail view.
- `streamlit-home.png`: optional profile setup and safety notice before generation.
- `streamlit-recommendations.png`: optional generated overview retained for older portfolio references.

Refresh flow:

```bash
streamlit run app.py
```

Recommended reviewer profile:

- Daily screenshots: default 75 kg, 180 cm, age 30, Mediterranean / Greek, balanced focus, 4 items per meal.
- Weekly screenshot: switch `Plan length` to `Weekly`, keep Mediterranean / Greek, then generate.
- Mobile screenshot: capture the generated `Day Detail` tab at a phone-sized viewport.
- Public-safety check: screenshots must not show `Plan Fit`, `Ranker:`, `quality_score`, or `neural_score`.

Suggested files:

- `streamlit-meal-plan.png`
- `streamlit-weekly-plan.png`
- `streamlit-daily-nutrition.png`
- `streamlit-alternatives.png`
- `streamlit-mobile-day-detail.png`
- `streamlit-recommendations.png`
