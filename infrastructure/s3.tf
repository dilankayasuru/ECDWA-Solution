# S3 Buckets - Data Lake and Log Archive

# Data Lake Bucket - stores telemetry data for analytics
resource "aws_s3_bucket" "data_lake" {
  bucket        = "${var.project_name}-data-lake-${random_id.suffix.hex}"
  force_destroy = true # Allow terraform destroy to delete non-empty bucket

  tags = {
    Name        = "${var.project_name}-data-lake"
    Environment = var.environment
    Purpose     = "S3 Data Lake for telemetry analytics"
  }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Lifecycle Policy - transition to IA after 30 days (cost optimisation)
resource "aws_s3_bucket_lifecycle_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# Log Archive Bucket - stores CloudWatch and application logs
resource "aws_s3_bucket" "log_archive" {
  bucket        = "${var.project_name}-log-archive-${random_id.suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "${var.project_name}-log-archive"
    Environment = var.environment
    Purpose     = "Log archive storage"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "log_archive" {
  bucket = aws_s3_bucket.log_archive.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
