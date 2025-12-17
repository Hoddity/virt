resource "yandex_storage_bucket" "tasks_bucket" {
  name = "tasks-bucket"
  access_key = var.yc_access_key
  secret_key = var.yc_secret_key
  acl      = "private"
}
