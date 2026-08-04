terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

provider "aws" { region = "af-south-1" }

# --- DynamoDB: tickets ---
resource "aws_dynamodb_table" "tickets" {
  name         = "it-support-tickets"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "ticketId"
  attribute { name = "ticketId" type = "S" }
}

# --- S3: runbooks ---
resource "aws_s3_bucket" "runbooks" {
  bucket = "it-support-runbooks-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

# --- IAM: Lambda execution role ---
resource "aws_iam_role" "lambda_role" {
  name = "it-support-lambda-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.tickets.arn
      },
      {
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstanceStatus", "ec2:RebootInstances", "ec2:DescribeSecurityGroups"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:ListAccessKeys", "iam:UpdateAccessKey", "iam:CreateAccessKey"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:StartQuery", "logs:GetQueryResults"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:Retrieve"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "*"
      }
    ]
  })
}

# --- Lambda: action handler ---
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda"
  output_path = "${path.module}/lambda.zip"
}

resource "aws_lambda_function" "action_handler" {
  function_name    = "it-support-action-handler"
  role             = aws_iam_role.lambda_role.arn
  handler          = "action_handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 60
}

# --- IAM: Bedrock agent role ---
resource "aws_iam_role" "bedrock_agent_role" {
  name = "it-support-bedrock-agent-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_agent_policy" {
  role = aws_iam_role.bedrock_agent_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = aws_lambda_function.action_handler.arn
      }
    ]
  })
}

# --- Lambda permission for Bedrock ---
resource "aws_lambda_permission" "bedrock_invoke" {
  statement_id  = "AllowBedrockInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.action_handler.function_name
  principal     = "bedrock.amazonaws.com"
}

output "lambda_arn"          { value = aws_lambda_function.action_handler.arn }
output "bedrock_role_arn"    { value = aws_iam_role.bedrock_agent_role.arn }
output "runbooks_bucket"     { value = aws_s3_bucket.runbooks.bucket }
output "tickets_table"       { value = aws_dynamodb_table.tickets.name }
