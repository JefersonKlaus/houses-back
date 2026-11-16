output "webhook_url" {
  description = "URL to configure as the Meta WhatsApp webhook callback."
  value       = "${aws_apigatewayv2_api.webhook.api_endpoint}/webhook"
}

