output "instance_ip" {
  value = google_compute_address.jmea.address
}

output "backup_bucket" {
  value = google_storage_bucket.backups.name
}
