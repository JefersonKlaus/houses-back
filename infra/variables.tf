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

variable "groq_api_key" {
  description = "Groq API key."
  type        = string
  sensitive   = true
}

variable "groq_model" {
  description = "Groq vision model used for receipt extraction."
  type        = string
  default     = "meta-llama/llama-4-scout-17b-16e-instruct"
}

variable "twilio_account_sid" {
  description = "Twilio Account SID."
  type        = string
  sensitive   = true
}

variable "twilio_auth_token" {
  description = "Twilio Auth Token."
  type        = string
  sensitive   = true
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
