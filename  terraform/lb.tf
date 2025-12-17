resource "yandex_lb_network_load_balancer" "tasks_lb" {
  name = "tasks-lb"

  listener {
    name = "http-listener"
    port = 80
    target_port = 8000
    external_address_spec {
      ip_version = "IPV4"
      address    = "dynamic"
    }
  }

  attached_target_group {
    target_group_id = yandex_lb_target_group.tasks_backend.id
  }
}

resource "yandex_lb_target_group" "tasks_backend" {
  name = "tasks-backend-tg"

  dynamic "targets" {
    for_each = [yandex_compute_instance.backend.network_interface[0].ip_address]
    content {
      address = targets.value
      subnet_id = yandex_vpc_subnet.tasks_subnet.id
      port     = 8000
      healthcheck {
        name = "http-health"
        http_options {
          port     = 8000
          path     = "/tasks"
          use_http2 = false
        }
      }
    }
  }
}
