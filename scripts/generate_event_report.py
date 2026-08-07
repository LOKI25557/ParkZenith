"""
ParkZenith Event Analytics Report Generator.
Command line script to query AI Event Analytics and print a detailed report.
"""

import sys
import asyncio
import httpx
import argparse


async def main():
    parser = argparse.ArgumentParser(description="ParkZenith Event Analytics Report Generator")
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8001/events/analytics",
        help="The URL of the Event Analytics endpoint.",
    )
    args = parser.parse_args()

    print(f"[*] Querying AI Event Analytics from {args.url}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(args.url, timeout=10.0)
            if resp.status_code != 200:
                print(f"[-] Failed to retrieve analytics: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
                sys.exit(1)

            data = resp.json()
            print("\n========================================================")
            print("         PARKZENITH AI EVENT-AWARE ANALYTICS REPORT     ")
            print("========================================================\n")
            
            print(f"Average Demand Increase: {data.get('demand_increase_percentage', 0.0)}%")
            print(f"Estimated Recommendation Effectiveness: {data.get('recommendation_effectiveness', 0.0)}%")
            print(f"Forecast Accuracy Improvement (with events): {data.get('forecast_accuracy_improvement', 0.0)}%\n")

            print("--- Most Impactful Events ---")
            for idx, item in enumerate(data.get("most_impactful_events", [])):
                print(f"{idx+1}. {item['name']} ({item['type']})")
                print(f"   Attendance: {item['expected_attendance']} | Impact Score: {item['calculated_impact_score']}")

            print("\n--- Facility Impact Rankings ---")
            for idx, item in enumerate(data.get("facility_impact_ranking", [])):
                print(f"{idx+1}. Facility ID: {item['facility_id']}")
                print(f"   Events Count: {item['events_count']} | Max Extra Demand: {item['max_extra_demand_percentage']}% | Max Congestion: {item['max_congestion_level']}")

            overflow = data.get("predicted_overflow_facilities", [])
            print("\n--- Predicted Facility Overflows ---")
            if not overflow:
                print("No facilities are predicted to overflow under current active events.")
            else:
                for idx, item in enumerate(overflow):
                    print(f"{idx+1}. Facility ID: {item['facility_id']}")
                    print(f"   Base Prediction: {item['base_predicted_occupancy']}% -> Adjusted: {item['adjusted_predicted_occupancy']}%")
                    print(f"   Triggered by: {item['trigger_event_name']}")

            print("\n========================================================\n")

        except Exception as e:
            print(f"[-] Error querying analytics service: {str(e)}", file=sys.stderr)
            print("[-] Hint: Ensure the FastAPI app is running with: python -m uvicorn ai_service.main:app --port 8001", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
