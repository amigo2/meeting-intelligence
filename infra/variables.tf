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
