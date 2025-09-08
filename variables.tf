variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "Default region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Default zone"
  type        = string
  default     = "us-central1-a"
}
