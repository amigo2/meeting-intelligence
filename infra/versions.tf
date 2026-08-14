terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.region

  # Tag EVERY resource, so cost can be filtered by project in Cost Explorer
  # (cost-to-serve attribution). Activate the "Project" tag in Billing to use it.
  default_tags {
    tags = {
      Project   = "meeting-intelligence"
      ManagedBy = "terraform"
    }
  }
}
