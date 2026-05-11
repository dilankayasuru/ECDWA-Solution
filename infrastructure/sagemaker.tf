# Amazon SageMaker - AI/ML for Anomaly Detection & Demand Forecasting

# SageMaker Execution Role
resource "aws_iam_role" "sagemaker_execution" {
  name = "${var.project_name}-sagemaker-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-sagemaker-execution-role"
  }
}

# S3 access for SageMaker (read/write to data lake)
resource "aws_iam_role_policy" "sagemaker_s3" {
  name = "${var.project_name}-sagemaker-s3-policy"
  role = aws_iam_role.sagemaker_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3DataLakeAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      },
      {
        Sid      = "S3ListBuckets"
        Effect   = "Allow"
        Action   = "s3:ListAllMyBuckets"
        Resource = "*"
      }
    ]
  })
}

# CloudWatch Logs access for SageMaker
resource "aws_iam_role_policy_attachment" "sagemaker_cloudwatch" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# SageMaker full access (needed for notebook to use SageMaker APIs)
resource "aws_iam_role_policy_attachment" "sagemaker_full" {
  role       = aws_iam_role.sagemaker_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# SageMaker Notebook Instance
# Free Tier: ml.t3.medium - 250 hours/month for first 2 months
resource "aws_sagemaker_notebook_instance" "anomaly_detection" {
  name                   = "${var.project_name}-anomaly-detection-nb"
  instance_type          = "ml.t3.medium" # Free Tier eligible
  role_arn               = aws_iam_role.sagemaker_execution.arn
  volume_size            = 5 # GB - minimum to stay cost-effective
  direct_internet_access = "Enabled"

  # Lifecycle config to auto-install dependencies on start
  lifecycle_config_name = aws_sagemaker_notebook_instance_lifecycle_configuration.setup.name

  tags = {
    Name        = "${var.project_name}-anomaly-detection-notebook"
    Environment = var.environment
    Purpose     = "AI-driven anomaly detection and demand forecasting Task 8"
  }
}

# Lifecycle configuration - installs Python libraries on notebook start
resource "aws_sagemaker_notebook_instance_lifecycle_configuration" "setup" {
  name = "${var.project_name}-nb-lifecycle"

  on_start = base64encode(<<-EOF
    #!/bin/bash
    set -e
    sudo -u ec2-user -i <<'USEREOF'
    # Install additional libraries in the default conda env
    source activate python3
    pip install --quiet scikit-learn matplotlib seaborn
    echo "ASU SageMaker setup complete"
    USEREOF
  EOF
  )
}
