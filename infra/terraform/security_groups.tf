resource "aws_security_group" "alb" {
  name   = "converta-alb-${var.environment}"
  vpc_id = module.vpc.vpc_id
  ingress { from_port = 80;   to_port = 80;   protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  ingress { from_port = 443;  to_port = 443;  protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "api" {
  name   = "converta-api-${var.environment}"
  vpc_id = module.vpc.vpc_id
  ingress { from_port = 8000; to_port = 8000; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
  egress  { from_port = 0;    to_port = 0;    protocol = "-1";  cidr_blocks = ["0.0.0.0/0"] }
}

resource "aws_security_group" "rds" {
  name   = "converta-rds-${var.environment}"
  vpc_id = module.vpc.vpc_id
  ingress { from_port = 5432; to_port = 5432; protocol = "tcp"; security_groups = [aws_security_group.api.id] }
}

resource "aws_security_group" "redis" {
  name   = "converta-redis-${var.environment}"
  vpc_id = module.vpc.vpc_id
  ingress { from_port = 6379; to_port = 6379; protocol = "tcp"; security_groups = [aws_security_group.api.id] }
}
