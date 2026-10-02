terraform {
  required_version = ">= 1.5"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.0" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  # Test setup uses local state. For a team, add an S3 backend here.
}

provider "aws" {
  region = var.region

  default_tags {
    tags = { Project = local.name, Environment = "test", ManagedBy = "terraform" }
  }
}
