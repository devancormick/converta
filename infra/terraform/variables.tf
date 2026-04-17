variable "aws_region" {
  default = "us-east-1"
}

variable "environment" {
  description = "staging or prod"
  default     = "staging"
}

variable "db_instance_class" {
  default = "db.t3.medium"
}

variable "db_password" {
  sensitive = true
}

variable "redis_node_type" {
  default = "cache.t3.micro"
}

variable "api_cpu" {
  default = 512
}

variable "api_memory" {
  default = 1024
}

variable "api_desired_count" {
  default = 2
}
