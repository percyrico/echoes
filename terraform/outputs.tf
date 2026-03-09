output "service_url" {
  value       = google_cloud_run_v2_service.echoes.uri
  description = "Echoes Cloud Run service URL"
}
