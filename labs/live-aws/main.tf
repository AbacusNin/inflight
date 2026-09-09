# Inflight Tier-3 live-AWS validation lab.
# Same topology as the emulator lab, but against real AWS: a VPC with an app tier
# reaching a db tier over tcp/5432, so Inflight's live boto3 adapter can be run
# against the real EC2 API. Credentials come from the default chain (aws configure,
# env vars, or SSO); no keys are hardcoded here. Tear this down with
# `terraform destroy` right after the run to keep it to a few cents.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  type    = string
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

# Current Amazon Linux 2023 AMI via the public SSM parameter (the canonical,
# always-valid way to get a bootable AMI on real AWS).
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_vpc" "lab" {
  cidr_block = "10.0.0.0/16"
  tags       = { Name = "inflight-tier3-lab" }
}

resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.lab.id
  cidr_block = "10.0.1.0/24"
  tags       = { Name = "inflight-tier3-lab" }
}

resource "aws_security_group" "app" {
  name   = "inflight-app-tier"
  vpc_id = aws_vpc.lab.id
  tags   = { Name = "inflight-tier3-lab" }
}

resource "aws_security_group" "db" {
  name   = "inflight-db-tier"
  vpc_id = aws_vpc.lab.id
  tags   = { Name = "inflight-tier3-lab" }
}

resource "aws_security_group_rule" "db_from_app" {
  type                     = "ingress"
  security_group_id        = aws_security_group.db.id
  source_security_group_id = aws_security_group.app.id
  protocol                 = "tcp"
  from_port                = 5432
  to_port                  = 5432
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
  tags                   = { Name = "inflight-tier3-lab" }
}

resource "aws_instance" "db" {
  ami                    = data.aws_ssm_parameter.al2023.value
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.db.id]
  tags                   = { Name = "inflight-tier3-lab" }
}

output "vpc_id" {
  value = aws_vpc.lab.id
}
