"""
ParkZenith Event Simulation Runner.
Command line script to seed synthetic event scenarios for validation.
"""

import sys
import asyncio
import argparse
from datetime import datetime, timezone

from ai_service.database.session import AsyncSessionFactory
from ai_service.services.event_service import EventIntelligenceService


async def main():
    parser = argparse.ArgumentParser(description="ParkZenith Event Simulation Seeding Script")
    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        choices=[
            "football match",
            "concert",
            "university festival",
            "shopping mall sale",
            "tech conference",
            "airport rush",
            "emergency road closure",
        ],
        help="The event scenario template to run.",
    )
    args = parser.parse_args()

    print(f"[*] Initializing Event Intelligence Service for simulation: '{args.scenario}'...")
    service = EventIntelligenceService()

    async with AsyncSessionFactory() as session:
        try:
            events = await service.run_simulations(session, args.scenario)
            print(f"[+] Simulation '{args.scenario}' executed successfully!")
            for idx, ev in enumerate(events):
                print(f"    - Event {idx+1}: {ev.name} ({ev.type})")
                print(f"      Location: {ev.location_name} (Lat: {ev.latitude}, Lon: {ev.longitude})")
                print(f"      Attendance: {ev.expected_attendance} | Conf: {ev.confidence_score}")
                print(f"      Time: {ev.start_time.isoformat()} to {ev.end_time.isoformat()}")
                print(f"      Impact: Extra Demand: {ev.predicted_extra_demand}%, Congestion: {ev.congestion_multiplier}x")
        except Exception as e:
            print(f"[-] Simulation failed: {str(e)}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    # Ensure correct event loop policy on Windows if needed
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
