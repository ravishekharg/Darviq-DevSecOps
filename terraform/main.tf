# Sample Terraform for Checkov IaC scanning demo

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
}

# Secure S3 bucket — passes Checkov
resource "aws_s3_bucket" "app_assets" {
  bucket = "devsecops-app-assets"
  tags   = { Environment = "prod", ManagedBy = "terraform" }
}

resource "aws_s3_bucket_versioning" "app_assets" {
  bucket = aws_s3_bucket.app_assets.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "app_assets" {
  bucket = aws_s3_bucket.app_assets.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "app_assets" {
  bucket                  = aws_s3_bucket.app_assets.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "app_assets" {
  bucket        = aws_s3_bucket.app_assets.id
  target_bucket = aws_s3_bucket.app_assets.id
  target_prefix = "access-logs/"
}