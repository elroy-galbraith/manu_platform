variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region (us-east1 satisfies the DPA posture in strawman §6)"
  type        = string
  default     = "us-east1"
}

variable "zone" {
  type    = string
  default = "us-east1-b"
}

variable "machine_type" {
  description = "e2-small for the data core; move to e2-standard-2 when the full stack lands (ADR-0003)"
  type        = string
  default     = "e2-small"
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH (your IP/32)"
  type        = string
}
