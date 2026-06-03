from ai_nutritionist.guidelines import (
    GENERAL_FIBER_TARGET_G,
    GUIDELINE_GUARDRAILS,
    MALE_FIBER_TARGET_G,
    SATURATED_FAT_MAX_ENERGY_PCT,
    SODIUM_LIMIT_MG,
    SUGAR_REFERENCE_ENERGY_PCT,
    guideline_summary,
)
from ai_nutritionist.profile import build_profile


def test_profile_targets_use_source_backed_guardrail_constants():
    profile = build_profile(weight_kg=75, height_cm=180, age=30, sex="male")

    assert profile.daily_targets.fiber_g == MALE_FIBER_TARGET_G
    assert profile.daily_targets.sodium_mg_limit == SODIUM_LIMIT_MG
    assert profile.daily_targets.saturated_fat_g_limit == round(
        (profile.daily_targets.calories * (SATURATED_FAT_MAX_ENERGY_PCT / 100)) / 9,
        1,
    )
    assert profile.daily_targets.sugars_g_limit == round(
        (profile.daily_targets.calories * (SUGAR_REFERENCE_ENERGY_PCT / 100)) / 4,
        1,
    )


def test_general_fiber_target_applies_to_older_or_non_male_profiles():
    older_profile = build_profile(weight_kg=70, height_cm=170, age=72, sex="female")

    assert older_profile.daily_targets.fiber_g == GENERAL_FIBER_TARGET_G


def test_guideline_summary_is_public_source_backed_and_non_clinical():
    summary = guideline_summary()
    ids = {item["id"] for item in summary}
    source_urls = {item["source_url"] for item in summary}

    assert len(summary) == len(GUIDELINE_GUARDRAILS)
    assert {"real_food_pattern", "sodium", "saturated_fat", "mediterranean_pattern"}.issubset(ids)
    assert "https://www.fns.usda.gov/cnpp/dietary-guidelines-americans" in source_urls
    assert "https://www.who.int/news-room/fact-sheets/detail/healthy-diet" in source_urls
    assert any("clinical" in item["caveat"].lower() for item in summary)
    assert any("proxy" in item["caveat"].lower() for item in summary)
