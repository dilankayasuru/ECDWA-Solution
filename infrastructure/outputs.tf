# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

# API Gateway
output "api_gateway_url" {
  description = "API Gateway base URL for the Customer Web Portal"
  value       = aws_api_gateway_stage.poc.invoke_url
}

output "api_health_url" {
  description = "API health check endpoint"
  value       = "${aws_api_gateway_stage.poc.invoke_url}/health"
}

output "api_meters_url" {
  description = "API meters listing endpoint"
  value       = "${aws_api_gateway_stage.poc.invoke_url}/meters"
}

output "api_stats_url" {
  description = "API statistics endpoint"
  value       = "${aws_api_gateway_stage.poc.invoke_url}/stats"
}

# IoT Core
output "iot_endpoint" {
  description = "IoT Core endpoint for MQTT connections"
  value       = data.aws_iot_endpoint.current.endpoint_address
}

output "iot_topic_rule" {
  description = "IoT Topic Rule name"
  value       = aws_iot_topic_rule.telemetry_to_sqs.name
}

# Data Stores
output "dynamodb_table_name" {
  description = "DynamoDB telemetry table name"
  value       = aws_dynamodb_table.telemetry.name
}

output "s3_data_lake_bucket" {
  description = "S3 Data Lake bucket name"
  value       = aws_s3_bucket.data_lake.id
}

output "s3_log_archive_bucket" {
  description = "S3 Log Archive bucket name"
  value       = aws_s3_bucket.log_archive.id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.primary.endpoint
}

# SQS
output "sqs_telemetry_queue_url" {
  description = "SQS telemetry queue URL"
  value       = aws_sqs_queue.telemetry.url
}

# SNS
output "sns_event_topic_arn" {
  description = "SNS Event Topic ARN"
  value       = aws_sns_topic.event_topic.arn
}

output "sns_notification_topic_arn" {
  description = "SNS Notification Topic ARN"
  value       = aws_sns_topic.notification_topic.arn
}

# Lambda
output "lambda_event_processor" {
  description = "Event Processor Lambda function name"
  value       = aws_lambda_function.event_processor.function_name
}

output "lambda_alert_evaluator" {
  description = "Alert Evaluator Lambda function name"
  value       = aws_lambda_function.alert_evaluator.function_name
}

output "lambda_api_handler" {
  description = "API Handler Lambda function name"
  value       = aws_lambda_function.api_handler.function_name
}

# CloudWatch
output "cloudwatch_dashboard_url" {
  description = "CloudWatch Dashboard URL"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}

# CloudTrail
output "cloudtrail_bucket" {
  description = "CloudTrail S3 bucket name"
  value       = aws_s3_bucket.cloudtrail.id
}

# SageMaker
output "sagemaker_notebook_url" {
  description = "SageMaker Notebook Instance URL (open in browser)"
  value       = "https://${var.aws_region}.console.aws.amazon.com/sagemaker/home?region=${var.aws_region}#/notebook-instances/${aws_sagemaker_notebook_instance.anomaly_detection.name}"
}

output "sagemaker_notebook_name" {
  description = "SageMaker Notebook Instance name"
  value       = aws_sagemaker_notebook_instance.anomaly_detection.name
}

# IoT Endpoint data source
data "aws_iot_endpoint" "current" {
  endpoint_type = "iot:Data-ATS"
}
