This is the docker compose setup for [Plex Media Server](https://www.plex.tv) - one of the top movies, TV and music personal servers.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)
  - [Back-up](#back-up)


## Understanding the setup
The setup starts 1 service:
- [plex-server](https://github.com/plexinc/pms-docker) on the host network (to be able to bind remote connections) - and the web UI can be accessed in browser at [http://localhost:32400/web](http://localhost:32400/web)

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

By default Plex Media Server has the mounted drivers such that it can perform transcoding (which, naturally, works better with an Intel Processor that supports Quick Sync).


### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `TimeZone`: a valid timezone in ISO format
- `CONFIG_PATH`: where Plex Server stores all the configuration data (should be on a fast drive with plenty of space)
  - this is not directly the 'Plex Media Server' folder that is usually backed up; the directory structure needs to be `/some/directory/Library/Application Support/Plex Media Server` and the `CONFIG_PATH` in this case would be `/some/directory` (details [here](https://github.com/plexinc/pms-docker?tab=readme-ov-file#config-directory) as well)
  - if you have data that needs to be migrated (see [this](https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/)), you need to put it in this folder in the same structure (e.g. put `Plex Media Server` directory in the right hierarchy)
- `TRANSCODE_PATH`: the path where Plex will put the temporary transcode files (should be on a fast drive with plenty of space)
- settings for each mount (at least 1) - to mount different hard-drives, let's say HDD number `n` you will have to add each of the three setup entries for it:
   - `MEDIA_SOURCE_n`: defines the path where the data is stored on the host, it will be mounted under the same path inside the container
- `PLEX_UID` and `PLEX_GID`: define the IDs that will be used by plex for file ownership and should coincide with your own user; since by default a normal user has id/gid as `1000` the defaults should be ok, but run `id $USER` to find out your IDs and replace if necessary

And then they have to be added in the `volumes` section in the [`docker-compose.yml`](docker-compose.yml). By default this setup has an example of adding two mounted drives.

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

If you are setting up Plex for the first time (e.g. server not claimed), you need to follow the steps from [here](https://github.com/plexinc/pms-docker?tab=readme-ov-file#running-on-a-headless-server-with-container-using-host-networking) to claim it. The alternative is to add a CLAIM_TOKEN to the compose setup.

Then, assuming you access your server using the resolved name `plex-server`, do the following steps:

1. Go to the running plex server instance web UI - e.g. http://plex-server:32400/web
2. Configure your server settings (if this is the first time you run it) using the hints and guidelines available at [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com) or using your own preferences.

### Back-up

The plex server configuration and data will be stored in the directories defined by the environment variables (`CONFIG_DATA` is the main one) - this is what you have to back-up.
