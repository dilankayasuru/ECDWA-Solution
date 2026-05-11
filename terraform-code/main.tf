terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
  alias  = "primary"
}

# 1. Networking : Multi-AZ VPC Design with Public and Private Subnets
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {
    Name        = "asu-main-vpc"
    Environment = "production"
    Project     = "AquaSense Migration"
  }
}

resource "aws_subnet" "public_az1" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-south-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "asu_public_subnet_1"
  }
}

resource "aws_subnet" "private_az1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "ap-south-1a"

  tags = {
    Name = "asu_private_subnet_1"
  }
}

resource "aws_subnet" "private_az2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "ap-south-1b"

  tags = {
    Name = "asu_private_subnet_2"
  }
}

# 2. Security: Network Security Groups using Attachment Resources
resource "aws_security_group" "ecs_sg" {
  name        = "asu-ecs-sg"
  description = "Security group for ECS microservices"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name = "asu_ecs_sg"
  }
}

resource "aws_security_group_rule" "ecs_ingress_https" {
  type              = "ingress"
  description       = "HTTPS inbound from VPC"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = [aws_vpc.main.cidr_block]
  security_group_id = aws_security_group.ecs_sg.id
}

# 3. Compute: ECS Cluster for Microservices (Fargate)
resource "aws_ecs_cluster" "smdp_cluster" {
  name = "asu-smdp-cluster"

  tags = {
    Name       = "asu_smdp_cluster"
    AppPurpose = "iot_telemetry_processing"
  }
}

# 4. Data Storage : Primary Amazon RDS Database
resource "aws_db_subnet_group" "default" {
  name       = "asu-db-subnet-group"
  subnet_ids = [aws_subnet.private_az1.id, aws_subnet.private_az2.id]

  tags = {
    Name = "asu_db_subnet_group"
  }
}

resource "aws_db_instance" "primary" {
  provider               = aws.primary
  allocated_storage      = 20
  engine                 = "postgres"
  instance_class         = "db.t3.micro"
  identifier             = "asu-primary-db"
  db_subnet_group_name   = aws_db_subnet_group.default.name
  vpc_security_group_ids = [aws_security_group.ecs_sg.id]
  skip_final_snapshot    = true

  username = "dbadmin"
  password = "AsuSecurePassword123!"
}
