"""
AquaSense Smart Utilities - Event Processor Lambda
Triggered by SQS (IoT telemetry queue).
Processes smart meter telemetry data:
  1. Writes to DynamoDB (hot storage)
  2. Writes to S3 Data Lake (analytics)
  3. Publishes anomaly events to SNS if thresholds are breached
"""

import json
import os
import boto3
from datetime import datetime, timezone

# AWS clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
sns = boto3.client("sns")

# Environment variables
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "asu-telemetry-data")
BUCKET_NAME = os.environ.get("S3_DATA_LAKE", "asu-data-lake")
EVENT_TOPIC_ARN = os.environ.get("EVENT_TOPIC_ARN", "")

# Anomaly thresholds
PRESSURE_LOW_THRESHOLD = 20.0   # PSI - potential pipe burst
PRESSURE_HIGH_THRESHOLD = 80.0  # PSI - overpressure
FLOW_HIGH_THRESHOLD = 500.0     # L/hr - potential leak


def lambda_handler(event, context):
    # Process SQS messages containing IoT telemetry data
    table = dynamodb.Table(TABLE_NAME)
    processed = 0
    anomalies = 0

    for record in event.get("Records", []):
        try:
            # Parse the SQS message body (IoT Core forwards JSON)
            body = json.loads(record["body"])

            meter_id = body.get("meter_id", "unknown")
            timestamp = body.get("ingestion_time",
                                 datetime.now(timezone.utc).isoformat())

            # Build telemetry record
            telemetry = {
                "meter_id": str(meter_id),
                "timestamp": str(timestamp),
                "water_flow_lph": str(body.get("water_flow_lph", 0)),
                "pressure_psi": str(body.get("pressure_psi", 0)),
                "energy_kwh": str(body.get("energy_kwh", 0)),
                "temperature_c": str(body.get("temperature_c", 0)),
                "battery_pct": str(body.get("battery_pct", 100)),
                "location": body.get("location", "unknown"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }

            # 1. Write to DynamoDB (hot storage)
            table.put_item(Item=telemetry)

            # 2. Write to S3 Data Lake (analytics / cold storage)
            now = datetime.now(timezone.utc)
            s3_key = (
                f"telemetry/{now.year}/{now.month:02d}/{now.day:02d}/"
                f"{meter_id}/{timestamp}.json"
            )
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=s3_key,
                Body=json.dumps(body),
                ContentType="application/json",
            )

            # 3. Check for anomalies
            pressure = float(body.get("pressure_psi", 50))
            flow = float(body.get("water_flow_lph", 0))

            is_anomaly = False
            anomaly_reasons = []

            if pressure < PRESSURE_LOW_THRESHOLD:
                is_anomaly = True
                anomaly_reasons.append(
                    f"Low pressure: {pressure} PSI (threshold: {PRESSURE_LOW_THRESHOLD})"
                )
            if pressure > PRESSURE_HIGH_THRESHOLD:
                is_anomaly = True
                anomaly_reasons.append(
                    f"High pressure: {pressure} PSI (threshold: {PRESSURE_HIGH_THRESHOLD})"
                )
            if flow > FLOW_HIGH_THRESHOLD:
                is_anomaly = True
                anomaly_reasons.append(
                    f"High flow rate: {flow} L/hr (threshold: {FLOW_HIGH_THRESHOLD})"
                )

            if is_anomaly and EVENT_TOPIC_ARN:
                anomaly_event = {
                    "event_type": "ANOMALY_DETECTED",
                    "meter_id": meter_id,
                    "timestamp": timestamp,
                    "reasons": anomaly_reasons,
                    "raw_data": body,
                }
                sns.publish(
                    TopicArn=EVENT_TOPIC_ARN,
                    Subject=f"[ASU Alert] Anomaly detected - Meter {meter_id}",
                    Message=json.dumps(anomaly_event, indent=2),
                )
                anomalies += 1

            processed += 1

        except Exception as e:
            print(f"Error processing record: {e}")
            # SQS will retry based on redrive policy
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Telemetry processed",
            "processed": processed,
            "anomalies_detected": anomalies,
        }),
    }
