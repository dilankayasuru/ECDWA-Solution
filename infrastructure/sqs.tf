# SQS - Message Queuing for Event-Driven Processing

# Main Telemetry Queue - receives IoT messages from IoT Core Rules Engine
resource "aws_sqs_queue" "telemetry" {
  name                       = "${var.project_name}-telemetry-queue"
  visibility_timeout_seconds = 60    # Must be >= Lambda timeout
  message_retention_seconds  = 86400 # 1 day
  delay_seconds              = 0
  receive_wait_time_seconds  = 10 # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.telemetry_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-telemetry-queue"
    Environment = var.environment
    Purpose     = "IoT telemetry ingestion queue"
  }
}

# Dead Letter Queue - catches unprocessable messages
resource "aws_sqs_queue" "telemetry_dlq" {
  name                      = "${var.project_name}-telemetry-dlq"
  message_retention_seconds = 604800 # 7 days

  tags = {
    Name        = "${var.project_name}-telemetry-dlq"
    Environment = var.environment
    Purpose     = "Dead letter queue for failed telemetry messages"
  }
}
