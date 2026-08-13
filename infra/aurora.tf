# Aurora PostgreSQL Serverless v2 (scales down when idle) with pgvector.
# The app runs CREATE EXTENSION vector on startup (init_db).
resource "random_password" "db" {
  length  = 24
  special = false # keep it URL-safe for the DATABASE_URL
}

resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project}-aurora"
  subnet_ids = data.aws_subnets.default.ids
}

resource "aws_rds_cluster" "aurora" {
  cluster_identifier     = "${var.project}-aurora"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"
  engine_version         = var.aurora_engine_version
  database_name          = var.db_name
  master_username        = var.db_username
  master_password        = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5 # scales down when idle to keep cost low
    max_capacity = 2.0
  }
}

resource "aws_rds_cluster_instance" "aurora" {
  cluster_identifier  = aws_rds_cluster.aurora.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.aurora.engine
  engine_version      = aws_rds_cluster.aurora.engine_version
  publicly_accessible = false
}
