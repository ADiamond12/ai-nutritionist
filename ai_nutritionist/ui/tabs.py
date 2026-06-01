import pandas as pd
import streamlit as st

from ai_nutritionist.ui.components import catalog, feedback_widget, items_frame, progress_row
from ai_nutritionist.ui.config import DIETARY_PATTERNS
from ai_nutritionist.ui.state import feedback_avoid_terms, feedback_csv


def feedback_context(result, dietary_pattern: str) -> dict[str, object]:
    return {
        "dietary_pattern": dietary_pattern,
        "weight_goal": result.preferences["weight_goal"],
        "nutrition_focus": result.preferences["goal_focus"],
        "bmi": round(result.bmi.value, 1),
        "daily_target_calories": result.daily_targets.calories,
    }


def render_profile_tab(result, weekly_result, weight_goal_label: str, focus_label: str, context: dict[str, object]) -> None:
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
    feedback_widget(
        scope="plan",
        label="overall",
        items=[item for meal in result.meals for item in meal.items],
        context=context,
    )


def render_weekly_tab(weekly_result) -> None:
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
                    st.dataframe(items_frame(meal.items), hide_index=True, use_container_width=True)


def render_meal_tab(result, weekly_result, context: dict[str, object]):
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
            st.dataframe(items_frame(meal.items), hide_index=True, use_container_width=True)
            with st.expander("Why these foods?"):
                for explanation in meal.explanations:
                    st.write(f"- {explanation}")
            with st.expander("Swap options"):
                for group, alternatives in meal.alternatives.items():
                    st.write(f"**{group.replace('_', ' ').title()}**")
                    st.dataframe(items_frame(alternatives[:2]), hide_index=True, use_container_width=True)
            feedback_widget(
                scope="meal",
                label=meal.name,
                items=meal.items,
                context={**context, "meal": meal.name},
            )
    return result


def render_nutrition_tab(result) -> None:
    totals = result.daily_totals
    targets = result.daily_targets
    st.subheader("Daily Nutrition Progress")
    macro_col1, macro_col2, macro_col3 = st.columns(3)
    macro_col1.metric("Protein calories", f"{result.macro_percentages['protein_pct']:.1f}%")
    macro_col2.metric("Carb calories", f"{result.macro_percentages['carbohydrate_pct']:.1f}%")
    macro_col3.metric("Fat calories", f"{result.macro_percentages['fat_pct']:.1f}%")
    left, middle, right = st.columns(3)
    with left:
        progress_row("Calories", totals["calories"], targets.calories, " kcal")
        progress_row("Protein", totals["protein_g"], targets.protein_g, "g")
    with middle:
        progress_row("Fiber", totals["fiber_g"], targets.fiber_g, "g")
        progress_row("Sugars", totals["sugars_g"], targets.sugars_g_limit, "g", limit=True)
    with right:
        progress_row("Sodium", totals["sodium_mg"], targets.sodium_mg_limit, "mg", limit=True)
        progress_row("Saturated fat", totals["saturated_fat_g"], targets.saturated_fat_g_limit, "g", limit=True)
    st.dataframe(pd.DataFrame([totals]), hide_index=True, use_container_width=True)


def render_alternatives_tab(result) -> None:
    st.subheader("Swap Alternatives")
    for meal in result.meals:
        with st.expander(meal.name, expanded=meal.name == "Breakfast"):
            for group, alternatives in meal.alternatives.items():
                st.write(f"**{group.replace('_', ' ').title()}**")
                st.dataframe(items_frame(alternatives), hide_index=True, use_container_width=True)


def render_feedback_tab() -> None:
    st.subheader("Feedback")
    st.caption("Feedback is stored only in this local Streamlit session and is not uploaded.")
    if st.session_state.feedback_log:
        st.dataframe(pd.DataFrame(st.session_state.feedback_log), hide_index=True, use_container_width=True)
        st.download_button(
            "Download feedback CSV",
            data=feedback_csv(),
            file_name="ai_nutritionist_feedback.csv",
            mime="text/csv",
            use_container_width=True,
        )
        if feedback_avoid_terms():
            st.info("Negative feedback will be used as local avoid terms when you click Regenerate with feedback.")
    else:
        st.write("No feedback recorded yet.")


def render_data_tab(dietary_label: str) -> None:
    st.subheader("USDA Catalog Explorer")
    data = catalog()
    if DIETARY_PATTERNS[dietary_label] == "vegan":
        data = data.loc[data["vegan"]]
    elif DIETARY_PATTERNS[dietary_label] == "vegetarian":
        data = data.loc[data["vegetarian"]]
    elif DIETARY_PATTERNS[dietary_label] == "keto_style":
        data = data.loc[
            data["food_group"].isin({"protein", "vegetable", "healthy_fat"})
            & (data["carbohydrate_g"] <= 18)
            & (data["sugars_g"] <= 6)
        ]

    group_options = ["All", *sorted(data["food_group"].unique())]
    group_filter = st.selectbox("Food group", group_options)
    search = st.text_input("Search catalog", placeholder="oat, salmon, beans")
    filtered = data.copy()
    if group_filter != "All":
        filtered = filtered.loc[filtered["food_group"] == group_filter]
    if search.strip():
        filtered = filtered.loc[filtered["food_name"].str.contains(search.strip(), case=False, na=False)]

    count_col, vegan_col, vegetarian_col = st.columns(3)
    count_col.metric("Foods shown", len(filtered))
    vegan_col.metric("Vegan rows", int(filtered["vegan"].sum()))
    vegetarian_col.metric("Vegetarian rows", int(filtered["vegetarian"].sum()))
    st.dataframe(filtered.head(250), hide_index=True, use_container_width=True)

