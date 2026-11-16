variable "aws_region" {
  description = "AWS region where the bot is deployed."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used for AWS resources."
  type        = string
  default     = "houses-receipt-bot"
}

variable "gemini_api_key" {
  description = "Google Gemini API key."
  type        = string
  sensitive   = true
}

variable "whatsapp_token" {
  description = "Meta WhatsApp Cloud API access token."
  type        = string
  sensitive   = true
}

variable "whatsapp_verify_token" {
  description = "Secret token configured in Meta webhook verification."
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp Cloud API phone number ID."
  type        = string
}

variable "google_sheet_id" {
  description = "ID of the Google spreadsheet that receives expenses."
  type        = string
}

variable "google_credentials_json" {
  description = "Google service account credentials as a JSON object."
  type        = string
  sensitive   = true
}

variable "google_sheet_worksheet" {
  description = "Worksheet title. The first worksheet is used when empty."
  type        = string
  default     = ""
}

variable "gemini_model" {
  description = "Gemini model used for receipt extraction."
  type        = string
  default     = "gemini-2.0-flash"
}

