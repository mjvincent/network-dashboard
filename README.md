# Network Dashboard

A modern, containerized dashboard for monitoring your home network and connected devices, including your Ubuntu server.

## 🚀 Features

*   **Real-time Network Discovery:** Automatically detects active devices on your network (via Nmap).
*   **Device Status:** Visual indicators for online/offline status and latency.
*   **Ubuntu Server Integration:** Deep-dive metrics including CPU, RAM, Disk, and service status via SSH.
*   **Responsive Interface:** Beautiful, mobile-friendly dashboard built with React and Tailwind CSS.
*   **Dockerized Deployment:** Easy one-command setup on any platform using Docker Compose.

## 🛠️ Tech Stack

*   **Backend:** Python (FastAPI)
*   **Frontend:** React, Tailwind CSS, Shadcn/UI
*   **Orchestration:** Docker, Docker Compose
*   **Networking:** Nmap, Paramiko (SSH)

## 📦 Getting Started

### Prerequisites

*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/mjvincent/network-dashboard.git
    cd network-dashboard
    ```

2.  Create a `.env` file with your credentials (e.g., SSH keys/passwords for your server).

3.  Start the application:
    ```bash
    docker-compose up -d
    ```

4.  Access the dashboard in your browser at `http://localhost:3000`.

## 🔒 Security

This application uses your existing SSH credentials and network scanning capabilities. Always ensure that the `.env` file is kept secure and never committed to version control.