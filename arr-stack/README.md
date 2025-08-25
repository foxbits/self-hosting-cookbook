This is the docker compose setup for the official images for the *arr stack: [radarr](https://github.com/Radarr/Radarr), [sonarr](https://github.com/Sonarr/Sonarr), [jackett](https://github.com/Jackett/Jackett) and [flaresolverr](https://github.com/FlareSolverr/FlareSolverr).

A full guideline and articles on building your own server, from hardware to software and tips and tricks can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
  - [Important about mounted directories](#important-about-mounted-directories)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)


## Understanding the setup

The setup starts 4 services:
- [radarr](https://github.com/Radarr/Radarr) at port `7878` - the service used for **movie** management
- [sonarr](https://github.com/Sonarr/Sonarr) at port `8989` - the service used for **tv show** management
- [jackett](https://github.com/Jackett/Jackett) at port `9117` - the service used for providing content sources (like torrent trackers)
- [flaresolverr](https://github.com/FlareSolverr/FlareSolverr) at port `8191` - the service used by `jackett` to solve cloudflare and other challenges when accessing the content source websites

In order to have a fully functional *arr stack, you will have to also have a download client running, for example a torrent client like [qBittorrent](https://www.qbittorrent.org) and have it's Web UI Open / Accessible (with user and password) on the host (e.g. at port `9999` or your preferred one), then configured inside the stack (both radarr and sonarr).

Each service stores its data in the [`config`](config) directory, so it's persistent across runs. 

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](env) file to define settings used in the docker compose, mainly the [timezone](https://timezonedb.com/time-zones) and mount paths.

To mount different hard-drives, let's say HDD number `n` you will have to add each of the three setup entries for it:
- `MEDIA_SOURCE_n`: defines the path where the data is stored on the host
- `MOVIES_MOUNT_n`: defines the path (relative to `/data/` directory) of the mounted folder for movies (Radarr)
- `TV_MOUNT_n`: same as previous, but for TV Shows (Sonarr)

And then they have to be added in the `volumes` section in the [`docker-compose.yml`](docker-compose.yml) file for both `radarr` and `sonarr`. By default this setup has an example of adding two mounted drives, and the `.env` file would look like:

```
# Media source #1 (host) and mounts (relative)
MEDIA_SOURCE_1=/mnt/sda2/MULTIMEDIA
MOVIES_MOUNT_1=movies-e
TV_MOUNT_1=tv-e

# Media source #2 (host) and mounts (relative)
MEDIA_SOURCE_2=/mnt/sda3/MULTIMEDIA
MOVIES_MOUNT_2=movies-f
TV_MOUNT_2=tv-f

# Timezone
TimeZone=Europe/Bucharest
```

### Important about mounted directories

The stack uses the concept of two separate directories - one for downloads, one for the library (downloads being managed mostly by the download client). 

The directories `downloads` and `library` (on the host if mounted) must both be in the same parent directory and mounted as a single item.

Example - if you have:
- `D:\Multimedia\Movies` -> contains the movies
- `D:\Multimedia\Downloads` -> contains the downloads

You will have to mount the whole `D:\Multimedia` directory (for radarr for example it will be `D:\Multimedia:/data/movies`).

Using 2 mounts (one for the library and one for downloads directory) won't work because docker creates them as 2 separate partitions and **hardlinks** don't work between separate partitions.


## Running

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly, as per instructions, add entries for each of the mounted HDDs you want to use.

Then use:
- [`run.sh`] - to just run the system (basic docker compose up command)
- [`run-and-update.sh`] - to first update the stack, and then run it

If you have a running system and want to update it, use the same update commands.

### Configuring the stack

1. Configure all your sources in the jackett application ([http://localhost:9117](http://localhost:9117)) and keep it at hand (the API key and the URLs are needed)
2. Have your download client up and running and configured with its Web UI accessible on the local network

Then, for Radarr:
1. Add your HDDs through their mounted paths (e.g. `/data/movies`) as locations: Media Management -> Root folder
2. Create a new category in your download client - e.g. "Movies - Radarr" and set the default download location for it inside the `Downloads` folder previously configured. This category will be used by Radarr to mark all radarr downloads with this category and put them in the right folder, but it will also help with things you download manually and want to be picked up by Radarr (e.g. if you download a movie manually and attach this category to it, radarr will automatically see it and import it, rather useful when automatic sources find no results)
3. Settings -> Download Clients - Add your download client:
   1. host: `host.docker.internal` (since it runs on the host)
   2. port: `9999` (the port you enabled the Web UI at)
   3. User/Pass: the user/pass you set for the Web UI
   4. Category: the exact category created at the previous step
   5. Do not enable "Remove completed" if you want to keep seeding, instead configure the seeding settings from the download client itself
4. Settings -> Download Clients - Add Remote path mapping. This is require for radarr to translate the path used by the download client with its local path from the running container
   1. Host: `host.docker.internal`
   2. Remote path: `D:\Multimedia\Downloads` (the path from your host where you set the downloads)
   3. Local path: `/data/movies/Downloads` (the mounted movie directory, but with the Downloads folder)
5. Add all the indexers you have set-up in jackett through Settings -> Indexers:
   1. URL: copy the tornzab url from jackett, but replace `localhost` with `jackett` (each container is accessible through its name inside the compose network)
   2. API Key: copy the API Key from jackett
   3. Categories: select the categories you need from this indexer (up to you, but it's important to configure, since the search will be done only in these categories)
   4. Priority: global priority when executing searches, compared to other indexes
   5. Test and Save
6. Settings -> Profiles:
   1. Create a new profile
   2. Enable only the release formats that you want, and order them in the priority you want them to be downloaded in. Radarr will try each of them sequentially and will download a release from the first one that it finds available
7. [Optional] Settings -> Custom Formats - this is a rather useful setting in order to make radarr prioritize certain releases or certain releasers, if you have any favorites, or to not download certain releases if they contain unsupported formats
   1. Add your favorite release tags and releasers in Custom Formats and mark them with positive scores in the Profiles tab. Usually title matching is just ok. 
   2. For example a profile named `HQ Encoding` would have the following different conditions: `x265`, `H265`, `H.265`, `HEVC`, `AV1` and would then be setup in Profiles with `+20`
   3. For example a profile named `HQ Releasers` would have the following different conditions: `QxR`, `JUDAS`, `FLUX` and would then be setup in Profiles with `+30`
   4. For example a profile named `Bad releasers` would have the following different conditions: `MeGusta`, `PSYPHER` and would then be setup in Profiles with `-100`
   5. Then in the profile you have setup, set minimum score to `+20` - this would make sure that each automatic download by radarr will be picked up first in the order of the formats set-up in Profiles, and for each format it would only check items with a score above 20
