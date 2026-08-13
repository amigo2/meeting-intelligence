# Reuse the account's existing networking + ECS cluster (no new VPC/NAT).
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_ecs_cluster" "shared" {
  cluster_name = var.ecs_cluster_name
}
