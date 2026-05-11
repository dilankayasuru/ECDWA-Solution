# RDS PostgreSQL - Customer Data (Free Tier Alternative to Aurora)
# Aurora is not Free Tier eligible. RDS PostgreSQL provides equivalent

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "primary" {
  identifier     = "${var.project_name}-primary-db"
  engine         = "postgres"
  engine_version = "15"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp2"
  storage_encrypted = true

  db_name  = "aquasense"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Free Tier - Single-AZ (Multi-AZ costs extra)
  multi_az            = false
  publicly_accessible = false
  skip_final_snapshot = true

  backup_retention_period = 0
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  tags = {
    Name        = "${var.project_name}-primary-db"
    Environment = var.environment
    Purpose     = "Customer data - Free Tier alternative to Aurora"
  }
}
