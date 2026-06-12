import streamlit as st
from typing import cast

from ai_nutritionist.constants import SAFETY_DISCLAIMER
from ai_nutritionist.recommender import recommend, recommend_week
from ai_nutritionist.ui.components import hide_streamlit_chrome
from ai_nutritionist.ui.config import DIETARY_PATTERNS, GOAL_FOCUS, WEIGHT_GOALS
from ai_nutritionist.ui.state import compatible_variation_terms, feedback_avoid_terms, merge_terms, ensure_session_state
from ai_nutritionist.ui.tabs import (
    feedback_context,
    render_alternatives_tab,
    render_data_tab,
    render_feedback_tab,
    render_grocery_tab,
    render_meal_tab,
    render_nutrition_tab,
    render_profile_tab,
    render_weekly_tab,
)


def run_app() -> None:
    st.set_page_config(
        page_title="AI Nutritionist",
        page_icon="AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    hide_streamlit_chrome()
    ensure_session_state()

    st.title("AI Nutritionist")
    st.caption(
        "Interactive USDA-backed planner with a deterministic neural food ranker and preference-aware guardrails."
    )
    st.warning(SAFETY_DISCLAIMER)

    with st.container(border=True):
        profile_inputs = _render_sidebar()

    if profile_inputs["should_generate"]:
        _generate_plan(profile_inputs)

    _render_plan_state()


def _render_sidebar() -> dict[str, object]:
    st.header("Profile")
    weight = st.number_input("Weight (kg)", min_value=30.0, max_value=220.0, value=75.0, step=0.5)
    height = st.number_input("Height (cm)", min_value=120.0, max_value=230.0, value=180.0, step=0.5)
    age = st.number_input("Age", min_value=10, max_value=100, value=30, step=1)
    sex = st.selectbox("Sex for energy estimate", ["unspecified", "female", "male"], index=0)
    activity = st.selectbox("Activity level", ["sedentary", "light", "moderate", "active"], index=2)
    use_body_fat = st.checkbox("Use body fat % for protein target")
    body_fat_pct = None
    if use_body_fat:
        body_fat_pct = st.number_input("Body fat (%)", min_value=5.0, max_value=60.0, value=18.0, step=0.5)

    st.header("Planner")
    plan_length = st.radio("Plan length", ["Daily", "Weekly"], horizontal=True)
    weight_goal_label = st.selectbox("Weight goal", list(WEIGHT_GOALS), index=0)
    dietary_label = st.selectbox("Dietary pattern", list(DIETARY_PATTERNS))
    focus_label = st.selectbox("Nutrition focus", list(GOAL_FOCUS))
    items_per_meal = st.slider("Items per meal", min_value=3, max_value=5, value=4)

    with st.expander("Preferences", expanded=True):
        avoid_foods = st.text_input("Avoid foods", placeholder="Optional: foods to avoid")
        preferred_foods = st.text_input("Prefer foods", placeholder="Optional: foods to prefer")
        st.caption("Separate terms with commas. Matching is conservative substring matching on USDA food names.")

    submitted = st.button("Generate meal plan", type="primary", width="stretch")
    regenerate = False
    if st.session_state.last_plan is not None:
        regenerate = st.button("Regenerate with feedback", width="stretch")
        if feedback_avoid_terms():
            st.caption("Uses disliked meals from this local session as avoid signals.")

    should_generate = submitted or regenerate
    return {
        "weight": weight,
        "height": height,
        "age": age,
        "sex": sex,
        "activity": activity,
        "body_fat_pct": body_fat_pct,
        "plan_length": plan_length,
        "weight_goal_label": weight_goal_label,
        "dietary_label": dietary_label,
        "focus_label": focus_label,
        "items_per_meal": items_per_meal,
        "avoid_foods": avoid_foods,
        "preferred_foods": preferred_foods,
        "regenerate": regenerate,
        "should_generate": should_generate,
    }


def _generate_plan(inputs: dict[str, object]) -> None:
    if bool(inputs["regenerate"]):
        st.session_state.plan_variant += 1
    else:
        st.session_state.plan_variant = 0

    dietary_pattern = DIETARY_PATTERNS[str(inputs["dietary_label"])]
    effective_avoid_terms = merge_terms(str(inputs["avoid_foods"]), feedback_avoid_terms())
    effective_preferred_terms = merge_terms(
        str(inputs["preferred_foods"]),
        compatible_variation_terms(dietary_pattern, st.session_state.plan_variant, effective_avoid_terms),
    )

    with st.spinner("Ranking USDA foods and building the meal plan..."):
        weekly_result = None
        if str(inputs["plan_length"]) == "Weekly":
            weekly_result = recommend_week(
                weight_kg=_float_input(inputs["weight"]),
                height_cm=_float_input(inputs["height"]),
                age=_int_input(inputs["age"]),
                sex=str(inputs["sex"]),
                activity=str(inputs["activity"]),
                dietary_pattern=dietary_pattern,
                body_fat_pct=_optional_float_input(inputs["body_fat_pct"]),
                weight_goal=WEIGHT_GOALS[str(inputs["weight_goal_label"])],
                goal_focus=GOAL_FOCUS[str(inputs["focus_label"])],
                avoid_terms=effective_avoid_terms,
                preferred_terms=effective_preferred_terms,
                top_k=_int_input(inputs["items_per_meal"]),
            )
            result = weekly_result.days[0].result
        else:
            result = recommend(
                weight_kg=_float_input(inputs["weight"]),
                height_cm=_float_input(inputs["height"]),
                age=_int_input(inputs["age"]),
                sex=str(inputs["sex"]),
                activity=str(inputs["activity"]),
                dietary_pattern=dietary_pattern,
                body_fat_pct=_optional_float_input(inputs["body_fat_pct"]),
                weight_goal=WEIGHT_GOALS[str(inputs["weight_goal_label"])],
                goal_focus=GOAL_FOCUS[str(inputs["focus_label"])],
                avoid_terms=effective_avoid_terms,
                preferred_terms=effective_preferred_terms,
                top_k=_int_input(inputs["items_per_meal"]),
            )

    st.session_state.last_plan = {
        "result": result,
        "weekly_result": weekly_result,
        "dietary_pattern": dietary_pattern,
        "dietary_label": inputs["dietary_label"],
        "weight_goal_label": inputs["weight_goal_label"],
        "focus_label": inputs["focus_label"],
        "plan_length": inputs["plan_length"],
    }


def _render_plan_state() -> None:
    plan_state = st.session_state.last_plan
    if plan_state is None:
        with st.container(border=True):
            st.subheader("No meal plan generated yet")
            st.caption("Profile-based recommendations will appear here after generation.")
        return

    result = plan_state["result"]
    weekly_result = plan_state["weekly_result"]
    dietary_pattern = str(plan_state["dietary_pattern"])
    dietary_label = str(plan_state["dietary_label"])
    weight_goal_label = str(plan_state["weight_goal_label"])
    focus_label = str(plan_state["focus_label"])
    context = feedback_context(result, dietary_pattern)

    if dietary_pattern == "vegan":
        st.info(
            "Vegan mode filters for conservative plant-only foods. It does not replace planning for B12, "
            "vitamin D, iron, iodine, omega-3, calcium, or professional dietary guidance."
        )
    if dietary_pattern == "keto_style":
        st.info(
            "Keto-style mode is a low-carbohydrate wellness filter, not a therapeutic ketogenic diet. "
            "It should not be used to manage diabetes, epilepsy, pregnancy nutrition, or medical conditions."
        )

    if weekly_result is not None:
        (
            profile_tab,
            weekly_tab,
            meal_tab,
            nutrition_tab,
            alternatives_tab,
            grocery_tab,
            feedback_tab,
            data_tab,
        ) = st.tabs(
            [
                "Profile",
                "Weekly Plan",
                "Day Detail",
                "Daily Nutrition",
                "Alternatives",
                "Grocery List",
                "Feedback",
                "Data Explorer",
            ]
        )
    else:
        profile_tab, meal_tab, nutrition_tab, alternatives_tab, grocery_tab, feedback_tab, data_tab = st.tabs(
            ["Profile", "Meal Plan", "Daily Nutrition", "Alternatives", "Grocery List", "Feedback", "Data Explorer"]
        )

    with profile_tab:
        render_profile_tab(result, weekly_result, weight_goal_label, focus_label, context)
    if weekly_result is not None:
        with weekly_tab:
            render_weekly_tab(weekly_result)
    with meal_tab:
        result = render_meal_tab(result, weekly_result, context)
    with nutrition_tab:
        render_nutrition_tab(result)
    with alternatives_tab:
        render_alternatives_tab(result)
    with grocery_tab:
        render_grocery_tab(result, weekly_result)
    with feedback_tab:
        render_feedback_tab()
    with data_tab:
        render_data_tab(dietary_label)


def _float_input(value: object) -> float:
    return float(cast(str | int | float, value))


def _int_input(value: object) -> int:
    return int(cast(str | int | float, value))


def _optional_float_input(value: object) -> float | None:
    if value is None:
        return None
    return _float_input(value)
