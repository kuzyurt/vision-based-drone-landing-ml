# Manual background services — 25 October 2026

The drone collector uses native Windows Python/MuJoCo/Node and does not need these services.

Completed:
- Disabled PI WSL Watchdog (previously every five minutes).
- Disabled WSL KeepAlive (previously at login).
- Disabled KuzGen Docker Trash Cleanup (custom scheduled housekeeping).
- Docker startup was already disabled; all four containers now use restart=no.
- Stopped the four containers, Docker Desktop, pi-web services and all WSL distributions.
- Turned off NVIDIA Overlay through NVIDIA App and verified its processes exited.
- Left graphics driver services and Freebuff running.
- No containers, volumes, Linux distributions or project data were deleted.

Remaining limitation:
NVIDIA App SelfUpdate_{B2FE1952-0186-46C3-BAEC-A80AA35AC5B8} is still enabled.
Windows denied access when disabling this administrator-owned task. No alternative bypass was attempted.
To make NVIDIA App updates manual too, open Task Scheduler as administrator, locate that task and disable it.
Opening NVIDIA App during this work ran its already pending app update. No graphics driver update was selected.

## Manual starts

Open Docker Desktop from the Start menu, or run:

```powershell
docker desktop start
```

Start only the containers you need:

```powershell
docker start kzy-mobility-minio kzy-mobility-redis
docker start toolrator-postgres toolrator-meilisearch
```

Open Ubuntu manually or use `wsl -d Ubuntu-22.04`.
To start the PI web services explicitly:

```powershell
wsl -d Ubuntu-22.04 -u root -- systemctl start pi-web.service pi-web-lite.service
```

To stop after use:

```powershell
docker desktop stop
wsl --shutdown
```

Enable NVIDIA Overlay manually in NVIDIA App > Einstellungen > Merkmale if desired.

## Previous settings

Exported scheduled-task XML files and previous container/overlay settings are stored beside this README.
Container restart policies were always for MinIO/Redis and unless-stopped for PostgreSQL/Meilisearch.
