"""
AquaSense Smart Utilities - API Handler Lambda
Triggered by API Gateway (REST API).
Provides REST endpoints for the Customer Web Portal:
  GET /health          - Health check
  GET /meters          - List recent telemetry from all meters
  GET /meters/{id}     - Get telemetry for a specific meter
  GET /stats           - Get aggregated statistics
"""

import json
import os
import boto3
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "asu-telemetry-data")


def lambda_handler(event, context):
    # Route API Gateway requests to appropriate handler
    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")
    path_params = event.get("pathParameters") or {}

    try:
        if path == "/health":
            return _response(200, {
                "status": "healthy",
                "service": "AquaSense Smart Utilities API",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0",
            })

        elif path == "/meters" and http_method == "GET":
            return _list_meters(event)

        elif path.startswith("/meters/") and http_method == "GET":
            meter_id = path_params.get("meter_id", path.split("/")[-1])
            return _get_meter(meter_id)

        elif path == "/stats" and http_method == "GET":
            return _get_stats()

        else:
            return _response(404, {"error": "Not Found", "path": path})

    except Exception as e:
        print(f"API Error: {e}")
        return _response(500, {"error": "Internal Server Error", "detail": str(e)})


def _list_meters(event):
    # List recent telemetry data (scan with limit)
    table = dynamodb.Table(TABLE_NAME)
    query_params = event.get("queryStringParameters") or {}
    limit = int(query_params.get("limit", 20))

    result = table.scan(Limit=min(limit, 100))

    items = result.get("Items", [])

    return _response(200, {
        "count": len(items),
        "meters": items,
        "scanned_count": result.get("ScannedCount", 0),
    })


def _get_meter(meter_id):
    # Get telemetry data for a specific meter
    table = dynamodb.Table(TABLE_NAME)

    result = table.query(
        KeyConditionExpression=Key("meter_id").eq(meter_id),
        ScanIndexForward=False,  # Most recent first
        Limit=50,
    )

    items = result.get("Items", [])

    if not items:
        return _response(404, {
            "error": "Meter not found",
            "meter_id": meter_id,
        })

    return _response(200, {
        "meter_id": meter_id,
        "readings_count": len(items),
        "readings": items,
    })


def _get_stats():
    # Get aggregated statistics across all meters
    table = dynamodb.Table(TABLE_NAME)

    result = table.scan(Limit=200)
    items = result.get("Items", [])

    if not items:
        return _response(200, {
            "total_readings": 0,
            "unique_meters": 0,
            "message": "No telemetry data available yet",
        })

    meter_ids = set()
    pressures = []
    flows = []

    for item in items:
        meter_ids.add(item.get("meter_id", ""))
        try:
            pressures.append(float(item.get("pressure_psi", 0)))
        except (ValueError, TypeError):
            pass
        try:
            flows.append(float(item.get("water_flow_lph", 0)))
        except (ValueError, TypeError):
            pass

    return _response(200, {
        "total_readings": len(items),
        "unique_meters": len(meter_ids),
        "pressure_stats": {
            "avg_psi": round(sum(pressures) / len(pressures), 2) if pressures else 0,
            "min_psi": round(min(pressures), 2) if pressures else 0,
            "max_psi": round(max(pressures), 2) if pressures else 0,
        },
        "flow_stats": {
            "avg_lph": round(sum(flows) / len(flows), 2) if flows else 0,
            "min_lph": round(min(flows), 2) if flows else 0,
            "max_lph": round(max(flows), 2) if flows else 0,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })


def _response(status_code, body):
    # Create a standard API Gateway response
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, default=str),
    }
