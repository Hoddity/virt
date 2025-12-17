resource "yandex_function_function" "tasks_file_processor" {
  name     = "tasks-file-processor"
  runtime  = "python310"
  entrypoint = "handler.main"
  folder_id = var.folder_id
  memory   = 128

  environment {
    variables = {
      BUCKET_NAME = yandex_storage_bucket.tasks_bucket.name
    }
  }

  resources {
    concurrency = 1
  }

  source_archive_bucket {
    bucket = yandex_storage_bucket.tasks_bucket.name
    object = "functions/tasks_file_processor.zip"
  }
}
