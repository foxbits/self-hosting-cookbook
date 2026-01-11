This is the docker compose setup for a simple [scrobblex](https://github.com/ryck/scrobblex) agent that can be connected to Plex and used to scrobble Plex plays live into trakt.tv.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-configuration](#pre-configuration)
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
- `PLEX_USER`: the plex username (or username list, separated by comma) to allow scrobbling for


## Running

### Pre-configuration

1. Go to https://trakt.tv/oauth/applications/new 
2. As name, use something like "plex scrobbler (scrobblex)"
3. As description, use something like "Application to scrobble from plex through scrobblex"
4. As Redirect uri, use http://localhost:3090/authorize on the first line (plex and scrobblex will be on the same server) and add new lines for each URL that you access your server with - IP or name, for example http://plex-server:3090/authorize
5. For permissions, enable `checkin` (optional) and `scrobble` (mandatory)
6. Use the application id and application secret in the environment variables 
7. Optionally, if you want to scrobble only for a specific user, also set the PLEX_USER environment variable (otherwise all the scrobbles from all the users will go in to the trakt account)

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

1. Go to the running scrobblex instance - e.g. http://plex-server:3090
2. Go to step 2 and do the trakt authorization flow
3. Go to your Plex Server (http://plex-server:32400/web) -> Settings -> Webhooks and add as webhook the scrobblex instance (http://plex-server:3090/plex)
4. Watch a movie or an episode of something and see if it gets scrobbled! Note that Plex [webhooks](https://support.plex.tv/articles/115002267687-webhooks/?utm_campaign=Plex%20Apps&utm_medium=Plex%20Web&utm_source=Plex%20Apps) are not triggered when you manually mark something as watched.

### Back-up

The scrobblex configuration and data will be stored in the `./scrobblex` folder (relative to where you're running the stack) - this is the folder you have to back-up.
