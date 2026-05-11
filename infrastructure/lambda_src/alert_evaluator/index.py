"""
AquaSense Smart Utilities - Alert Evaluator Lambda
Triggered by SNS (Event Topic).
Evaluates anomaly events and publishes final notifications.
"""

import json
import os
import boto3
from datetime import datetime, timezone

sns = boto3.client("sns")

NOTIFICATION_TOPIC_ARN = os.environ.get("NOTIFICATION_TOPIC_ARN", "")

# Severity levels based on anomaly type
SEVERITY_MAP = {
    "Low pressure": "CRITICAL",
    "High pressure": "WARNING",
    "High flow rate": "CRITICAL",
}


def lambda_handler(event, context):
    """Evaluate anomaly events and send user notifications."""
    notifications_sent = 0

    for record in event.get("Records", []):
        try:
            # Parse SNS message
            sns_message = record.get("Sns", {})
            message_body = json.loads(sns_message.get("Message", "{}"))

            meter_id = message_body.get("meter_id", "unknown")
            reasons = message_body.get("reasons", [])
            timestamp = message_body.get("timestamp", "N/A")

            # Determine highest severity
            severity = "INFO"
            for reason in reasons:
                for key, sev in SEVERITY_MAP.items():
                    if key in reason:
                        if sev == "CRITICAL":
                            severity = "CRITICAL"
                        elif sev == "WARNING" and severity != "CRITICAL":
                            severity = "WARNING"

            # Build notification message
            notification = {
                "alert_id": f"ALT-{meter_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
                "severity": severity,
                "meter_id": meter_id,
                "timestamp": timestamp,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "issues": reasons,
                "recommended_action": _get_recommendation(severity),
            }

            # Publish to Notification Topic
            if NOTIFICATION_TOPIC_ARN:
                sns.publish(
                    TopicArn=NOTIFICATION_TOPIC_ARN,
                    Subject=f"[{severity}] AquaSense Alert - Meter {meter_id}",
                    Message=json.dumps(notification, indent=2),
                )
                notifications_sent += 1

            print(f"Alert evaluated: meter={meter_id}, severity={severity}")

        except Exception as e:
            print(f"Error evaluating alert: {e}")
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Alerts evaluated",
            "notifications_sent": notifications_sent,
        }),
    }


def _get_recommendation(severity):
    # Return recommended action based on severity
    if severity == "CRITICAL":
        return (
            "Immediate inspection required. Dispatch field team to meter location. "
            "Possible pipe burst or major leak detected."
        )
    elif severity == "WARNING":
        return (
            "Schedule inspection within 24 hours. "
            "Elevated pressure detected - monitor for escalation."
        )
    return "No immediate action required. Continue monitoring."
