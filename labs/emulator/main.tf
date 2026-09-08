# Inflight AWS-emulator validation lab.
# Provisions a minimal VPC with an app tier reaching a db tier over tcp/5432,
# so Inflight's live boto3 adapter can read a real topology from an emulator.
# Targets a local moto server (no account or token needed), running on
# http://localhost:5001. Terraform provisions it, so the topology doubles as an
# infrastructure-as-code artifact.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    ec2 = "http://localhost:5001"
    sts = "http://localhost:5001"
  }
}

data "aws_ami" "base" {
  most_recent = true
  owners      = ["amazon"]
}

resource "aws_vpc" "lab" {
  cidr_block = "10.0.0.0/16"
  tags       = { Name = "inflight-lab" }
}

resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.lab.id
  cidr_block = "10.0.1.0/24"
}

resource "aws_security_group" "app" {
  name   = "app-tier"
  vpc_id = aws_vpc.lab.id
}

resource "aws_security_group" "db" {
  name   = "db-tier"
  vpc_id = aws_vpc.lab.id
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
  ami                    = data.aws_ami.base.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
  tags                   = { Name = "i-app" }
}

resource "aws_instance" "db" {
  ami                    = data.aws_ami.base.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.db.id]
  tags                   = { Name = "i-db" }
}

output "vpc_id" {
  value = aws_vpc.lab.id
}
