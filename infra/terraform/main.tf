terraform {
  required_version = ">= 1.7"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "converta-terraform-state"
    key    = "converta/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# ── VPC ────────────────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  name    = "converta-${var.environment}"
  cidr    = "10.0.0.0/16"
  azs             = ["${var.aws_region}a", "${var.aws_region}b"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24"]
  enable_nat_gateway = true
  single_nat_gateway = true
}

# ── RDS PostgreSQL ─────────────────────────────────────────────────────────────
resource "aws_db_instance" "postgres" {
  identifier        = "converta-${var.environment}"
  engine            = "postgres"
  engine_version    = "16"
  instance_class    = var.db_instance_class
  allocated_storage = 50
  db_name           = "converta"
  username          = "converta"
  password          = var.db_password
  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  skip_final_snapshot    = var.environment != "prod"
  deletion_protection    = var.environment == "prod"
  backup_retention_period = 7
  storage_encrypted      = true
  tags = local.common_tags
}

resource "aws_db_subnet_group" "main" {
  name       = "converta-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

# ── ElastiCache Redis ──────────────────────────────────────────────────────────
resource "aws_elasticache_cluster" "redis" {
  cluster_id      = "converta-${var.environment}"
  engine          = "redis"
  node_type       = var.redis_node_type
  num_cache_nodes = 1
  port            = 6379
  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]
  tags = local.common_tags
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "converta-${var.environment}"
  subnet_ids = module.vpc.private_subnets
}

# ── S3 Buckets ────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "main" {
  bucket = "llm-msgopt-${var.environment}"
  tags   = local.common_tags
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "converta-${var.environment}"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = local.common_tags
}

resource "aws_ecs_task_definition" "api" {
  family                   = "converta-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "converta-api"
    image     = "${aws_ecr_repository.main.repository_url}:latest"
    essential = true
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "ENVIRONMENT", value = var.environment }
    ]
    secrets = [
      { name = "DATABASE_URL", valueFrom = aws_secretsmanager_secret.db_url.arn },
      { name = "REDIS_URL",    valueFrom = aws_secretsmanager_secret.redis_url.arn },
      { name = "OPENAI_API_KEY", valueFrom = aws_secretsmanager_secret.openai_key.arn }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.api.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "api"
      }
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "converta-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = module.vpc.private_subnets
    security_groups  = [aws_security_group.api.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "converta-api"
    container_port   = 8000
  }

  lifecycle { ignore_changes = [desired_count] }
}

# ── ECR ───────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "main" {
  name                 = "converta"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.common_tags
}

# ── ALB ───────────────────────────────────────────────────────────────────────
resource "aws_lb" "main" {
  name               = "converta-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  subnets            = module.vpc.public_subnets
  security_groups    = [aws_security_group.alb.id]
  tags = local.common_tags
}

resource "aws_lb_target_group" "api" {
  name        = "converta-api-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = module.vpc.vpc_id
  target_type = "ip"
  health_check { path = "/health" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

# ── CloudWatch ────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name              = "/converta/${var.environment}/api"
  retention_in_days = 90
}

# ── Secrets Manager ───────────────────────────────────────────────────────────
resource "aws_secretsmanager_secret" "db_url"    { name = "converta/${var.environment}/database_url" }
resource "aws_secretsmanager_secret" "redis_url" { name = "converta/${var.environment}/redis_url" }
resource "aws_secretsmanager_secret" "openai_key" { name = "converta/${var.environment}/openai_api_key" }

locals {
  common_tags = {
    Project     = "converta"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
