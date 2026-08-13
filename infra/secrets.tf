# The full DATABASE_URL (incl. password) lives in Secrets Manager, injected into the
# container as an env var at runtime — never in the task definition in plaintext.
resource "aws_secretsmanager_secret" "db_url" {
  name                    = "${var.project}-database-url"
  recovery_window_in_days = 0 # allow immediate re-create on destroy/apply cycles
}

resource "aws_secretsmanager_secret_version" "db_url" {
  secret_id = aws_secretsmanager_secret.db_url.id
  secret_string = format(
    "postgresql://%s:%s@%s:5432/%s",
    var.db_username,
    random_password.db.result,
    aws_rds_cluster.aurora.endpoint,
    var.db_name,
  )
}
