This is the docker compose setup for a simple [Firefly III](https://github.com/firefly-iii/firefly-iii) and [Firefly III Data Importer](https://github.com/firefly-iii/data-importer) installation for money management and reporting.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

Term definitions:
**App URL**: `http://my-server:9850` (`my-server` can be `localhost`, your server name if using local/vpn, or your actual public domain such us firefly.my-domain.com)
**FIDI Local URL**: `http://my-server:9851`
**FIDI Public URL**: `https://my-server:9853`

The setup starts the following services:
- [The Firefly Server](https://github.com/firefly-iii/firefly-iii) at port `9850` - can be accessed in browser at [http://localhost:9850](http://localhost:9850)
- [The Data Importer](https://github.com/firefly-iii/data-importer) at port `9851` - can be accessed (HTTP) in browser at [http://localhost:9851](http://localhost:9851)
- [The Caddy Server](https://github.com/caddyserver/caddy) at port `9853` - reverse proxy with HTTPS to enable secure connection to the data importer, can be accessed at [https://localhost:9853](https://localhost:9853)
- Maria DB - database server used by Firefly, internal only
- Custom Cron Scheduler - job scheduler used by Firefly, internal only

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `SITE_OWNER`: set to your email
- `APP_KEY`: set to a (new) random 32 characters string (important, security)
- `TZ`: the timezone used, set to your timezone
- `DB_PASSWORD`: the database password to use, set to a strong password
- `STATIC_CRON_TOKEN`: set to a (new) random 32 characters string (different than APP_KEY)
- `APP_URL`: set to **App URL**
  
The setup uses the [`.db.env`](.db.env) file to define settings used in the docker compose. [`.db.env.default`](.db.env.default) can be used as example. Possible variables:
- `MYSQL_PASSWORD`: set to the same value as `DB_PASSWORD`

The setup uses the [`.importer.env`](.importer.env) file to define settings used in the docker compose. [`.importer.env.default`](.importer.env.default) can be used as example. Possible variables:
- `VANITY_URL`: set to **App URL**
- `APP_URL`: set to **App URL**
- `ENABLE_BANKING_APP_ID`: set to your Enable Banking application ID, if using Enable Banking
- `ENABLE_BANKING_PRIVATE_KEY`: set to the contents of the `.pem` file downloaded from Enable Banking; since it's multiline, make sure to enclose by quotes ("<certificate-multi-line>")


## Running

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

If you have a running system and want to update it, use the same update commands. Use **App URL** to access Firefly (first time it will ask you to create an admin user) and **FIDI Public URL** to access the Data Importer. Check out extra guidelines on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com) or on Firefly Docs:
- https://docs.firefly-iii.org/how-to/firefly-iii/installation/docker/
- https://docs.firefly-iii.org/how-to/data-importer/installation/docker/
- https://docs.firefly-iii.org/tutorials/data-importer/data-providers/
- https://docs.firefly-iii.org/how-to/firefly-iii/advanced/notifications/#email

### Back-up

The configuration and data will be stored in the `./importer` folder (relative to where you're running the stack) - for the data used by the importer - and in these docker volumes: firefly_iii_upload, firefly_iii_db, caddy_data, caddy_config - so this is what you have to back-up.
