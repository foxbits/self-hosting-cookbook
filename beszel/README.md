This is the docker compose setup for a [Beszel](https://beszel.dev/) system monitoring server.

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
- `DISABLE_PASSWORD_AUTH`: set to false if you have an auth server, e.g. [`fusionauth`](../fusionauth/), defaults to true
- `KEY`: HUB SSH Public Key, needed by the agent - needs to be set after the hub's first run
- `TOKEN`: Hub Auth Token, needed by the agent - needs to be set after the hub's first run


## Running

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

### Configuring the stack

1. Go to `HUB_URL` and create an account.

### Back-up

The configuration and data will be stored in the `beszel_data`, `beszel_agent_data` folders - so this is what you have to back-up.
