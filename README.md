# qbittorrent_nordvpn_docker

### SETUP
1. Rename .env_example to .env and replace placeholders with sensible values
2. Run via `docker compose up [-d] [--build]`

### TODO
* Killswitch *should* work, but adding redundancy via comparing the result of a `curl ifconfig.me` from inside and outside the container to ensure they're different could be a nice to have
