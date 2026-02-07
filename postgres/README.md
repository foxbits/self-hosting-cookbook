This is the docker compose setup for an [PostgreSQL](https://www.postgresql.org/docs/) database server.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [The PostgreSQL Database Server](https://www.postgresql.org/docs/) at port `5432`

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `POSTGRES_USER`: `postgres`
- `POSTGRES_PASSWORD`: set to a strong password


## Running

### Pre-requisites

The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../)

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

Other systems can be connected directly to the database server from the host, or through the `postgres` name if they run on the same docker network (`home-lab-net`), at port `5432`.

### Back-up

The configuration and data will be stored in the `postgres_data` volume - so this is what you have to back-up.
