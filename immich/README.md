This is the docker compose setup for [Immich](https://immich.app/), a self-hosted photo and video backup solution with mobile apps for automatic backup.

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [Immich Server](https://immich.app/) at port `2283` - can be accessed in browser at [http://localhost:2283](http://localhost:2283)
- [Immich Machine Learning](https://github.com/immich-app/immich) - for facial recognition and other ML features (using OpenVINO for Intel CPU acceleration)

This stack depends on a PostgreSQL (with pgvector and vchord) database and Redis/Valkey for caching. By default it is configured to use a [`datastore-sql`](../datastore-sql/) and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables that might need changing:

**General settings:**
- `UPLOAD_LOCATION`: The location where your uploaded files are stored (default: `/mnt/sda4/photos`)
- `TZ`: Timezone (e.g., `Europe/London`) - uncomment to set
- `IMMICH_VERSION`: The Immich version to use. You can pin this to a specific version like `v1.71.0` (default: `release`)

**Redis/Valkey:**
- `REDIS_URL`: URL for the Redis/Valkey instance (default: `redis://datastore-memory:6379/0`)

**Database:**
- `DB_PASSWORD`: PostgreSQL password (change from default)
- `DB_USERNAME`: PostgreSQL username (default: `postgres`)
- `DB_DATABASE_NAME`: PostgreSQL database name (default: `immich`)


## Running

### Pre-requisites

1. The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).
2. This stack depends on a PostgreSQL database and Redis/Valkey. By default it is configured to use [`datastore-sql`](../datastore-sql/) and [`datastore-memory`](../datastore-memory/) instances already running on the same docker network (`home-lab-net`).
3. The stack also needs to be exposed through HTTPS to your connecting devices / services and that part is not included here. You can either add a [`caddy`](https://github.com/caddyserver/caddy) reverse proxy (with self-signed certificate) or use a tunneling service like [cloudflared](https://github.com/cloudflare/cloudflared).
4. The machine learning service uses OpenVINO for hardware acceleration on Intel CPUs. If you're using a different CPU architecture, you may need to change the image tag suffix (`-openvino`) to match your hardware (e.g., `-cuda` for NVIDIA GPUs, `-rocm` for AMD GPUs, `-armnn` for ARM).
5. Hardware acceleration for transcoding is enabled by default using QuickSync. This can be disabled by removing or commenting out the `extends` section in the docker-compose.yml, or changed to another option (nvenc, rkmpp, vaapi, vaapi-wsl, cpu) by changing the service in the extends block.

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure to copy `.env.default` to `.env` and update the values appropriately.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command); additionally it will also create the database and extensions on first run
- `make run-update` - to first update the stack (pull), and then run it (run)

Immich will be available at [http://localhost:2283](http://localhost:2283).

### Configure the stack

1. On first access, you'll be taken to the admin registration page to create your admin account.
2. Download the Immich mobile app and connect it to your server for automatic photo backup.
3. For advanced features like facial recognition, ensure the machine learning service is running properly.

### Back-up

The configuration and data will be stored in the `immich` PostgreSQL database, and the photos in `UPLOAD_LOCATION` - so back these up.
Also back up the `.env` file (contains passwords and configuration).