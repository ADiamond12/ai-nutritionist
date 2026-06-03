from dataclasses import dataclass


@dataclass(frozen=True)
class GuidelineGuardrail:
    id: str
    public_name: str
    implementation: str
    source_url: str
    source_note: str
    caveat: str


SODIUM_LIMIT_MG = 2300.0
WHO_SODIUM_REFERENCE_MG = 2000.0
SATURATED_FAT_MAX_ENERGY_PCT = 10.0
SUGAR_REFERENCE_ENERGY_PCT = 10.0
GENERAL_FIBER_TARGET_G = 25.0
MALE_FIBER_TARGET_G = 30.0
ADULT_PRODUCE_REFERENCE_G = 400.0

MEDITERRANEAN_ANCHOR_GROUPS = (
    "vegetables",
    "fruits",
    "whole grains",
    "legumes",
    "fish/seafood",
    "poultry",
    "olive-oil and unsaturated-fat sources",
)

GUIDELINE_GUARDRAILS = (
    GuidelineGuardrail(
        id="real_food_pattern",
        public_name="Prioritize whole and minimally processed foods",
        implementation="Ranker rewards minimally_processed rows and practical whole-food meal groups.",
        source_url="https://www.fns.usda.gov/cnpp/dietary-guidelines-americans",
        source_note="USDA/FNS Dietary Guidelines for Americans 2025-2030 overview.",
        caveat="The app uses catalog-level processing signals, not a full food-processing ontology.",
    ),
    GuidelineGuardrail(
        id="produce_and_fiber",
        public_name="Include produce and fiber-rich foods",
        implementation=(
            "Meal checks require produce presence and reward fiber-rich items; daily targets use "
            f"{GENERAL_FIBER_TARGET_G:.0f}-{MALE_FIBER_TARGET_G:.0f} g fiber."
        ),
        source_url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        source_note="WHO healthy diet fact sheet: adults should aim for fruit/vegetable intake and dietary fiber.",
        caveat="USDA rows do not verify full-day micronutrient adequacy or exact fruit/vegetable gram targets.",
    ),
    GuidelineGuardrail(
        id="saturated_fat",
        public_name="Limit saturated fat",
        implementation=f"Daily saturated-fat guardrail is {SATURATED_FAT_MAX_ENERGY_PCT:.0f}% of target calories.",
        source_url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        source_note="WHO recommends no more than 10% of total energy from saturated fat.",
        caveat="This is a population-level guardrail, not a clinical lipid-management prescription.",
    ),
    GuidelineGuardrail(
        id="sodium",
        public_name="Track sodium conservatively",
        implementation=(
            f"Daily sodium guardrail is {SODIUM_LIMIT_MG:.0f} mg, while evaluation documents misses; "
            f"WHO's adult reference is stricter at about {WHO_SODIUM_REFERENCE_MG:.0f} mg sodium."
        ),
        source_url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        source_note="WHO healthy diet fact sheet gives a less-than-5-g salt / 2-g sodium reference.",
        caveat=(
            "Restaurant-style or prepared USDA/FNDDS rows can exceed sodium limits even when meals are "
            "otherwise practical."
        ),
    ),
    GuidelineGuardrail(
        id="sugars",
        public_name="Limit free or added sugars without overclaiming total-sugar data",
        implementation=(
            f"Sugar guardrail uses {SUGAR_REFERENCE_ENERGY_PCT:.0f}% of target calories as a cautious "
            "ranking signal."
        ),
        source_url="https://www.who.int/news-room/fact-sheets/detail/healthy-diet",
        source_note="WHO recommends limiting free sugars to less than 10% of total energy.",
        caveat="USDA total sugars are not the same as free or added sugars, so the app labels this as a proxy.",
    ),
    GuidelineGuardrail(
        id="mediterranean_pattern",
        public_name="Mediterranean-style pattern anchors",
        implementation=(
            "Weekly Mediterranean plans rotate poultry, fish/seafood, legumes, vegetables, whole grains, "
            "and olive-oil sides."
        ),
        source_url="https://www.heart.org/en/healthy-living/healthy-eating/eat-smart/nutrition-basics/mediterranean-diet",
        source_note="American Heart Association Mediterranean diet overview.",
        caveat="The rotation is cultural/product framing, not a prescribed therapeutic diet.",
    ),
)


def guideline_summary() -> list[dict[str, str]]:
    return [
        {
            "id": guardrail.id,
            "public_name": guardrail.public_name,
            "implementation": guardrail.implementation,
            "source_url": guardrail.source_url,
            "caveat": guardrail.caveat,
        }
        for guardrail in GUIDELINE_GUARDRAILS
    ]
