resource "yandex_monitoring_alert" "tasks_alert" {
  folder_id = var.folder_id
  name      = "High CPU Usage Alert"
  description = "Alert when CPU > 80%"
  condition {
    metric = "compute_instance_cpu_utilization"
    threshold = 0.8
  }
}
