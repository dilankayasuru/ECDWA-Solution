# IoT Core - Smart Meter Ingestion

# IoT Thing - represents a smart meter device
resource "aws_iot_thing" "meter_demo" {
  name = "${var.project_name}-water-meter-001"

  attributes = {
    type     = "water-meter"
    location = "mumbai-zone-1"
    firmware = "v2.1"
  }
}

# IoT Policy - least privilege for smart meters (MQTT data plane)
resource "aws_iot_policy" "meter_policy" {
  name = "${var.project_name}-meter-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowConnect"
        Effect   = "Allow"
        Action   = "iot:Connect"
        Resource = "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:client/$${iot:Connection.Thing.ThingName}"
      },
      {
        Sid      = "AllowPublishTelemetry"
        Effect   = "Allow"
        Action   = "iot:Publish"
        Resource = "arn:aws:iot:${var.aws_region}:${data.aws_caller_identity.current.account_id}:topic/telemetry/water-meter/$${iot:Connection.Thing.ThingName}"
      }
    ]
  })
}

# IoT Topic Rule - routes telemetry from MQTT to SQS Queue
resource "aws_iot_topic_rule" "telemetry_to_sqs" {
  name        = "${var.project_name}_telemetry_to_sqs"
  description = "Routes smart meter telemetry to SQS for Lambda processing"
  enabled     = true
  sql         = "SELECT *, topic(3) AS meter_id, timestamp() AS ingestion_time FROM 'telemetry/water-meter/+'"
  sql_version = "2016-03-23"

  sqs {
    queue_url  = aws_sqs_queue.telemetry.id
    role_arn   = aws_iam_role.iot_rule.arn
    use_base64 = false
  }

  # Error action - send to DLQ if SQS fails
  error_action {
    sqs {
      queue_url  = aws_sqs_queue.telemetry_dlq.id
      role_arn   = aws_iam_role.iot_rule.arn
      use_base64 = false
    }
  }

  tags = {
    Name = "${var.project_name}-telemetry-to-sqs"
  }
}
