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
  description = "e2-standard-2 (4 vCPU / 8 GB) - required once Lightdash joins the stack (ADR-0003 staged sizing; data-core-only stacks can override to e2-small)"
  type        = string
  default     = "e2-standard-2"
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH (your IP/32)"
  type        = string
}
