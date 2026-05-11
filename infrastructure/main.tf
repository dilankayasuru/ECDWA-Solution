# AquaSense Smart Utilities (ASU) - Complete AWS Infrastructure
# Proof of Concept using AWS Free Tier Compatible Services
# Region: ap-south-1 (Mumbai)

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Random suffix for globally unique S3 bucket names
resource "random_id" "suffix" {
  byte_length = 4
}

# Current AWS account ID and region
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
