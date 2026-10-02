# No default on purpose: terraform prompts for it on every plan/apply.
# Or pass it: terraform apply -var region=ap-southeast-1
variable "region" {
  description = "AWS region to deploy into (e.g. ap-southeast-1)"
  type        = string
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "data_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.20.0/24", "10.20.21.0/24"]
}

variable "container_cpu" {
  type    = number
  default = 256
}

variable "container_memory" {
  type    = number
  default = 512
}

variable "use_spot" {
  description = "Run Fargate tasks on Spot (cheapest, may be interrupted)"
  type        = bool
  default     = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.micro"
}

variable "github_repo" {
  description = "GitHub repo (owner/name) allowed to deploy through OIDC"
  type        = string
  default     = "ehsanaleemavee/ai-concierge-test"
}

variable "enable_github_oidc" {
  description = "Create the GitHub OIDC provider + deploy role. Set false if the account already has the GitHub OIDC provider."
  type        = bool
  default     = true
}
