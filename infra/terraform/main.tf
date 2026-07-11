terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

resource "google_compute_address" "jmea" {
  name = "jmea-platform-ip"
}

resource "google_storage_bucket" "backups" {
  name                        = "${var.project_id}-jmea-backups"
  location                    = var.region
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_service_account" "jmea_vm" {
  account_id   = "jmea-platform-vm"
  display_name = "JMEA platform VM"
}

resource "google_storage_bucket_iam_member" "backup_writer" {
  bucket = google_storage_bucket.backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.jmea_vm.email}"
}

resource "google_compute_firewall" "ssh" {
  name    = "jmea-allow-ssh"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = [var.admin_cidr]
  target_tags   = ["jmea-platform"]
}

resource "google_compute_instance" "jmea" {
  name         = "jmea-platform"
  machine_type = var.machine_type
  tags         = ["jmea-platform"]

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 30
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.jmea.address
    }
  }

  service_account {
    email  = google_service_account.jmea_vm.email
    scopes = ["cloud-platform"]
  }

  metadata_startup_script = templatefile("${path.module}/startup.sh.tftpl", {
    backup_bucket = google_storage_bucket.backups.name
  })
}
