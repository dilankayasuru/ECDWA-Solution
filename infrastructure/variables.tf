# Variables

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "asu"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "poc"
}

variable "db_username" {
  description = "RDS database admin username"
  type        = string
  default     = "dbadmin"
}

variable "db_password" {
  description = "RDS database admin password"
  type        = string
  default     = "AsuSecureP0C2026!"
  sensitive   = true
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (one per AZ)"
  type        = list(string)
  default     = ["10.0.3.0/24", "10.0.4.0/24"]
}

variable "availability_zones" {
  description = "Availability zones for Multi-AZ deployment"
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b"]
}

variable "alert_email" {
  description = "Email address for SNS alert notifications"
  type        = string
  default     = "admin@aquasense-asu.example.com"
}
