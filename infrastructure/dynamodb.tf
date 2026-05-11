# DynamoDB - Telemetry Data (Hot Storage)

resource "aws_dynamodb_table" "telemetry" {
  name         = "${var.project_name}-telemetry-data"
  billing_mode = "PAY_PER_REQUEST" # On-demand - Free Tier compatible
  hash_key     = "meter_id"
  range_key    = "timestamp"

  attribute {
    name = "meter_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  tags = {
    Name        = "${var.project_name}-telemetry-data"
    Environment = var.environment
    Purpose     = "IoT telemetry hot storage"
  }
}
