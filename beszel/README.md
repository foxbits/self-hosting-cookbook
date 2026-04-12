This is the docker compose setup for a [Beszel](https://beszel.dev/) system monitoring server that can monitor both system usage, services and docker containers.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [The Beszel HUB](http://fx-plex-server:8090) at port `8090`
- [The Beszel Agent](http://fx-plex-server:8090) at socket `./beszel_socket`

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `HUB_URL`: the url that will be used to access this server e.g. http://my-server:8090
- `KEY`: HUB SSH Public Key, needed by the agent - needs to be set after the hub's first run
- `TOKEN`: Hub Auth Token, needed by the agent - needs to be set after the hub's first run
- `EXTRA_FILESYSTEMS`: A list of disk mounts and the label to mount them as in the monitoring system, comma separated, in the format "<mount-path>:<label>", example `/mnt/sda2:MEDIA_E,/mnt/sda3:MEDIA_F`


## Running

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

### Configuring the stack

1. Go to `HUB_URL` and create an account with a strong password (the admin account)
2. Click `Add System` -> Select Docker:
   1. Name: `local agent`
   2. Host/IP: `/beszel_socket/beszel.sock`
   3. Copy the Public Key field and paste it into the `.env` file -> KEY
   4. Copy the Token field and paste it into the `.env` file -> Token
   5. Click Save
3. Restart the docker containers with `make update-run` and go back. You will see that now the agent will show as connected
4. Connect extra disks - by default Beszel only reads the root disk, to add others, add them in the volumes list of `beszel-agent` (hot of the hub!) (example [here](https://beszel.dev/guide/additional-disks#docker-agent)) and then restart the containers
5. If the system services do not show up, check the troubleshooting [here](https://beszel.dev/guide/systemd#docker-agent).
6. Enable notifications
   1. Go to Settings -> Notifications
   2. If you want to enable email notifications, click on the SMTP Settings. Login again on the new page with the username and password of the Admin, and then go to Settings -> Mail Settings and setup your SMTP server (e.g. use a mail server you use).
   3. For other channel notifications, see [this page](https://beszel.dev/guide/notifications/). For example, for Discord, have a private Server (or Create one), create a dedicated channel for server updates (e.g. #server-updates), then go to Channel Settings -> Integrations and create a new Webhook with a nice bot name. Copy the Webhook URL and extract from it the `token` and `webhookid` and then add them to the notifications list in the format `discord://token@webhookid` and Save.
   4. Go to the Hub Dashboard, and at the end of the row for the All Systems list, check the little notifications arrow. Enable / Disable there what notifications you want to receive.

### Back-up

The configuration and data will be stored in the `beszel_data`, `beszel_agent_data` folders - so this is what you have to back-up.
