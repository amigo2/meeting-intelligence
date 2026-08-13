# Container registry: where the backend Docker image is stored for Fargate to pull.
resource "aws_ecr_repository" "app" {
  name                 = var.project
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true # basic vuln scan on every push (SAST-ish, cheap)
  }

  force_delete = true # allow `terraform destroy` to remove it even with images
}

output "ecr_repository_url" {
  value       = aws_ecr_repository.app.repository_url
  description = "Push the backend image here."
}
