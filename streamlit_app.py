import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import streamlit as st


def _bootstrap_pythonpath() -> None:
    """Ensure `src` is importable when running `streamlit run` directly."""
    project_root = Path(__file__).resolve().parent
    src_path = project_root / "src"
    if src_path.exists() and str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))


_bootstrap_pythonpath()

from surprise_travel.crew import SurpriseTravelCrew


def _prefill_templates() -> dict[str, dict[str, Any]]:
    def flight_info(
        airline_code: str,
        departure_in_days: int,
        departure_hour: int,
        departure_minute: int,
        duration_hours: int,
        duration_minutes: int,
    ) -> str:
        departure_dt = (
            datetime.now()
            + timedelta(days=departure_in_days)
        ).replace(hour=departure_hour, minute=departure_minute, second=0, microsecond=0)
        arrival_dt = departure_dt + timedelta(
            hours=duration_hours, minutes=duration_minutes
        )
        date_fmt = "%b %d, %Y %H:%M"
        return (
            f"{airline_code} | Departure: {departure_dt.strftime(date_fmt)} | "
            f"Arrival: {arrival_dt.strftime(date_fmt)}"
        )

    return {
        "Classic NYC (2 weeks)": {
            "origin": "Sao Paulo, GRU",
            "destination": "New York, JFK",
            "age": 31,
            "hotel_location": "Brooklyn",
            "flight_information": flight_info("GOL 1234", 30, 10, 0, 8, 45),
            "trip_duration": "14 days",
        },
        "Tokyo Explorer (1 week)": {
            "origin": "Bengaluru, BLR",
            "destination": "Tokyo, HND",
            "age": 29,
            "hotel_location": "Shinjuku",
            "flight_information": flight_info(
                "Japan Airlines JL754", 45, 23, 15, 8, 15
            ),
            "trip_duration": "7 days",
        },
        "Paris Quick Trip (4 days)": {
            "origin": "Chennai, MAA",
            "destination": "Paris, CDG",
            "age": 34,
            "hotel_location": "Le Marais",
            "flight_information": flight_info("Air France AF129", 20, 1, 55, 10, 25),
            "trip_duration": "4 days",
        },
    }


def _extract_itinerary_dict(result: object) -> dict[str, Any] | None:
    """Normalize CrewAI result objects into a dictionary."""
    json_dict = getattr(result, "json_dict", None)
    if isinstance(json_dict, dict):
        return json_dict

    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and hasattr(pydantic_obj, "model_dump"):
        dumped = pydantic_obj.model_dump()
        if isinstance(dumped, dict):
            return dumped

    raw = getattr(result, "raw", None)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None

    return None


def _format_rating(rating: Any) -> str:
    if rating is None:
        return "NA"
    try:
        return f"{float(rating):.1f} / 5"
    except (TypeError, ValueError):
        return str(rating)


def _render_structured_itinerary(itinerary: dict[str, Any]) -> None:
    itinerary_name = itinerary.get("name", "Surprise Trip Itinerary")
    hotel = itinerary.get("hotel", "No hotel details provided.")
    day_plans = itinerary.get("day_plans", [])
    if not isinstance(day_plans, list):
        day_plans = []

    total_activities = sum(
        len(day.get("activities", []))
        for day in day_plans
        if isinstance(day, dict) and isinstance(day.get("activities", []), list)
    )
    ratings: list[float] = []
    for day in day_plans:
        if not isinstance(day, dict):
            continue
        for activity in day.get("activities", []):
            if isinstance(activity, dict) and isinstance(activity.get("rating"), (int, float)):
                ratings.append(float(activity["rating"]))
    avg_rating = sum(ratings) / len(ratings) if ratings else None

    st.markdown(f"## {itinerary_name}")
    st.info(hotel)

    m1, m2, m3 = st.columns(3)
    m1.metric("Days Planned", len(day_plans))
    m2.metric("Activities", total_activities)
    m3.metric("Average Rating", f"{avg_rating:.1f}" if avg_rating is not None else "NA")

    st.markdown("### Day-wise Plan")
    for idx, day in enumerate(day_plans, start=1):
        if not isinstance(day, dict):
            continue

        date = day.get("date", f"Day {idx}")
        activities = day.get("activities", [])
        restaurants = day.get("restaurants", [])
        flight = day.get("flight")

        header = f"Day {idx}: {date}"
        if isinstance(activities, list):
            header += f" ({len(activities)} activities)"

        with st.expander(header, expanded=(idx <= 2)):
            if flight:
                st.markdown(f"**Flight:** {flight}")

            if isinstance(activities, list) and activities:
                for act_idx, activity in enumerate(activities, start=1):
                    if not isinstance(activity, dict):
                        continue
                    title = activity.get("name", f"Activity {act_idx}")
                    st.markdown(f"#### {act_idx}. {title}")
                    st.markdown(f"**Location:** {activity.get('location', 'NA')}")
                    st.markdown(f"**Description:** {activity.get('description', 'NA')}")
                    st.markdown(
                        f"**Why suitable:** {activity.get('why_its_suitable', 'NA')}"
                    )
                    st.markdown(f"**Cuisine:** {activity.get('cousine', 'NA')}")
                    st.markdown(f"**Rating:** {_format_rating(activity.get('rating'))}")

                    reviews = activity.get("reviews", [])
                    if isinstance(reviews, list) and reviews:
                        with st.container():
                            st.markdown("**Reviews**")
                            for review in reviews:
                                st.markdown(f"- {review}")
                    st.divider()
            else:
                st.caption("No activities listed for this day.")

            if isinstance(restaurants, list) and restaurants:
                st.markdown("**Restaurants**")
                for restaurant in restaurants:
                    st.markdown(f"- {restaurant}")


def _render_result(result: object) -> None:
    st.subheader("Generated Itinerary")
    itinerary_dict = _extract_itinerary_dict(result)

    if itinerary_dict:
        tab_readable, tab_json = st.tabs(["Readable View", "Raw JSON"])
        with tab_readable:
            _render_structured_itinerary(itinerary_dict)
        with tab_json:
            st.json(itinerary_dict)
    else:
        st.warning("Could not parse structured itinerary. Showing raw result below.")
        raw = getattr(result, "raw", None)
        if raw:
            st.code(str(raw), language="markdown")
        else:
            st.code(str(result), language="markdown")


def _run_crew(inputs: dict) -> None:
    with st.spinner("Running surprise trip agent flow..."):
        result = SurpriseTravelCrew().crew().kickoff(inputs=inputs)
    _render_result(result)


def _train_crew(inputs: dict, iterations: int) -> None:
    with st.spinner(f"Training crew for {iterations} iterations..."):
        train_result = SurpriseTravelCrew().crew().train(
            n_iterations=iterations, inputs=inputs
        )

    st.success("Training completed.")
    if train_result is not None:
        st.subheader("Training Output")
        try:
            st.code(json.dumps(train_result, indent=2), language="json")
        except TypeError:
            st.code(str(train_result))


def main() -> None:
    st.set_page_config(page_title="Surprise Trip Agent UI", page_icon=":airplane:")
    st.title("Surprise Trip Agent Flow")
    st.caption("Run and train the CrewAI-based travel planning flow from a web UI.")

    st.info(
        "Before running, make sure required environment variables are set "
        "(for example OPENAI keys and tool-specific keys)."
    )

    templates = _prefill_templates()
    selected_template = st.selectbox(
        "Prefilled Trip Template",
        options=list(templates.keys()),
        index=0,
        help="Choose a template to auto-fill the form with realistic sample data.",
    )
    defaults = templates[selected_template]

    with st.form("agent_flow_form"):
        input_col, runtime_col = st.columns([2, 1])
        with input_col:
            origin = st.text_input(
                "Origin",
                value=defaults["origin"],
                help="City and airport code, e.g. Bengaluru, BLR",
            )
            destination = st.text_input(
                "Destination",
                value=defaults["destination"],
                help="City and airport code, e.g. Tokyo, HND",
            )
            age = st.number_input(
                "Traveler Age",
                min_value=1,
                max_value=120,
                value=int(defaults["age"]),
            )
            hotel_location = st.text_input(
                "Preferred Hotel Location",
                value=defaults["hotel_location"],
                help="Neighborhood or area preference, e.g. Shinjuku",
            )
            flight_information = st.text_area(
                "Flight Information",
                value=defaults["flight_information"],
                help="Include flight number and times to help planning around travel windows.",
            )
            trip_duration = st.text_input(
                "Trip Duration",
                value=defaults["trip_duration"],
                help="Examples: 4 days, 1 week, 10 days",
            )
        with runtime_col:
            st.markdown("### Actions")
            iterations = st.number_input(
                "Training Iterations",
                min_value=1,
                max_value=100,
                value=5,
                help="Used only when you click 'Train Crew'.",
            )
            run_clicked = st.form_submit_button("Run Agent Flow", use_container_width=True)
            train_clicked = st.form_submit_button("Train Crew", use_container_width=True)

    inputs = {
        "origin": origin,
        "destination": destination,
        "age": int(age),
        "hotel_location": hotel_location,
        "flight_information": flight_information,
        "trip_duration": trip_duration,
    }

    if run_clicked:
        try:
            _run_crew(inputs)
        except Exception as exc:
            st.error(f"Failed to run crew: {exc}")

    if train_clicked:
        try:
            _train_crew(inputs, int(iterations))
        except Exception as exc:
            st.error(f"Failed to train crew: {exc}")


if __name__ == "__main__":
    main()
