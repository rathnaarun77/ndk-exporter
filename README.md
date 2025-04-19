# NDK Exporter
**ndk-exporter** is a Prometheus exporter for monitoring Nutanix Data Services for Kubernetes (NDK). It collects metrics from NDK custom resources and exposes them for Prometheus to scrape.

A pre-configured Grafana dashboard is also provided and can be easily imported for immediate visualization of the collected metrics.

---

## Features

- Exposes metrics for NDK resources like:
  - Application
  - ApplicationSnapshot
  - ApplicationSnapshotRestore
  - ReplicationTarget
  - ApplicationSnapshotReplication
  - Remote
  - JobScheduler
  - ProtectionPlan
  - AppProtectionPlan
- Integration with Prometheus
- Pre-built Grafana dashboard

---

## Deploy

1. Apply the Kubernetes manifest(deploy-exporter.yaml), you can just use the below command to install:

```bash
kubectl apply -f https://raw.githubusercontent.com/rathnaarun77/ndk-exporter/refs/heads/main/deploy-exporter.yaml 
```
2. Import the `NDK_Dashboard.json` file to grafana and choose prometheus as the datasource.

### Grafana Dashboard Previews
![Dashboard Screenshot 1](https://raw.githubusercontent.com/rathnaarun77/ndk-exporter/main/dashboard_screenshot1.jpg)

![Dashboard Screenshot 2](https://raw.githubusercontent.com/rathnaarun77/ndk-exporter/main/dashboard_screenshot2.jpg)

