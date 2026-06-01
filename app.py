import pandas as pd
import streamlit as st

from ai_nutritionist.constants import SAFETY_DISCLAIMER
from ai_nutritionist.data import load_food_catalog
from ai_nutritionist.recommender import recommend, recommend_week


DIETARY_PATTERNS = {
    "Mediterranean / Greek": "mediterranean",
    "Omnivore": "omnivore",
    "Vegetarian": "vegetarian",
    "Vegan": "vegan",
    "Keto-style / low carb": "keto_style",
}

GOAL_FOCUS = {
    "Balanced": "balanced",
    "Higher protein": "higher_protein",
    "Higher fiber": "higher_fiber",
    "Lighter meals": "lighter_meals",
    "Lower sodium": "lower_sodium",
}

WEIGHT_GOALS = {
    "Auto from BMI": "auto",
    "Maintain weight": "maintain",
    "Lose weight": "lose",
    "Gain weight": "gain",
}

PLAN_VARIATIONS = {
    "mediterranean": [
        ("chicken", "souvlaki"),
        ("salmon", "fish"),
        ("lentil", "fasolada"),
        ("cod", "plaki"),
        ("chickpea", "gigantes"),
        ("tuna", "white bean"),
    ],
    "omnivore": [("chicken",), ("salmon", "fish"), ("beans", "lentil"), ("turkey",)],
    "vegetarian": [("egg", "yogurt"), ("lentil", "beans"), ("chickpea", "hummus"), ("tofu",)],
    "vegan": [("lentil", "beans"), ("tofu", "soy"), ("chickpea", "hummus"), ("quinoa", "beans")],
    "keto_style": [("chicken",), ("salmon", "fish"), ("egg",), ("turkey",)],
}

FEEDBACK_AVOID_TERMS = (
    "chicken",
    "souvlaki",
    "salmon",
    "cod",
    "tuna",
    "lentil",
    "fasolada",
    "chickpea",
    "gigantes",
    "beans",
    "yogurt",
    "egg",
    "turkey",
    "tofu",
)


st.set_page_config(page_title="AI Nutritionist", page_icon="AI", layout="wide")

st.markdown(
    """
    <style>
      #MainMenu,
      footer,
      header,
      [data-testid="stDeployButton"],
      [data-testid="stToolbar"],
      [data-testid="stDecoration"],
      [data-testid="stStatusWidget"],
      .stDeployButton {
        display: none !important;
      }
      .block-container {
        padding-top: 3rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def _catalog() -> pd.DataFrame:
    return load_food_catalog()


def _progress_value(current: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return min(float(current) / float(target), 1.0)


def _progress_row(label: str, current: float, target: float, unit: str, *, limit: bool = False) -> None:
    pct = 0 if target <= 0 else (current / target) * 100
    status = "limit" if limit else "target"
    st.write(f"**{label}**")
    st.progress(_progress_value(current, target))
    st.caption(f"{current:.1f}{unit} / {target:.1f}{unit} {status} ({pct:.0f}%)")


def _items_frame(items: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(items)[
        [
            "food_name",
            "food_group",
            "serving_grams",
            "calories",
            "protein_g",
            "carbohydrate_g",
            "fiber_g",
            "sugars_g",
            "sodium_mg",
            "saturated_fat_g",
            "vegetarian",
            "vegan",
        ]
    ]


def _ensure_session_state() -> None:
    st.session_state.setdefault("feedback_log", [])
    st.session_state.setdefault("last_plan", None)
    st.session_state.setdefault("plan_variant", 0)


def _merge_terms(*values: str | list[str] | tuple[str, ...] | None) -> list[str]:
    merged: list[str] = []
    for value in values:
        if not value:
            continue
        if isinstance(value, str):
            terms = value.replace(";", ",").replace("\n", ",").split(",")
        else:
            terms = list(value)
        for term in terms:
            cleaned = str(term).strip().lower()
            if cleaned and cleaned not in merged:
                merged.append(cleaned)
    return merged


def _variation_terms(dietary_pattern: str, variant: int) -> tuple[str, ...]:
    options = PLAN_VARIATIONS.get(dietary_pattern, ())
    if not options or variant <= 0:
        return ()
    return options[(variant - 1) % len(options)]


def _feedback_avoid_terms() -> list[str]:
    terms: list[str] = []
    for entry in st.session_state.feedback_log:
        if entry.get("sentiment") != "not_liked":
            continue
        for term in entry.get("avoid_terms", []):
            if term not in terms:
                terms.append(term)
    return terms


def _main_feedback_terms(items: list[dict[str, object]]) -> list[str]:
    names = " ".join(str(item.get("food_name", "")).lower() for item in items)
    return [term for term in FEEDBACK_AVOID_TERMS if term in names][:3]


def _feedback_widget(
    *,
    scope: str,
    label: str,
    items: list[dict[str, object]],
    context: dict[str, object],
) -> None:
    st.caption(f"Was this {scope} useful?")
    key = f"feedback_{scope}_{label}".lower().replace(" ", "_").replace("/", "_")
    value = st.feedback("thumbs", key=key)
    marker_key = f"{key}_recorded"
    if value is None or st.session_state.get(marker_key) == value:
        return

    sentiment = "liked" if value == 1 else "not_liked"
    st.session_state.feedback_log.append(
        {
            "timestamp_utc": pd.Timestamp.utcnow().isoformat(),
            "scope": scope,
            "label": label,
            "sentiment": sentiment,
            "avoid_terms": _main_feedback_terms(items) if sentiment == "not_liked" else [],
            **context,
        }
    )
    st.session_state[marker_key] = value
    if sentiment == "not_liked":
        st.caption("Feedback saved locally. Use Regenerate with feedback to try a different version.")


def _feedback_csv() -> str:
    if not st.session_state.feedback_log:
        return "timestamp_utc,scope,label,sentiment,avoid_terms\n"
    frame = pd.DataFrame(st.session_state.feedback_log).copy()
    if "avoid_terms" in frame.columns:
        frame["avoid_terms"] = frame["avoid_terms"].apply(lambda terms: ", ".join(terms or []))
    return frame.to_csv(index=False)


_ensure_session_state()

st.title("AI Nutritionist")
st.caption("Interactive USDA-backed planner with a deterministic neural food ranker and preference-aware guardrails.")
st.warning(SAFETY_DISCLAIMER)

with st.sidebar:
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
        avoid_foods = st.text_input("Avoid foods", placeholder="fish, chicken, nuts")
        preferred_foods = st.text_input("Prefer foods", placeholder="salmon, beans, berries")
        st.caption("Separate terms with commas. Matching is conservative substring matching on USDA food names.")

    submitted = st.button("Generate meal plan", type="primary", use_container_width=True)
    regenerate = False
    if st.session_state.last_plan is not None:
        regenerate = st.button("Regenerate with feedback", use_container_width=True)
        if _feedback_avoid_terms():
            st.caption("Uses disliked meals from this local session as avoid signals.")

should_generate = submitted or regenerate

if should_generate:
    if regenerate:
        st.session_state.plan_variant += 1
    else:
        st.session_state.plan_variant = 0
    dietary_pattern = DIETARY_PATTERNS[dietary_label]
    effective_avoid_terms = _merge_terms(avoid_foods, _feedback_avoid_terms())
    effective_preferred_terms = _merge_terms(
        preferred_foods,
        _variation_terms(dietary_pattern, st.session_state.plan_variant),
    )

    with st.spinner("Ranking USDA foods and building the meal plan..."):
        weekly_result = None
        if plan_length == "Weekly":
            weekly_result = recommend_week(
                weight_kg=weight,
                height_cm=height,
                age=age,
                sex=sex,
                activity=activity,
                dietary_pattern=dietary_pattern,
                body_fat_pct=body_fat_pct,
                weight_goal=WEIGHT_GOALS[weight_goal_label],
                goal_focus=GOAL_FOCUS[focus_label],
                avoid_terms=effective_avoid_terms,
                preferred_terms=effective_preferred_terms,
                top_k=items_per_meal,
            )
            result = weekly_result.days[0].result
        else:
            result = recommend(
                weight_kg=weight,
                height_cm=height,
                age=age,
                sex=sex,
                activity=activity,
                dietary_pattern=dietary_pattern,
                body_fat_pct=body_fat_pct,
                weight_goal=WEIGHT_GOALS[weight_goal_label],
                goal_focus=GOAL_FOCUS[focus_label],
                avoid_terms=effective_avoid_terms,
                preferred_terms=effective_preferred_terms,
                top_k=items_per_meal,
            )
    st.session_state.last_plan = {
        "result": result,
        "weekly_result": weekly_result,
        "dietary_pattern": dietary_pattern,
        "dietary_label": dietary_label,
        "weight_goal_label": weight_goal_label,
        "focus_label": focus_label,
        "plan_length": plan_length,
    }

plan_state = st.session_state.last_plan

if plan_state is not None:
    result = plan_state["result"]
    weekly_result = plan_state["weekly_result"]
    dietary_pattern = str(plan_state["dietary_pattern"])
    dietary_label = str(plan_state["dietary_label"])
    weight_goal_label = str(plan_state["weight_goal_label"])
    focus_label = str(plan_state["focus_label"])
    feedback_context = {
        "dietary_pattern": dietary_pattern,
        "weight_goal": result.preferences["weight_goal"],
        "nutrition_focus": result.preferences["goal_focus"],
        "bmi": round(result.bmi.value, 1),
        "daily_target_calories": result.daily_targets.calories,
    }

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
        profile_tab, weekly_tab, meal_tab, nutrition_tab, alternatives_tab, feedback_tab, data_tab = st.tabs(
            ["Profile", "Weekly Plan", "Day Detail", "Daily Nutrition", "Alternatives", "Feedback", "Data Explorer"]
        )
    else:
        profile_tab, meal_tab, nutrition_tab, alternatives_tab, feedback_tab, data_tab = st.tabs(
            ["Profile", "Meal Plan", "Daily Nutrition", "Alternatives", "Feedback", "Data Explorer"]
        )

    with profile_tab:
        bmi_col, category_col, calories_col, goal_col, focus_col = st.columns(5)
        bmi_col.metric("BMI", f"{result.bmi.value:.1f}")
        category_col.metric("BMI category", result.bmi.category_label)
        calories_col.metric("Daily energy target", f"{result.daily_targets.calories} kcal")
        goal_col.metric("Weight goal", weight_goal_label)
        focus_col.metric("Nutrition focus", focus_label)
        st.write(f"Profile goal: {result.profile_goal}")
        if weekly_result is not None:
            st.caption(
                f"Weekly mode uses {len(weekly_result.days)} daily plans with Mediterranean-style protein rotation "
                "where the selected dietary pattern supports it."
            )
        if result.body_fat_pct is not None and result.lean_body_mass_kg is not None:
            st.caption(
                f"Body fat input: {result.body_fat_pct:.1f}% | "
                f"Estimated lean body mass: {result.lean_body_mass_kg:.1f} kg"
            )
        if result.preferences["avoid_terms"] or result.preferences["preferred_terms"]:
            st.caption(
                "Preferences -> "
                f"Avoiding: {', '.join(result.preferences['avoid_terms']) or 'none'} | "
                f"Preferring: {', '.join(result.preferences['preferred_terms']) or 'none'}"
            )
        st.divider()
        _feedback_widget(
            scope="plan",
            label="overall",
            items=[item for meal in result.meals for item in meal.items],
            context=feedback_context,
        )

    if weekly_result is not None:
        with weekly_tab:
            st.subheader("Weekly Meal Rotation")
            avg_col, poultry_col, fish_col, legume_col = st.columns(4)
            avg_col.metric("Average calories", f"{weekly_result.weekly_averages['calories']:.0f}")
            poultry_col.metric("Poultry days", weekly_result.variety_counts["poultry_days"])
            fish_col.metric("Fish days", weekly_result.variety_counts["fish_days"])
            legume_col.metric("Legume days", weekly_result.variety_counts["legume_days"])
            day_tabs = st.tabs([day.day_name for day in weekly_result.days])
            for day, day_tab in zip(weekly_result.days, day_tabs):
                with day_tab:
                    st.caption(f"Rotation focus: {day.rotation_focus.replace('_', ' ')}")
                    for meal in day.result.meals:
                        with st.container(border=True):
                            st.markdown(f"**{meal.name}: {meal.title}**")
                            metric_cols = st.columns(3)
                            metric_cols[0].metric("Calories", f"{meal.totals['calories']:.0f}")
                            metric_cols[1].metric("Protein", f"{meal.totals['protein_g']:.1f}g")
                            metric_cols[2].metric("Fiber", f"{meal.totals['fiber_g']:.1f}g")
                            st.dataframe(_items_frame(meal.items), hide_index=True, use_container_width=True)

    with meal_tab:
        if weekly_result is not None:
            selected_day_name = st.selectbox("Day", [day.day_name for day in weekly_result.days])
            result = next(day.result for day in weekly_result.days if day.day_name == selected_day_name)
        for meal in result.meals:
            with st.container(border=True):
                st.subheader(meal.title)
                kcal_col, protein_col, fiber_col = st.columns(3)
                kcal_col.metric("Calories", f"{meal.totals['calories']:.0f}")
                protein_col.metric("Protein", f"{meal.totals['protein_g']:.1f}g")
                fiber_col.metric("Fiber", f"{meal.totals['fiber_g']:.1f}g")
                st.caption(f"Ranker: {meal.model_name}")
                st.dataframe(_items_frame(meal.items), hide_index=True, use_container_width=True)
                with st.expander("Why these foods?"):
                    for explanation in meal.explanations:
                        st.write(f"- {explanation}")
                with st.expander("Swap options"):
                    for group, alternatives in meal.alternatives.items():
                        st.write(f"**{group.replace('_', ' ').title()}**")
                        st.dataframe(_items_frame(alternatives[:2]), hide_index=True, use_container_width=True)
                _feedback_widget(
                    scope="meal",
                    label=meal.name,
                    items=meal.items,
                    context={**feedback_context, "meal": meal.name},
                )

    with nutrition_tab:
        totals = result.daily_totals
        targets = result.daily_targets
        st.subheader("Daily Nutrition Progress")
        macro_col1, macro_col2, macro_col3 = st.columns(3)
        macro_col1.metric("Protein calories", f"{result.macro_percentages['protein_pct']:.1f}%")
        macro_col2.metric("Carb calories", f"{result.macro_percentages['carbohydrate_pct']:.1f}%")
        macro_col3.metric("Fat calories", f"{result.macro_percentages['fat_pct']:.1f}%")
        left, middle, right = st.columns(3)
        with left:
            _progress_row("Calories", totals["calories"], targets.calories, " kcal")
            _progress_row("Protein", totals["protein_g"], targets.protein_g, "g")
        with middle:
            _progress_row("Fiber", totals["fiber_g"], targets.fiber_g, "g")
            _progress_row("Sugars", totals["sugars_g"], targets.sugars_g_limit, "g", limit=True)
        with right:
            _progress_row("Sodium", totals["sodium_mg"], targets.sodium_mg_limit, "mg", limit=True)
            _progress_row(
                "Saturated fat",
                totals["saturated_fat_g"],
                targets.saturated_fat_g_limit,
                "g",
                limit=True,
            )
        st.dataframe(pd.DataFrame([totals]), hide_index=True, use_container_width=True)

    with alternatives_tab:
        st.subheader("Swap Alternatives")
        for meal in result.meals:
            with st.expander(meal.name, expanded=meal.name == "Breakfast"):
                for group, alternatives in meal.alternatives.items():
                    st.write(f"**{group.replace('_', ' ').title()}**")
                    st.dataframe(_items_frame(alternatives), hide_index=True, use_container_width=True)

    with feedback_tab:
        st.subheader("Feedback")
        st.caption("Feedback is stored only in this local Streamlit session and is not uploaded.")
        if st.session_state.feedback_log:
            st.dataframe(pd.DataFrame(st.session_state.feedback_log), hide_index=True, use_container_width=True)
            st.download_button(
                "Download feedback CSV",
                data=_feedback_csv(),
                file_name="ai_nutritionist_feedback.csv",
                mime="text/csv",
                use_container_width=True,
            )
            if _feedback_avoid_terms():
                st.info("Negative feedback will be used as local avoid terms when you click Regenerate with feedback.")
        else:
            st.write("No feedback recorded yet.")

    with data_tab:
        st.subheader("USDA Catalog Explorer")
        catalog = _catalog()
        if DIETARY_PATTERNS[dietary_label] == "vegan":
            catalog = catalog.loc[catalog["vegan"]]
        elif DIETARY_PATTERNS[dietary_label] == "vegetarian":
            catalog = catalog.loc[catalog["vegetarian"]]
        elif DIETARY_PATTERNS[dietary_label] == "keto_style":
            catalog = catalog.loc[
                catalog["food_group"].isin({"protein", "vegetable", "healthy_fat"})
                & (catalog["carbohydrate_g"] <= 18)
                & (catalog["sugars_g"] <= 6)
            ]

        group_options = ["All", *sorted(catalog["food_group"].unique())]
        group_filter = st.selectbox("Food group", group_options)
        search = st.text_input("Search catalog", placeholder="oat, salmon, beans")
        filtered = catalog.copy()
        if group_filter != "All":
            filtered = filtered.loc[filtered["food_group"] == group_filter]
        if search.strip():
            filtered = filtered.loc[filtered["food_name"].str.contains(search.strip(), case=False, na=False)]

        count_col, vegan_col, vegetarian_col = st.columns(3)
        count_col.metric("Foods shown", len(filtered))
        vegan_col.metric("Vegan rows", int(filtered["vegan"].sum()))
        vegetarian_col.metric("Vegetarian rows", int(filtered["vegetarian"].sum()))
        st.dataframe(filtered.head(250), hide_index=True, use_container_width=True)
else:
    with st.container(border=True):
        st.subheader("No meal plan generated yet")
        st.caption("Profile-based recommendations will appear here after generation.")
