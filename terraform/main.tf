terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

# Single Cloud Run service (backend + frontend combined)
resource "google_cloud_run_v2_service" "echoes" {
  name     = "echoes"
  location = var.region

  template {
    containers {
      image = "gcr.io/${var.project_id}/echoes:latest"

      ports {
        container_port = 8000
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "GOOGLE_API_KEY"
        value = var.google_api_key
      }

      # Minimal resources for cost savings
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    # Minimal cost: scale to zero, max 1 instance
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    timeout = "300s"
  }

  depends_on = [google_project_service.run]
}

# Make service publicly accessible
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.echoes.name
  location = var.region
  role     = "roles/run.invoker"
  member   = "allUsers"
}
