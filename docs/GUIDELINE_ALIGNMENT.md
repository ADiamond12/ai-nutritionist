# Guideline Alignment

AI Nutritionist is a software recommender, not a clinical nutrition system. This page documents how public nutrition guidance is translated into code-level guardrails so the project stays inspectable and honest.

## Source Posture

The project uses public guidance as product constraints, not as proof of medical accuracy:

- USDA/FNS Dietary Guidelines for Americans 2025-2030 overview: https://www.fns.usda.gov/cnpp/dietary-guidelines-americans
- WHO healthy diet fact sheet: https://www.who.int/news-room/fact-sheets/detail/healthy-diet
- USDA MyPlate resources: https://www.myplate.gov/
- American Heart Association Mediterranean diet overview: https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/mediterranean-diet
- NHLBI heart-healthy food guidance: https://www.nhlbi.nih.gov/health/heart-healthy-living/healthy-foods

## Implementation Map

| Guidance theme | Code behavior | Boundary |
| --- | --- | --- |
| Prioritize whole, healthy, nutritious foods | `ai_nutritionist.guidelines` defines real-food guardrails; the ranker rewards minimally processed rows and practical meal groups. | Processing is inferred from catalog/category rules, not a full processing classification model. |
| Vegetables, fruits, fiber-rich foods | Meal checks require produce presence and reward fiber-rich foods. Daily fiber target uses 25-30 g depending on profile. | This does not prove full micronutrient adequacy or exact produce grams. |
| Saturated fat | Profile targets cap saturated fat at 10% of target calories. | This is a general wellness guardrail, not lipid-management care. |
| Sodium | The app uses a 2,300 mg daily sodium guardrail and documents sodium misses in evaluation. WHO's adult reference is stricter at about 2,000 mg sodium. | USDA prepared-food rows can be sodium-heavy; misses are surfaced rather than hidden. |
| Sugars | Total sugar is used as a cautious proxy signal at 10% of target calories. | USDA total sugars are not equivalent to free or added sugars. |
| Mediterranean-style pattern | Weekly Mediterranean mode rotates poultry, fish/seafood, legumes, vegetables, whole grains/starches, yogurt, fruit, and olive-oil sides. | This is food-culture/product framing, not a therapeutic prescription. |

## Why This Matters

The recommendation model can rank foods, but the public product needs visible constraints around what it is optimizing. This document makes the connection between sources, code, and limitations explicit:

- The app does not claim clinical validation.
- Internal quality scores are not shown to users.
- Sodium and sugar limitations are documented where the available data is imperfect.
- Vegan and keto-style modes stay clearly labeled as wellness filters.
- BMI, calories, and body-fat input are planning signals, not diagnoses.

## Code References

- `ai_nutritionist/guidelines.py`: guideline constants and source-backed implementation notes.
- `ai_nutritionist/profile.py`: daily target construction for fiber, sodium, saturated fat, and sugar.
- `ai_nutritionist/recommender.py`: meal-level checks, weekly rotation, and practical food filtering.
- `ai_nutritionist/evaluation.py`: product-quality matrix that records whether guardrails pass.
