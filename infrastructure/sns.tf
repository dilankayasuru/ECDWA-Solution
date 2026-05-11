# SNS - Event-Driven Alerting

# Event Topic - receives anomaly events from Event Processor Lambda
resource "aws_sns_topic" "event_topic" {
  name = "${var.project_name}-event-topic"

  tags = {
    Name        = "${var.project_name}-event-topic"
    Environment = var.environment
    Purpose     = "Anomaly event notifications"
  }
}

# Notification Topic - sends final alerts to users/operators
resource "aws_sns_topic" "notification_topic" {
  name = "${var.project_name}-notification-topic"

  tags = {
    Name        = "${var.project_name}-notification-topic"
    Environment = var.environment
    Purpose     = "User-facing alert notifications"
  }
}

# Email subscription for notifications (operator alert)
resource "aws_sns_topic_subscription" "email_alert" {
  topic_arn = aws_sns_topic.notification_topic.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
