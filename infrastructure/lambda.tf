# Lambda Functions + API Gateway
# Lambda is used as Free Tier alternative to ECS Fargate for compute.

# Package Lambda Source Code

data "archive_file" "event_processor" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src/event_processor"
  output_path = "${path.module}/.build/event_processor.zip"
}

data "archive_file" "alert_evaluator" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src/alert_evaluator"
  output_path = "${path.module}/.build/alert_evaluator.zip"
}

data "archive_file" "api_handler" {
  type        = "zip"
  source_dir  = "${path.module}/lambda_src/api_handler"
  output_path = "${path.module}/.build/api_handler.zip"
}

# Lambda Functions

# Event Processor - processes IoT telemetry from SQS
resource "aws_lambda_function" "event_processor" {
  function_name    = "${var.project_name}-event-processor"
  description      = "Processes IoT telemetry data from SQS, writes to DynamoDB and S3"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128
  filename         = data.archive_file.event_processor.output_path
  source_code_hash = data.archive_file.event_processor.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE  = aws_dynamodb_table.telemetry.name
      S3_DATA_LAKE    = aws_s3_bucket.data_lake.id
      EVENT_TOPIC_ARN = aws_sns_topic.event_topic.arn
    }
  }

  tags = {
    Name        = "${var.project_name}-event-processor"
    Environment = var.environment
  }
}

# SQS to Event Processor trigger
resource "aws_lambda_event_source_mapping" "sqs_to_processor" {
  event_source_arn = aws_sqs_queue.telemetry.arn
  function_name    = aws_lambda_function.event_processor.arn
  batch_size       = 10
  enabled          = true
}

# 2. Alert Evaluator - evaluates anomaly events from SNS
resource "aws_lambda_function" "alert_evaluator" {
  function_name    = "${var.project_name}-alert-evaluator"
  description      = "Evaluates anomaly events and sends user notifications"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 128
  filename         = data.archive_file.alert_evaluator.output_path
  source_code_hash = data.archive_file.alert_evaluator.output_base64sha256

  environment {
    variables = {
      NOTIFICATION_TOPIC_ARN = aws_sns_topic.notification_topic.arn
    }
  }

  tags = {
    Name        = "${var.project_name}-alert-evaluator"
    Environment = var.environment
  }
}

# SNS Event Topic → Alert Evaluator subscription
resource "aws_sns_topic_subscription" "event_to_alert_evaluator" {
  topic_arn = aws_sns_topic.event_topic.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.alert_evaluator.arn
}

# Allow SNS to invoke Alert Evaluator
resource "aws_lambda_permission" "sns_invoke_alert" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert_evaluator.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.event_topic.arn
}

# 3. API Handler - REST API for Customer Web Portal
resource "aws_lambda_function" "api_handler" {
  function_name    = "${var.project_name}-api-handler"
  description      = "REST API handler for Customer Web Portal"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "index.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 128
  filename         = data.archive_file.api_handler.output_path
  source_code_hash = data.archive_file.api_handler.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.telemetry.name
    }
  }

  tags = {
    Name        = "${var.project_name}-api-handler"
    Environment = var.environment
  }
}

# API Gateway (REST API)
# Free Tier alternative to ALB

resource "aws_api_gateway_rest_api" "cwp" {
  name        = "${var.project_name}-customer-web-portal-api"
  description = "AquaSense Customer Web Portal REST API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "${var.project_name}-cwp-api"
    Environment = var.environment
  }
}

# /health endpoint
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.cwp.id
  parent_id   = aws_api_gateway_rest_api.cwp.root_resource_id
  path_part   = "health"
}

resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.cwp.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "health_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.cwp.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# /meters endpoint
resource "aws_api_gateway_resource" "meters" {
  rest_api_id = aws_api_gateway_rest_api.cwp.id
  parent_id   = aws_api_gateway_rest_api.cwp.root_resource_id
  path_part   = "meters"
}

resource "aws_api_gateway_method" "meters_get" {
  rest_api_id   = aws_api_gateway_rest_api.cwp.id
  resource_id   = aws_api_gateway_resource.meters.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "meters_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.cwp.id
  resource_id             = aws_api_gateway_resource.meters.id
  http_method             = aws_api_gateway_method.meters_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# /meters/{meter_id} endpoint
resource "aws_api_gateway_resource" "meter_by_id" {
  rest_api_id = aws_api_gateway_rest_api.cwp.id
  parent_id   = aws_api_gateway_resource.meters.id
  path_part   = "{meter_id}"
}

resource "aws_api_gateway_method" "meter_by_id_get" {
  rest_api_id   = aws_api_gateway_rest_api.cwp.id
  resource_id   = aws_api_gateway_resource.meter_by_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "meter_by_id_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.cwp.id
  resource_id             = aws_api_gateway_resource.meter_by_id.id
  http_method             = aws_api_gateway_method.meter_by_id_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# /stats endpoint
resource "aws_api_gateway_resource" "stats" {
  rest_api_id = aws_api_gateway_rest_api.cwp.id
  parent_id   = aws_api_gateway_rest_api.cwp.root_resource_id
  path_part   = "stats"
}

resource "aws_api_gateway_method" "stats_get" {
  rest_api_id   = aws_api_gateway_rest_api.cwp.id
  resource_id   = aws_api_gateway_resource.stats.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "stats_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.cwp.id
  resource_id             = aws_api_gateway_resource.stats.id
  http_method             = aws_api_gateway_method.stats_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "cwp" {
  rest_api_id = aws_api_gateway_rest_api.cwp.id

  depends_on = [
    aws_api_gateway_integration.health_lambda,
    aws_api_gateway_integration.meters_lambda,
    aws_api_gateway_integration.meter_by_id_lambda,
    aws_api_gateway_integration.stats_lambda,
  ]

  # Force redeployment when API changes
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.health.id,
      aws_api_gateway_resource.meters.id,
      aws_api_gateway_resource.meter_by_id.id,
      aws_api_gateway_resource.stats.id,
      aws_api_gateway_method.health_get.id,
      aws_api_gateway_method.meters_get.id,
      aws_api_gateway_method.meter_by_id_get.id,
      aws_api_gateway_method.stats_get.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "poc" {
  deployment_id = aws_api_gateway_deployment.cwp.id
  rest_api_id   = aws_api_gateway_rest_api.cwp.id
  stage_name    = var.environment

  tags = {
    Name        = "${var.project_name}-api-stage"
    Environment = var.environment
  }
}

# Allow API Gateway to invoke the API Handler Lambda
resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.cwp.execution_arn}/*/*"
}
