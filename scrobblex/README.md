This is the docker compose setup for a simple [scrobblex](https://github.com/ryck/scrobblex) agent that can be connected to Plex and used to scrobble Plex plays live into trakt.tv.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)
  - [Back-up](#back-up)


## Understanding the setup
The setup starts 1 service:
- [The Scrobblex Agent](https://github.com/ryck/scrobblex?tab=readme-ov-file#docker) at port `3090` - can be accessed in browser at [http://localhost:3090](http://localhost:3090)

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `TRAKT_ID`: the trakt.tv application id
- `TRAKT_SECRET`: the trakt.tv application secret


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

1. Go to https://trakt.tv/oauth/applications/new 
2. As name, use something like "plex scrobbler (scrobblex)"
3. As description, use something like "Application to scrobble from plex through scrobblex"
4. As Redirect uri, use http://localhost:3090/authorize  (plex and scrobblex will be on the same server)
5. For permissions, enable `checkin` and `scrobble`
6. Use the application id and application secret in the environment variables 

### Back-up

The scrobblex configuration and data will be stored in the `./scrobblex` folder (relative to where you're running the stack) - this is the folder you have to back-up.
