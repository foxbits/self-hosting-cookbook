This repository contains a set of tools and helpers for deploying self-hosted applications (mostly docker compose files and instructions).

## Applications list
1. [`arr-stack`](arr-stack) - docker compose setup for the official images for the *arr stack: [radarr](https://github.com/Radarr/Radarr), [sonarr](https://github.com/Sonarr/Sonarr), [jackett](https://github.com/Jackett/Jackett) and [flaresolverr](https://github.com/FlareSolverr/FlareSolverr)
2. [`firefly-iii`](firefly) - docker compose setup for [Firefly III](https://github.com/firefly-iii/firefly-iii) and [Firefly III Data Importer](https://github.com/firefly-iii/data-importer) installation for money management and reporting
3. [`jenkins`](jenkins) - docker compose setup for a simple jenkins stack with a controller and an agent that runs the jobs (CI/CD). This is build based on the documentation available at [jenkins](https://github.com/jenkinsci/docker/blob/master/README.md). The agent is custom made - it is given access to docker on the host machine (DooS - to run builds in containers and be able to deploy) and can run `make` commands
4. [`plex-server`](plex-server) - docker compose setup for Plex Media Server - one of the top movies, TV and music personal servers management systems.
5. [`postgres`](postgres) - docker compose setup for an [PostgreSQL](https://www.postgresql.org/docs/) database server
6. [`portainer`](portainer) - docker compose setup for [portainer](https://docs.portainer.io), a web UI for docker container management
7. [`scrobblex`](scrobblex) - docker compose setup for a simple [scrobblex](https://github.com/ryck/scrobblex) agent that can be connected to Plex and used to scrobble Plex plays live into trakt.tv.


## How to use

### Pre-requisites

1. Before using any services from this suite, you need to create the underlying home lab docker network, by running `make create-network`

### How to run

1. Select a service you want to use and follow the instructions from the Readme to set it up
2. Use `make run-update-all` to update all the running services (make sure to set the `EXCLUDE` env var)

### Available commands

The following commands are available at repo-level (they require `make`):

1. `make create-network` - creates the underlying docker network (`home-lab-net`) that is required for inter-container communication
2. `make run-update-all` - updates all of the applications to the latest stable version (runs the `update-run` command of each); if you want to exclude certain apps (e.g. if you do not use them), add a `.env` file and set the `EXCLUDE` value there as a space-separated list of directory names
