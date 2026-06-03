# Research Notes

AI Nutritionist uses public nutrient data and broad population-level guidance. It does not claim clinical accuracy.

## Project Status

These notes support the current standalone software system. They are not thesis material and should not be read as a clinical or academic validation study.

## Data Source

- USDA FoodData Central downloadable datasets: https://fdc.nal.usda.gov/download-datasets/
- This project uses the FNDDS 2021-2023 CSV release dated October 2024.
- The committed processed catalog is reproducible through `scripts/build_food_catalog.py`.
- The data pipeline derives serving sizes, meal tags, vegetarian flags, vegan flags, and broad food groups from USDA descriptions and WWEIA categories.

## Guidance Used For Scoring

- Dietary Guidelines for Americans 2025-2030 overview: https://www.fns.usda.gov/cnpp/dietary-guidelines-americans
- ODPHP Dietary Guidelines evidence resource: https://odphp.health.gov/healthypeople/tools-action/browse-evidence-based-resources/dietary-guidelines-americans-2025-2030
- WHO healthy diet guidance: https://www.who.int/health-topics/healthy-diet
- CDC healthy eating tips: https://www.cdc.gov/nutrition/features/healthy-eating-tips.html
- NIH/National Academies DRI overview: https://ods.od.nih.gov/healthinformation/nutrientrecommendations.aspx
- American Heart Association Mediterranean diet overview: https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/mediterranean-diet
- Mayo Clinic Mediterranean diet overview: https://www.mayoclinic.org/healthy-lifestyle/nutrition-and-healthy-eating/in-depth/mediterranean-diet/art-20047801
- CDC losing weight guidance: https://www.cdc.gov/healthy-weight-growth/losing-weight/index.html
- Mayo Clinic weight loss strategy overview: https://www.mayoclinic.org/health/weight-loss/HQ01625
- FAO Greece food-based dietary guidelines summary: https://www.fao.org/nutrition/educacion-nutricional/food-dietary-guidelines/regions/greece/previous-versions-gre/es/
- NIH vitamin B12 fact sheet: https://ods.od.nih.gov/factsheets/VitaminB12-HealthProfessional/
- NHS vegan diet overview: https://www.nhs.uk/live-well/eat-well/how-to-eat-a-balanced-diet/the-vegan-diet/

See `docs/GUIDELINE_ALIGNMENT.md` for the implementation map that connects these sources to target constants, meal-level checks, evaluation fields, and caveats.

## Neural Ranking Approach

The project uses a local scikit-learn `MLPRegressor` as a neural food ranker. The ranker is trained on weak labels generated from USDA nutrients and guidance-alignment rules. This is intentionally not described as clinical fine-tuning because the repository does not include registered-dietitian labels, clinical outcomes, allergies, medical history, medication interactions, or disease-state targets.

The weak-label target rewards protein density, fiber density, meal fit, lower sodium density, lower saturated-fat density, lower total-sugar density, and a minimally processed signal. The meal planner then applies deterministic guardrails so the model cannot freely output high-sugar, high-sodium, repeated, or meal-context-inappropriate foods.

## Mediterranean/Greek Handling

The project now includes a curated Mediterranean/Greek extension because raw nutrient ranking can over-select technically nutritious but awkward standalone ingredients such as sprouts or seeds. The extension follows broad Mediterranean pattern guidance: vegetables, fruits, whole grains, legumes, olive oil, fish/seafood, poultry, yogurt, and modest cheese use. Greek-oriented rows include foods such as Greek yogurt bowls, dakos-style toast, lentil soup, fasolada, chickpea salad, grilled fish with horta, cucumber tomato salad, and olive-oil vegetable sides.

These rows are practical software data, not clinical diet plans. Nutrients are estimated from USDA-style components and are used to make the recommender produce recognizable meals while preserving safety disclaimers and guardrails.

The weekly planner uses that guidance as a rotation pattern rather than a prescription: poultry appears on selected days, fish/seafood appears multiple times, legumes are deliberately surfaced, and vegetables, whole-grain/starch sides, yogurt, fruit, and olive oil remain recurring anchors. This is based on public Mediterranean guidance from the American Heart Association, Mayo Clinic, and Greece food-based dietary guideline summaries, which emphasize vegetables, fruits, whole grains, legumes, olive oil, fish, poultry, and limited red meat.

The planner does not claim that a generated week is clinically optimized. It is a reproducible product behavior check that makes the recommender output more practical, varied, and culturally coherent.

## Weight Goal Handling

`weight_goal` is separate from nutrition focus. `auto` uses the BMI category to choose a conservative energy direction. `maintain`, `lose`, and `gain` let the user explicitly choose the planning direction while preserving calorie floors and safety language. The system does not promise weight loss or gain outcomes.

For explicit `lose`, the project uses a bounded deficit heuristic rather than a flat subtraction. Public guidance commonly frames gradual weight loss around steady behavior change and calorie reduction; CDC describes gradual 1-2 pound-per-week loss as more maintainable, and Mayo Clinic describes creating a daily calorie deficit through intake reduction and activity. The implementation uses a conservative 25% estimated-energy deficit bounded by profile category, then scales generated portions if the plan sits materially above the target. This is a software planning heuristic, not a personalized medical prescription.

## Feedback Handling

The Streamlit feedback feature is a local product signal. Users can mark the full plan or individual meals with thumbs feedback. Negative meal feedback is converted into temporary avoid terms for `Regenerate with feedback`, and the session log can be exported as CSV for review. The app does not upload feedback, profile data, or generated plans.

## Vegan Handling

Vegan mode uses conservative category and description rules. Plant-based milk/yogurt, legumes, grains, fruits, vegetables, nuts, seeds, and oils can be selected when the description does not include animal-derived terms. Ambiguous mixed dishes are not marked vegan unless the rules are clear enough for a public wellness recommender.

The UI and docs do not claim that vegan mode solves all nutrient-planning concerns. Vitamin B12, vitamin D, iodine, iron, calcium, and omega-3 planning can require fortified foods, supplements, or professional guidance.

## Keto-Style Handling

Keto-style mode is implemented as a low-carbohydrate food filter and meal template. It avoids grain slots, limits per-serving carbohydrate and sugar, and prioritizes protein, vegetables, and healthy-fat groups. It is not presented as a therapeutic ketogenic diet and is not intended for diabetes, epilepsy, pregnancy nutrition, or disease management.

## Body-Fat Input

When body-fat percentage is provided, the system estimates lean body mass and raises the protein target when the lean-mass-based estimate is higher than the default body-weight estimate. This is a planning signal only, not a body-composition diagnosis.

## Practical Translation

The system rewards:

- protein presence at each meal
- fruits and vegetables
- fiber-rich foods
- whole-grain or minimally processed carbohydrate sources
- lower sodium density
- lower saturated fat density
- lower total sugar density, while noting that USDA total sugars are not equivalent to added sugars
- meal group diversity

The system avoids:

- disease-specific claims
- clinical prescriptions
- replacing a registered dietitian or physician
- presenting BMI or calorie targets as diagnosis or treatment
