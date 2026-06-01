import argparse

from ai_nutritionist.recommender import RecommendationResult, recommend, recommend_week


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI Nutritionist recommendation system")
    parser.add_argument("--weight", type=float, required=True, help="Weight in kg")
    parser.add_argument("--height", type=float, required=True, help="Height in cm")
    parser.add_argument("--age", type=int, required=True, help="Age in years")
    parser.add_argument("--sex", choices=["female", "male", "unspecified"], default="unspecified")
    parser.add_argument("--activity", choices=["sedentary", "light", "moderate", "active"], default="moderate")
    parser.add_argument(
        "--dietary-pattern",
        choices=["mediterranean", "omnivore", "vegetarian", "vegan", "keto_style"],
        default="mediterranean",
    )
    parser.add_argument(
        "--weight-goal",
        choices=["auto", "maintain", "lose", "gain"],
        default="auto",
        help="Energy goal: auto from BMI, maintain, lose, or gain",
    )
    parser.add_argument("--body-fat", type=float, default=None, help="Optional body fat percentage for lean-mass protein target")
    parser.add_argument(
        "--goal-focus",
        choices=["balanced", "higher_protein", "higher_fiber", "lighter_meals", "lower_sodium"],
        default="balanced",
        help="Planning focus for ranking and meal assembly",
    )
    parser.add_argument("--avoid", default="", help="Comma-separated food terms to avoid")
    parser.add_argument("--prefer", default="", help="Comma-separated food terms to boost")
    parser.add_argument(
        "--veg",
        type=int,
        default=-1,
        choices=[-1, 0, 1],
        help="Compatibility filter: -1 any, 0 vegetarian, 1 non-vegetarian",
    )
    parser.add_argument("--topk", "--top-k", dest="topk", type=int, default=5, help="Items per meal")
    parser.add_argument("--weekly", action="store_true", help="Print a 7-day meal plan instead of one day")
    parser.add_argument("--days", type=int, default=7, help="Number of days for --weekly, from 1 to 14")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.weekly:
        weekly = recommend_week(
            weight_kg=args.weight,
            height_cm=args.height,
            age=args.age,
            sex=args.sex,
            activity=args.activity,
            dietary_pattern=args.dietary_pattern,
            body_fat_pct=args.body_fat,
            weight_goal=args.weight_goal,
            goal_focus=args.goal_focus,
            avoid_terms=args.avoid,
            preferred_terms=args.prefer,
            top_k=args.topk,
            veg_filter=args.veg,
            days=args.days,
        )
        print("AI Nutritionist recommendation system")
        print(weekly.disclaimer)
        print()
        print(f"Weight goal: {weekly.weight_goal}")
        print(f"Diet: {weekly.dietary_pattern}")
        print("Weekly Mediterranean rotation" if weekly.dietary_pattern == "mediterranean" else "Weekly meal rotation")
        print(
            "Weekly averages -> "
            f"Calories:{weekly.weekly_averages['calories']:.0f} "
            f"P:{weekly.weekly_averages['protein_g']:.1f}g "
            f"Fiber:{weekly.weekly_averages['fiber_g']:.1f}g "
            f"Sodium:{weekly.weekly_averages['sodium_mg']:.0f}mg"
        )
        print(
            "Variety -> "
            f"Poultry days:{weekly.variety_counts['poultry_days']} "
            f"Fish days:{weekly.variety_counts['fish_days']} "
            f"Legume days:{weekly.variety_counts['legume_days']}"
        )
        for day in weekly.days:
            print()
            print(f"{day.day_name} ({day.rotation_focus})")
            _print_daily_result(day.result, include_items=False)
        return 0

    result = recommend(
        weight_kg=args.weight,
        height_cm=args.height,
        age=args.age,
        sex=args.sex,
        activity=args.activity,
        dietary_pattern=args.dietary_pattern,
        body_fat_pct=args.body_fat,
        weight_goal=args.weight_goal,
        goal_focus=args.goal_focus,
        avoid_terms=args.avoid,
        preferred_terms=args.prefer,
        top_k=args.topk,
        veg_filter=args.veg,
    )

    print("AI Nutritionist recommendation system")
    print(result.disclaimer)
    print()
    _print_daily_result(result, body_fat_input=args.body_fat)

    return 0


def _print_daily_result(
    result: RecommendationResult,
    *,
    body_fat_input: float | None = None,
    include_items: bool = True,
) -> None:
    print(result.health_summary)
    print(f"Daily target: {result.daily_targets.calories} kcal | Protein: {result.daily_targets.protein_g:.1f}g")
    print(f"Diet: {result.preferences['dietary_pattern']}")
    print(f"Weight goal: {result.preferences['weight_goal']}")
    if body_fat_input is not None:
        print(f"Body fat: {body_fat_input:.1f}%")
    print(f"Focus: {result.preferences['goal_focus']}")
    if result.preferences["avoid_terms"]:
        print(f"Avoiding: {', '.join(result.preferences['avoid_terms'])}")
    if result.preferences["preferred_terms"]:
        print(f"Preferring: {', '.join(result.preferences['preferred_terms'])}")
    print(
        "Daily totals -> "
        f"Calories:{result.daily_totals['calories']:.0f} "
        f"P:{result.daily_totals['protein_g']:.1f}g "
        f"Fiber:{result.daily_totals['fiber_g']:.1f}g "
        f"Sodium:{result.daily_totals['sodium_mg']:.0f}mg"
    )
    print(
        "Macro split -> "
        f"P:{result.macro_percentages['protein_pct']:.1f}% "
        f"C:{result.macro_percentages['carbohydrate_pct']:.1f}% "
        f"F:{result.macro_percentages['fat_pct']:.1f}%"
    )

    for meal in result.meals:
        print()
        print(f"{meal.name}: {meal.title} ({len(meal.items)} items)")
        if include_items:
            for item in meal.items:
                print(
                    " - "
                    f"{item['food_name']} - "
                    f"{item['calories']:.0f} kcal | "
                    f"P:{item['protein_g']:.1f}g "
                    f"C:{item['carbohydrate_g']:.1f}g "
                    f"Fiber:{item['fiber_g']:.1f}g "
                    f"Sugars:{item['sugars_g']:.1f}g "
                    f"F:{item['fat_g']:.1f}g"
                )
        totals = meal.totals
        print(
            "   Totals -> "
            f"Calories:{totals['calories']:.0f} "
            f"P:{totals['protein_g']:.1f}g "
            f"C:{totals['carbohydrate_g']:.1f}g "
            f"Fiber:{totals['fiber_g']:.1f}g "
            f"Sugars:{totals['sugars_g']:.1f}g "
            f"F:{totals['fat_g']:.1f}g"
        )
        if include_items:
            for explanation in meal.explanations:
                print(f"   Why: {explanation}")


if __name__ == "__main__":
    raise SystemExit(main())
