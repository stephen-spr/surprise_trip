#!/usr/bin/env python
import sys
from surprise_travel.crew import SurpriseTravelCrew


def run():
    inputs = {
        'origin': 'São Paulo, GRU',
        'destination': 'New York, JFK',
        'age': 31,
        'hotel_location': 'Brooklyn',
        'flight_information': 'GOL 1234, leaving at June 30th, 2024, 10:00',
        'trip_duration': '14 days'
    }
    print("Running crew...")
    result = SurpriseTravelCrew().crew().kickoff(inputs=inputs)
    print("Result:\n", result)


def train():
    inputs = {
        'origin': 'São Paulo, GRU',
        'destination': 'New York, JFK',
        'age': 31,
        'hotel_location': 'Brooklyn',
        'flight_information': 'GOL 1234, leaving at June 30th, 2024, 10:00',
        'trip_duration': '14 days'
    }
    try:
        SurpriseTravelCrew().crew().train(
            n_iterations=int(sys.argv[1]),
            inputs=inputs
        )
    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")


# ✅ ONLY HERE (outside functions)
if __name__ == "__main__":
    print("Starting Surprise Travel App...\n")
    run()
