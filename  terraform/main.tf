terraform {
  required_providers {
    yandex = {
      source  = "yandex-cloud/yandex"
      version = "0.80.0"
    }
  }
}

provider "yandex" {
  token     = var.yc_token
  cloud_id  = var.cloud_id
  folder_id = var.folder_id
  zone      = "ru-central1-a"
}

resource "yandex_vpc_network" "tasks_network" {
  name = "tasks-network"
}

resource "yandex_vpc_subnet" "tasks_subnet" {
  name           = "tasks-subnet"
  zone           = "ru-central1-a"
  network_id     = yandex_vpc_network.tasks_network.id
  v4_cidr_blocks = ["10.10.0.0/24"]
}

resource "yandex_compute_instance" "backend" {
  name        = "tasks-backend"
  platform_id = "standard-v1"
  resources {
    cores  = 2
    memory = 4
  }
  boot_disk {
    initialize_params {
      image_id = "fd84rmelvcpjp2jpo1gq" # последняя Ubuntu
      size     = 20
    }
  }
  network_interface {
    subnet_id = yandex_vpc_subnet.tasks_subnet.id
    nat       = true
  }
  metadata = {
    ssh-keys = "ubuntu:${file("~/.ssh/id_rsa.pub")}"
  }
}
