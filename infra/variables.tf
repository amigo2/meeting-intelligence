variable "project" {
  description = "Project name, used to prefix AWS resources."
  type        = string
  default     = "meeting-intelligence"
}

variable "region" {
  description = "AWS region (London for UK/EU data residency)."
  type        = string
  default     = "eu-west-2"
}

variable "ecs_cluster_name" {
  description = "Existing ECS cluster to deploy into (reused from the account)."
  type        = string
  default     = "alameda-prod-cluster"
}

variable "db_name" {
  type    = string
  default = "meetings"
}

variable "db_username" {
  type    = string
  default = "meetings"
}

variable "aurora_engine_version" {
  type    = string
  default = "16.11"
}

variable "bedrock_llm_model_id" {
  type    = string
  default = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
}

variable "bedrock_embed_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}
