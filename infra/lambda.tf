locals {
  lambda_package_dir = "${path.module}/.terraform/lambda-package"
  lambda_zip         = "${path.module}/.terraform/lambda.zip"
}

resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements_hash = filebase64sha256("${path.module}/../src/requirements.txt")
    source_hash       = sha256(join("", [for file in fileset("${path.module}/../src", "*.py") : filebase64sha256("${path.module}/../src/${file}")]))
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-NoProfile", "-NonInteractive", "-Command"]
    command = "$ErrorActionPreference = 'Stop'; " +
      "if (Test-Path -LiteralPath '${local.lambda_package_dir}') { Remove-Item -LiteralPath '${local.lambda_package_dir}' -Recurse -Force }; " +
      "New-Item -ItemType Directory -Path '${local.lambda_package_dir}' -Force | Out-Null; " +
      "python -m pip install --disable-pip-version-check -r '${path.module}/../src/requirements.txt' -t '${local.lambda_package_dir}'; " +
      "Copy-Item -Path '${path.module}/../src/*.py' -Destination '${local.lambda_package_dir}' -Force"
  }
}

data "archive_file" "lambda" {
  depends_on  = [null_resource.lambda_dependencies]
  type        = "zip"
  source_dir  = local.lambda_package_dir
  output_path = local.lambda_zip
}

resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "webhook" {
  function_name    = var.project_name
  role             = aws_iam_role.lambda.arn
  handler          = "function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 512
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = {
      GROQ_API_KEY            = var.groq_api_key
      GROQ_MODEL              = var.groq_model
      TWILIO_ACCOUNT_SID      = var.twilio_account_sid
      TWILIO_AUTH_TOKEN       = var.twilio_auth_token
      GOOGLE_SHEET_ID         = var.google_sheet_id
      GOOGLE_CREDENTIALS_JSON = var.google_credentials_json
      GOOGLE_SHEET_WORKSHEET  = var.google_sheet_worksheet
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.webhook.function_name}"
  retention_in_days = 14
}

resource "aws_apigatewayv2_api" "webhook" {
  name          = var.project_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.webhook.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.webhook.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_webhook" {
  api_id    = aws_apigatewayv2_api.webhook.id
  route_key = "GET /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "post_webhook" {
  api_id    = aws_apigatewayv2_api.webhook.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.webhook.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook.execution_arn}/*/*"
}
