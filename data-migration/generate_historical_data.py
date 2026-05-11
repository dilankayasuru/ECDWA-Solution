"""
AquaSense Smart Utilities - Historical Data Generator
=====================================================
Simulates the on-premise PostgreSQL database that ASU currently operates.

This script:
  1. Creates the database schema (5 tables: customers, meters, telemetry_readings,
     billing, maintenance_logs)
  2. Generates realistic historical data spanning 90 days for 200 meters
  3. Inserts into a local PostgreSQL database (simulating on-premise infrastructure)
  4. Also exports to CSV files (for migration without DMS)

Prerequisites:
  - Local PostgreSQL installed and running (https://www.postgresql.org/download/)
  - Create a database: createdb aquasense_onprem
  - Install dependencies: pip install -r requirements.txt

Usage:
  # With local PostgreSQL
  python generate_historical_data.py --db-host localhost --db-name aquasense_onprem

  # CSV-only mode (no PostgreSQL needed)
  python generate_historical_data.py --csv-only

  # Custom parameters
  python generate_historical_data.py --meters 200 --days 90 --csv-only
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

# Try importing PostgreSQL driver
try:
    import psycopg2
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

# Try importing Faker for realistic names
try:
    from faker import Faker
    fake = Faker()
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False


# Database Schema
SCHEMA_SQL = """
-- AquaSense Smart Utilities - On-Premise Database Schema
-- This represents the legacy database to be migrated to AWS RDS

CREATE TABLE IF NOT EXISTS customers (
    customer_id     VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    email           VARCHAR(100),
    phone           VARCHAR(20),
    address         VARCHAR(200),
    city            VARCHAR(50),
    zone            VARCHAR(50),
    plan_type       VARCHAR(20) DEFAULT 'standard',
    registered_date DATE NOT NULL,
    status          VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS meters (
    meter_id         VARCHAR(50) PRIMARY KEY,
    meter_type       VARCHAR(20) NOT NULL,
    customer_id      VARCHAR(50) REFERENCES customers(customer_id),
    location         VARCHAR(100),
    zone             VARCHAR(50),
    install_date     DATE NOT NULL,
    firmware_version VARCHAR(10) DEFAULT 'v2.1',
    status           VARCHAR(20) DEFAULT 'active',
    latitude         DECIMAL(10,6),
    longitude        DECIMAL(10,6)
);

CREATE TABLE IF NOT EXISTS telemetry_readings (
    reading_id       SERIAL PRIMARY KEY,
    meter_id         VARCHAR(50) REFERENCES meters(meter_id),
    reading_time     TIMESTAMP NOT NULL,
    water_flow_lph   DECIMAL(10,2),
    pressure_psi     DECIMAL(10,2),
    energy_kwh       DECIMAL(10,2),
    temperature_c    DECIMAL(5,1),
    battery_pct      INTEGER,
    signal_strength  INTEGER,
    is_anomaly       BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS billing (
    bill_id             SERIAL PRIMARY KEY,
    customer_id         VARCHAR(50) REFERENCES customers(customer_id),
    billing_period      VARCHAR(7) NOT NULL,
    total_consumption_l DECIMAL(12,2),
    total_energy_kwh    DECIMAL(10,2),
    amount_usd          DECIMAL(10,2),
    status              VARCHAR(20) DEFAULT 'paid',
    due_date            DATE
);

CREATE TABLE IF NOT EXISTS maintenance_logs (
    log_id              SERIAL PRIMARY KEY,
    meter_id            VARCHAR(50) REFERENCES meters(meter_id),
    maintenance_date    TIMESTAMP NOT NULL,
    maintenance_type    VARCHAR(50),
    description         TEXT,
    technician          VARCHAR(100),
    cost_usd            DECIMAL(10,2),
    status              VARCHAR(20) DEFAULT 'completed'
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_telemetry_meter ON telemetry_readings(meter_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry_readings(reading_time);
CREATE INDEX IF NOT EXISTS idx_billing_customer ON billing(customer_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_meter ON maintenance_logs(meter_id);
"""


# Data Generation
ZONES = [
    "mumbai-zone-1", "mumbai-zone-2", "mumbai-zone-3",
    "pune-zone-1", "pune-zone-2",
    "bangalore-zone-1", "bangalore-zone-2",
    "delhi-zone-1", "delhi-zone-2", "delhi-zone-3",
]

CITIES = {
    "mumbai-zone-1": "Mumbai", "mumbai-zone-2": "Mumbai", "mumbai-zone-3": "Mumbai",
    "pune-zone-1": "Pune", "pune-zone-2": "Pune",
    "bangalore-zone-1": "Bangalore", "bangalore-zone-2": "Bangalore",
    "delhi-zone-1": "Delhi", "delhi-zone-2": "Delhi", "delhi-zone-3": "Delhi",
}

PLANS = ["basic", "standard", "premium", "enterprise"]
METER_TYPES = ["water-meter", "water-meter", "water-meter", "energy-meter", "combo-meter"]
MAINTENANCE_TYPES = [
    "routine-inspection", "battery-replacement", "firmware-update",
    "sensor-calibration", "pipe-repair", "meter-replacement",
]


def _fake_name():
    return fake.name() if HAS_FAKER else f"Customer {random.randint(1000,9999)}"

def _fake_email(name):
    if HAS_FAKER:
        return fake.email()
    return f"{name.lower().replace(' ', '.')}@example.com"

def _fake_phone():
    return fake.phone_number() if HAS_FAKER else f"+91-{random.randint(7000000000, 9999999999)}"

def _fake_address():
    return fake.address().replace("\n", ", ") if HAS_FAKER else f"{random.randint(1,999)} Main Road"


def generate_customers(n_customers):
    # Generate customer records
    customers = []
    for i in range(1, n_customers + 1):
        zone = random.choice(ZONES)
        name = _fake_name()
        customers.append({
            "customer_id": f"CUST-{i:05d}",
            "name": name,
            "email": _fake_email(name),
            "phone": _fake_phone(),
            "address": _fake_address(),
            "city": CITIES[zone],
            "zone": zone,
            "plan_type": random.choice(PLANS),
            "registered_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "status": random.choices(["active", "inactive", "suspended"], weights=[90, 7, 3])[0],
        })
    return customers


def generate_meters(customers, n_meters):
    # Generate meter records linked to customers
    meters = []
    for i in range(1, n_meters + 1):
        customer = random.choice(customers)
        zone = customer["zone"]
        # Coordinates around the city
        base_lat = {"Mumbai": 19.076, "Pune": 18.520, "Bangalore": 12.971, "Delhi": 28.613}
        base_lon = {"Mumbai": 72.877, "Pune": 73.856, "Bangalore": 77.594, "Delhi": 77.209}
        city = CITIES[zone]
        meters.append({
            "meter_id": f"asu-water-meter-{i:04d}",
            "meter_type": random.choice(METER_TYPES),
            "customer_id": customer["customer_id"],
            "location": f"{city} - {zone}",
            "zone": zone,
            "install_date": (datetime(2021, 1, 1) + timedelta(days=random.randint(0, 1200))).strftime("%Y-%m-%d"),
            "firmware_version": random.choice(["v1.8", "v2.0", "v2.1", "v2.2"]),
            "status": random.choices(["active", "maintenance", "offline"], weights=[85, 10, 5])[0],
            "latitude": round(base_lat[city] + random.uniform(-0.1, 0.1), 6),
            "longitude": round(base_lon[city] + random.uniform(-0.1, 0.1), 6),
        })
    return meters


def generate_telemetry(meters, n_days, readings_per_day=4):
    # Generate telemetry readings (every 6 hours by default)
    readings = []
    start_date = datetime(2026, 1, 1)
    hours_step = 24 // readings_per_day

    for meter in meters:
        base_flow = np.random.uniform(50, 150)
        base_pressure = np.random.uniform(40, 60)
        base_energy = np.random.uniform(2, 10)

        for day in range(n_days):
            for reading in range(readings_per_day):
                hour = reading * hours_step
                ts = start_date + timedelta(days=day, hours=hour)

                # Time of day pattern
                hour_factor = 1.0
                if 6 <= hour <= 9:
                    hour_factor = 1.8
                elif 18 <= hour <= 21:
                    hour_factor = 1.5
                elif 0 <= hour <= 5:
                    hour_factor = 0.3

                dow_factor = 1.1 if ts.weekday() >= 5 else 1.0

                flow = base_flow * hour_factor * dow_factor + np.random.normal(0, 10)
                pressure = base_pressure + np.random.normal(0, 3)
                energy = base_energy * hour_factor + np.random.normal(0, 0.5)
                temp = 25 + 5 * np.sin(2 * np.pi * hour / 24) + np.random.normal(0, 1)

                # Inject anomalies (~2%)
                is_anomaly = False
                if np.random.random() < 0.02:
                    is_anomaly = True
                    atype = np.random.choice(["leak", "burst", "overpressure"])
                    if atype == "leak":
                        flow = np.random.uniform(600, 1000)
                    elif atype == "burst":
                        pressure = np.random.uniform(5, 15)
                        flow = np.random.uniform(800, 1500)
                    elif atype == "overpressure":
                        pressure = np.random.uniform(90, 130)

                readings.append({
                    "meter_id": meter["meter_id"],
                    "reading_time": ts.isoformat(),
                    "water_flow_lph": round(max(0, flow), 2),
                    "pressure_psi": round(max(0, pressure), 2),
                    "energy_kwh": round(max(0, energy), 2),
                    "temperature_c": round(temp, 1),
                    "battery_pct": max(0, 100 - day // 10 + random.randint(-5, 5)),
                    "signal_strength": random.randint(-90, -30),
                    "is_anomaly": is_anomaly,
                })
    return readings


def generate_billing(customers, n_months=3):
    """Generate monthly billing records."""
    bills = []
    base_date = datetime(2026, 1, 1)
    for customer in customers:
        for month_offset in range(n_months):
            period_date = base_date + timedelta(days=30 * month_offset)
            period = period_date.strftime("%Y-%m")
            consumption = round(random.uniform(5000, 50000), 2)
            energy = round(random.uniform(100, 1500), 2)
            # Rate: $0.005 per liter + $0.10 per kWh
            amount = round(consumption * 0.005 + energy * 0.10, 2)
            bills.append({
                "customer_id": customer["customer_id"],
                "billing_period": period,
                "total_consumption_l": consumption,
                "total_energy_kwh": energy,
                "amount_usd": amount,
                "status": random.choices(["paid", "pending", "overdue"], weights=[80, 15, 5])[0],
                "due_date": (period_date + timedelta(days=30)).strftime("%Y-%m-%d"),
            })
    return bills


def generate_maintenance(meters, n_days):
    """Generate maintenance log entries (sparse - ~5% of meters get maintenance)."""
    logs = []
    start_date = datetime(2026, 1, 1)
    for meter in meters:
        if random.random() < 0.3:  # 30% of meters have maintenance records
            n_events = random.randint(1, 3)
            for _ in range(n_events):
                mtype = random.choice(MAINTENANCE_TYPES)
                logs.append({
                    "meter_id": meter["meter_id"],
                    "maintenance_date": (start_date + timedelta(days=random.randint(0, n_days))).isoformat(),
                    "maintenance_type": mtype,
                    "description": f"{mtype.replace('-', ' ').title()} for meter {meter['meter_id']} in {meter['zone']}",
                    "technician": _fake_name(),
                    "cost_usd": round(random.uniform(50, 500), 2),
                    "status": random.choices(["completed", "in-progress", "scheduled"], weights=[70, 20, 10])[0],
                })
    return logs


# CSV Export
def export_to_csv(output_dir, customers, meters, telemetry, billing, maintenance):
    """Export all data to CSV files."""
    os.makedirs(output_dir, exist_ok=True)

    datasets = {
        "customers.csv": (customers, ["customer_id", "name", "email", "phone", "address", "city", "zone", "plan_type", "registered_date", "status"]),
        "meters.csv": (meters, ["meter_id", "meter_type", "customer_id", "location", "zone", "install_date", "firmware_version", "status", "latitude", "longitude"]),
        "telemetry_readings.csv": (telemetry, ["meter_id", "reading_time", "water_flow_lph", "pressure_psi", "energy_kwh", "temperature_c", "battery_pct", "signal_strength", "is_anomaly"]),
        "billing.csv": (billing, ["customer_id", "billing_period", "total_consumption_l", "total_energy_kwh", "amount_usd", "status", "due_date"]),
        "maintenance_logs.csv": (maintenance, ["meter_id", "maintenance_date", "maintenance_type", "description", "technician", "cost_usd", "status"]),
    }

    for filename, (data, headers) in datasets.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
        print(f"  Exported {filepath} ({len(data):,} rows)")


# PostgreSQL Insert
def insert_to_postgres(conn, customers, meters, telemetry, billing, maintenance):
    # Insert all data into local PostgreSQL database
    cur = conn.cursor()

    # Create schema
    cur.execute(SCHEMA_SQL)
    conn.commit()
    print("  Schema created successfully")

    # Insert customers
    for c in customers:
        cur.execute(
            "INSERT INTO customers (customer_id, name, email, phone, address, city, zone, plan_type, registered_date, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (customer_id) DO NOTHING",
            (c["customer_id"], c["name"], c["email"], c["phone"], c["address"], c["city"], c["zone"], c["plan_type"], c["registered_date"], c["status"])
        )
    conn.commit()
    print(f"  Inserted {len(customers):,} customers")

    # Insert meters
    for m in meters:
        cur.execute(
            "INSERT INTO meters (meter_id, meter_type, customer_id, location, zone, install_date, firmware_version, status, latitude, longitude) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (meter_id) DO NOTHING",
            (m["meter_id"], m["meter_type"], m["customer_id"], m["location"], m["zone"], m["install_date"], m["firmware_version"], m["status"], m["latitude"], m["longitude"])
        )
    conn.commit()
    print(f"  Inserted {len(meters):,} meters")

    # Insert telemetry in batches
    batch_size = 1000
    for i in range(0, len(telemetry), batch_size):
        batch = telemetry[i:i + batch_size]
        args = [(t["meter_id"], t["reading_time"], t["water_flow_lph"], t["pressure_psi"],
                 t["energy_kwh"], t["temperature_c"], t["battery_pct"], t["signal_strength"],
                 t["is_anomaly"]) for t in batch]
        cur.executemany(
            "INSERT INTO telemetry_readings (meter_id, reading_time, water_flow_lph, pressure_psi, energy_kwh, temperature_c, battery_pct, signal_strength, is_anomaly) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            args
        )
        conn.commit()
    print(f"  Inserted {len(telemetry):,} telemetry readings")

    # Insert billing
    for b in billing:
        cur.execute(
            "INSERT INTO billing (customer_id, billing_period, total_consumption_l, total_energy_kwh, amount_usd, status, due_date) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (b["customer_id"], b["billing_period"], b["total_consumption_l"], b["total_energy_kwh"], b["amount_usd"], b["status"], b["due_date"])
        )
    conn.commit()
    print(f"  Inserted {len(billing):,} billing records")

    # Insert maintenance
    for m in maintenance:
        cur.execute(
            "INSERT INTO maintenance_logs (meter_id, maintenance_date, maintenance_type, description, technician, cost_usd, status) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (m["meter_id"], m["maintenance_date"], m["maintenance_type"], m["description"], m["technician"], m["cost_usd"], m["status"])
        )
    conn.commit()
    print(f"  Inserted {len(maintenance):,} maintenance logs")

    cur.close()


# Main
def main():
    parser = argparse.ArgumentParser(description="AquaSense Historical Data Generator")
    parser.add_argument("--meters", type=int, default=200, help="Number of meters (default: 200)")
    parser.add_argument("--customers", type=int, default=150, help="Number of customers (default: 150)")
    parser.add_argument("--days", type=int, default=90, help="Days of telemetry history (default: 90)")
    parser.add_argument("--csv-only", action="store_true", help="Export to CSV only (no PostgreSQL needed)")
    parser.add_argument("--output-dir", default="exported_data", help="CSV output directory (default: exported_data)")
    parser.add_argument("--db-host", default="localhost", help="PostgreSQL host (default: localhost)")
    parser.add_argument("--db-port", type=int, default=5432, help="PostgreSQL port (default: 5432)")
    parser.add_argument("--db-name", default="aquasense_onprem", help="PostgreSQL database name")
    parser.add_argument("--db-user", default="postgres", help="PostgreSQL username (default: postgres)")
    parser.add_argument("--db-password", default="postgres", help="PostgreSQL password (default: postgres)")

    args = parser.parse_args()
    np.random.seed(42)
    random.seed(42)

    print("=" * 60)
    print("AquaSense Smart Utilities - Historical Data Generator")
    print("=" * 60)
    print(f"  Customers:  {args.customers}")
    print(f"  Meters:     {args.meters}")
    print(f"  Days:       {args.days}")
    print(f"  Readings:   {args.meters * args.days * 4:,} (4 per day per meter)")
    print(f"  Mode:       {'CSV only' if args.csv_only else 'PostgreSQL + CSV'}")
    print("=" * 60)

    # Generate data
    print("\n[1/5] Generating customers...")
    customers = generate_customers(args.customers)

    print("[2/5] Generating meters...")
    meters = generate_meters(customers, args.meters)

    print("[3/5] Generating telemetry readings (this may take a moment)...")
    telemetry = generate_telemetry(meters, args.days, readings_per_day=4)

    print("[4/5] Generating billing records...")
    billing = generate_billing(customers, n_months=3)

    print("[5/5] Generating maintenance logs...")
    maintenance = generate_maintenance(meters, args.days)

    # Summary
    anomaly_count = sum(1 for t in telemetry if t["is_anomaly"])
    print(f"\n  Total records generated:")
    print(f"    Customers:      {len(customers):,}")
    print(f"    Meters:         {len(meters):,}")
    print(f"    Telemetry:      {len(telemetry):,} ({anomaly_count} anomalies)")
    print(f"    Billing:        {len(billing):,}")
    print(f"    Maintenance:    {len(maintenance):,}")

    # Export to CSV (always)
    print(f"\nExporting to CSV ({args.output_dir}/)...")
    export_to_csv(args.output_dir, customers, meters, telemetry, billing, maintenance)

    # Insert into PostgreSQL (unless --csv-only)
    if not args.csv_only:
        if not HAS_PSYCOPG2:
            print("\npsycopg2 not installed. Install: pip install psycopg2-binary")
            print("Falling back to CSV-only mode.")
        else:
            print(f"\nConnecting to PostgreSQL ({args.db_host}:{args.db_port}/{args.db_name})...")
            try:
                conn = psycopg2.connect(
                    host=args.db_host, port=args.db_port,
                    dbname=args.db_name, user=args.db_user,
                    password=args.db_password,
                )
                print("  Connected successfully!")
                insert_to_postgres(conn, customers, meters, telemetry, billing, maintenance)
                conn.close()
                print("  PostgreSQL insertion complete ✅")
            except psycopg2.OperationalError as e:
                print(f"\nPostgreSQL connection failed: {e}")
                print("Make sure PostgreSQL is running and the database exists:")
                print(f"createdb {args.db_name}")
                print("Or use --csv-only flag to skip PostgreSQL.")

    print("\n" + "=" * 60)
    print("Data generation complete!")
    print(f"CSV files are in: {os.path.abspath(args.output_dir)}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
