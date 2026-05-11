# CloudWatch - Monitoring, Dashboards, and Alarms
# CloudWatch is used as Free Tier alternative to OpenSearch and QuickSight

# Log Groups for Lambda Functions
resource "aws_cloudwatch_log_group" "event_processor" {
  name              = "/aws/lambda/${aws_lambda_function.event_processor.function_name}"
  retention_in_days = 7 # Keep logs for 7 days to minimize storage costs

  tags = {
    Name        = "${var.project_name}-event-processor-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "alert_evaluator" {
  name              = "/aws/lambda/${aws_lambda_function.alert_evaluator.function_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-alert-evaluator-logs"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api_handler" {
  name              = "/aws/lambda/${aws_lambda_function.api_handler.function_name}"
  retention_in_days = 7

  tags = {
    Name        = "${var.project_name}-api-handler-logs"
    Environment = var.environment
  }
}

# CloudWatch Alarms

# Alarm: Event Processor Lambda Errors
resource "aws_cloudwatch_metric_alarm" "event_processor_errors" {
  alarm_name          = "${var.project_name}-event-processor-errors"
  alarm_description   = "Alert when Event Processor Lambda has errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.event_processor.function_name
  }

  alarm_actions = [aws_sns_topic.notification_topic.arn]

  tags = {
    Name = "${var.project_name}-event-processor-errors-alarm"
  }
}

# Alarm: SQS DLQ has messages (failed processing)
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-dlq-messages"
  alarm_description   = "Alert when messages land in the Dead Letter Queue"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.telemetry_dlq.name
  }

  alarm_actions = [aws_sns_topic.notification_topic.arn]

  tags = {
    Name = "${var.project_name}-dlq-messages-alarm"
  }
}

# Alarm: API Handler high latency
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "${var.project_name}-api-high-latency"
  alarm_description   = "Alert when API response time exceeds 5 seconds"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 5000
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.api_handler.function_name
  }

  alarm_actions = [aws_sns_topic.notification_topic.arn]

  tags = {
    Name = "${var.project_name}-api-latency-alarm"
  }
}

# CloudWatch Dashboard
# Free Tier alternative to Amazon QuickSight for visualization

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-operations-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "Lambda Invocations"
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.event_processor.function_name, { label = "Event Processor" }],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.alert_evaluator.function_name, { label = "Alert Evaluator" }],
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.api_handler.function_name, { label = "API Handler" }],
          ]
          period = 300
          region = var.aws_region
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "Lambda Errors"
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.event_processor.function_name, { label = "Event Processor Errors", color = "#d62728" }],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.alert_evaluator.function_name, { label = "Alert Evaluator Errors", color = "#ff7f0e" }],
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.api_handler.function_name, { label = "API Handler Errors", color = "#9467bd" }],
          ]
          period = 300
          region = var.aws_region
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "SQS Queue Metrics"
          metrics = [
            ["AWS/SQS", "NumberOfMessagesSent", "QueueName", aws_sqs_queue.telemetry.name, { label = "Messages Sent" }],
            ["AWS/SQS", "NumberOfMessagesReceived", "QueueName", aws_sqs_queue.telemetry.name, { label = "Messages Received" }],
            ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", aws_sqs_queue.telemetry_dlq.name, { label = "DLQ Messages", color = "#d62728" }],
          ]
          period = 300
          region = var.aws_region
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "API Gateway Requests"
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", aws_api_gateway_rest_api.cwp.name, { label = "Total API Requests" }],
            ["AWS/ApiGateway", "4XXError", "ApiName", aws_api_gateway_rest_api.cwp.name, { label = "4XX Errors", color = "#ff7f0e" }],
            ["AWS/ApiGateway", "5XXError", "ApiName", aws_api_gateway_rest_api.cwp.name, { label = "5XX Errors", color = "#d62728" }],
          ]
          period = 300
          region = var.aws_region
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "DynamoDB Read/Write Capacity"
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.telemetry.name, { label = "Read Capacity" }],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", aws_dynamodb_table.telemetry.name, { label = "Write Capacity" }],
          ]
          period = 300
          region = var.aws_region
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 12
        width  = 12
        height = 6
        properties = {
          title = "Lambda Duration (ms)"
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.event_processor.function_name, { label = "Event Processor", stat = "Average" }],
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.api_handler.function_name, { label = "API Handler", stat = "Average" }],
          ]
          period = 300
          region = var.aws_region
        }
      }
    ]
  })
}
