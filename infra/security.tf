# Least-privilege security groups: ALB open to the world, task only from ALB,
# database only from the task.
resource "aws_security_group" "alb" {
  name   = "${var.project}-alb"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "task" {
  name   = "${var.project}-task"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description     = "App port from the ALB only"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # to Bedrock, ECR, Secrets Manager, Aurora
  }
}

resource "aws_security_group" "db" {
  name   = "${var.project}-db"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from the task only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.task.id]
  }
}
