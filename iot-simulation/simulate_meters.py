"""
AquaSense Smart Utilities - IoT Smart Meter Simulator
Simulates 30,000+ smart meters sending telemetry data to AWS IoT Core.

For the POC, this script uses the AWS IoT Data Plane (HTTPS) to publish
MQTT messages, which avoids the need for device certificates in testing.

Usage:
    # Install dependencies
    pip install -r requirements.txt

    # Set your IoT endpoint (from terraform output)
    export IOT_ENDPOINT="iot-endpoint.iot.ap-south-1.amazonaws.com"

    # Run simulation (default: 10 meters, 5 readings each)
    python simulate_meters.py

    # Run with custom parameters
    python simulate_meters.py --meters 50 --readings 10 --interval 2

    # Simulate anomalies (for testing alert pipeline)
    python simulate_meters.py --meters 5 --readings 3 --anomaly
"""

import argparse
import json
import random
import time
import sys
from datetime import datetime, timezone

import boto3

# Default IoT Core endpoint (override with --endpoint or IOT_ENDPOINT env var)
DEFAULT_REGION = "ap-south-1"


def generate_normal_reading(meter_id, location):
    # Generate a normal telemetry reading
    return {
        "meter_id": meter_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "water_flow_lph": round(random.uniform(10.0, 200.0), 2),
        "pressure_psi": round(random.uniform(30.0, 70.0), 2),
        "energy_kwh": round(random.uniform(0.5, 15.0), 2),
        "temperature_c": round(random.uniform(20.0, 35.0), 1),
        "battery_pct": random.randint(60, 100),
        "location": location,
        "firmware": "v2.1",
        "signal_strength_dbm": random.randint(-90, -30),
    }


def generate_anomaly_reading(meter_id, location):
    # Generate an anomalous telemetry reading (for testing alerts)
    anomaly_type = random.choice(["low_pressure", "high_pressure", "high_flow"])

    reading = generate_normal_reading(meter_id, location)

    if anomaly_type == "low_pressure":
        reading["pressure_psi"] = round(random.uniform(5.0, 18.0), 2)
        print(f"  [ANOMALY] Low pressure: {reading['pressure_psi']} PSI")
    elif anomaly_type == "high_pressure":
        reading["pressure_psi"] = round(random.uniform(85.0, 120.0), 2)
        print(f"  [ANOMALY] High pressure: {reading['pressure_psi']} PSI")
    elif anomaly_type == "high_flow":
        reading["water_flow_lph"] = round(random.uniform(550.0, 1000.0), 2)
        print(f"  [ANOMALY] High flow: {reading['water_flow_lph']} L/hr")

    return reading


def simulate(args):
    # Run the IoT meter simulation
    iot_client = boto3.client("iot-data", region_name=args.region)

    locations = [
        "mumbai-zone-1", "mumbai-zone-2", "mumbai-zone-3",
        "pune-zone-1", "pune-zone-2",
        "bangalore-zone-1", "bangalore-zone-2",
        "delhi-zone-1", "delhi-zone-2", "delhi-zone-3",
    ]

    print("=" * 60)
    print("AquaSense Smart Meter Simulator")
    print("=" * 60)
    print(f"  Region:   {args.region}")
    print(f"  Meters:   {args.meters}")
    print(f"  Readings: {args.readings} per meter")
    print(f"  Interval: {args.interval}s between readings")
    print(f"  Anomaly:  {'ENABLED' if args.anomaly else 'Disabled'}")
    print(f"  Total messages: {args.meters * args.readings}")
    print("=" * 60)

    total_sent = 0
    total_errors = 0

    for reading_num in range(1, args.readings + 1):
        print(f"\n--- Reading batch {reading_num}/{args.readings} ---")

        for meter_num in range(1, args.meters + 1):
            meter_id = f"asu-water-meter-{meter_num:04d}"
            location = random.choice(locations)
            topic = f"telemetry/water-meter/{meter_id}"

            # Generate reading (anomaly if flag set, ~20% chance)
            if args.anomaly and random.random() < 0.2:
                reading = generate_anomaly_reading(meter_id, location)
            else:
                reading = generate_normal_reading(meter_id, location)

            try:
                iot_client.publish(
                    topic=topic,
                    qos=1,
                    payload=json.dumps(reading),
                )
                total_sent += 1
                print(f"  [{total_sent}] {meter_id} -> {topic} "
                      f"(flow={reading['water_flow_lph']}L/hr, "
                      f"pressure={reading['pressure_psi']}PSI)")

            except Exception as e:
                total_errors += 1
                print(f"  [ERROR] {meter_id}: {e}")

        if reading_num < args.readings:
            print(f"\n  Waiting {args.interval}s before next batch...")
            time.sleep(args.interval)

    print("\n" + "=" * 60)
    print(f"Simulation Complete!")
    print(f"  Total sent:   {total_sent}")
    print(f"  Total errors: {total_errors}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="AquaSense IoT Smart Meter Simulator"
    )
    parser.add_argument(
        "--region", default=DEFAULT_REGION,
        help="AWS region (default: ap-south-1)"
    )
    parser.add_argument(
        "--meters", type=int, default=10,
        help="Number of smart meters to simulate (default: 10)"
    )
    parser.add_argument(
        "--readings", type=int, default=5,
        help="Number of readings per meter (default: 5)"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="Seconds between reading batches (default: 2)"
    )
    parser.add_argument(
        "--anomaly", action="store_true",
        help="Enable anomaly generation (~20%% of readings)"
    )

    args = parser.parse_args()
    simulate(args)


if __name__ == "__main__":
    main()
