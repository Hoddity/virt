resource "yandex_iam_service_account" "tasks_app" {
  name = "tasks-app-sa"
}

resource "yandex_iam_service_account_key" "tasks_app_key" {
  service_account_id = yandex_iam_service_account.tasks_app.id
  description = "Key for tasks app"
}

resource "yandex_iam_role" "tasks_bucket_access" {
  name = "tasks-bucket-access"
  description = "Access to tasks bucket"
  permissions = ["storage.buckets.get", "storage.objects.*"]
}

resource "yandex_iam_service_account_iam_binding" "tasks_bucket_binding" {
  service_account_id = yandex_iam_service_account.tasks_app.id
  role_id = yandex_iam_role.tasks_bucket_access.id
}
