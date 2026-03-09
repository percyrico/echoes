variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "google_api_key" {
  description = "Google Gemini API key"
  type        = string
  sensitive   = true
}
