output "api_url" {
  description = "Live API base URL (ALB). Point the frontend here, or curl /health."
  value       = "http://${aws_lb.app.dns_name}"
}

output "aurora_endpoint" {
  description = "Aurora writer endpoint (private)."
  value       = aws_rds_cluster.aurora.endpoint
}
