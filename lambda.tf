locals {
  lambda_package_dir = "${path.module}/.terraform/lambda-package"
  lambda_zip         = "${path.module}/.terraform/lambda.zip"
}

resource "null_resource" "lambda_dependencies" {
  triggers = {
    requirements_hash = filebase64sha256("${path.module}/lambda/requirements.txt")
    source_hash       = sha256(join("", [for file in fileset("${path.module}/lambda", "*.py") : filebase64sha256("${path.module}/lambda/${file}")]))
  }

  provisioner "local-exec" {
    command = "rm -rf '${local.lambda_package_dir}' && mkdir -p '${local.lambda_package_dir}' && python3 -m pip install --disable-pip-version-check -r '${path.module}/lambda/requirements.txt' -t '${local.lambda_package_dir}' && cp '${path.module}'/lambda/*.py '${local.lambda_package_dir}/'"
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
      GEMINI_API_KEY          = var.gemini_api_key
      GEMINI_MODEL            = var.gemini_model
      WHATSAPP_TOKEN          = var.whatsapp_token
      WHATSAPP_VERIFY_TOKEN   = var.whatsapp_verify_token
      WHATSAPP_PHONE_NUMBER_ID = var.whatsapp_phone_number_id
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

