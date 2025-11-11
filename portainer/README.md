This is the docker compose setup for [portainer](https://docs.portainer.io) - a web UI for docker container management.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)
  - [Back-up](#back-up)


## Understanding the setup
The setup starts 1 service:
- [portainer](https://docs.portainer.io/start/install-ce/server/docker/linux#docker-compose) at port `9843` - can be accessed in browser at [http://localhost:9843](http://localhost:9843)

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).


## Running

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

If you have a running system and want to update it, use the same update commands.

### Configuring the stack
Assuming you access your server using the resolved name `plex-server`, do the following steps:

1. Go to the running portainer instance - e.g. http://plex-server:9843
2. Follow the setup guide from https://docs.portainer.io/start/install-ce/server/setup

### Back-up

The portainer configuration and data will be stored in the `portainer_data` volume - this is what you have to back-up.
