This is the docker compose setup for an [FusionAuth](https://fusionauth.io/docs/get-started/download-and-install/docker) (community edition), a fully integrated authentication and authorization server.

A full setup and integration guide can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Pre-requisites](#pre-requisites)
  - [Starting the stack](#starting-the-stack)
  - [Configure the stack](#configure-the-stack)
  - [Back-up](#back-up)


## Understanding the setup

The setup starts the following services:
- [The Fusion Auth Server](https://fusionauth.io/docs/get-started/download-and-install/docker) at port `9701` - can be accessed in browser at [http://localhost:9701](http://localhost:9701) but it does not work well without an HTTPS reverse proxy on top of it
- [Open Search Server](https://docs.opensearch.org/latest/about/) at port `9702` - needed by Fusion Auth to work properly

This stack depends on a postgres database and by default is configured to use a [`postgres`](../postgres/) instance already running on the same docker network (`home-lab-net`).

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- `DATABASE_PASSWORD`: set a strong password that will be used by the fusionauth account in postgres
- `POSTGRES_PASSWORD`: set the password that is set for the `postgres` (with admin access) in your postgres instance (needed to run admin-like DML scripts)


## Running

### Pre-requisites

The stack runs on the docker network `home-lab-net`. To create it you can use the command `make create-network` from the root of this repository [`self-hosting-cookbook`](../).

The stack also needs to be exposed through HTTPS to your connecting devices / services and that part is not included here. You can either add a [`caddy`](https://github.com/caddyserver/caddy) reverse proxy (with self-signed certificate) (example [`here`](../firefly/Caddyfile)) and then import the `.crt` certificate to your devices, or use a tunneling service like [cloudflared](https://github.com/cloudflare/cloudflared).

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

FusionAuth will be available at [http://localhost:9701](http://localhost:9701).
You will need to configure your HTTPS reverse proxy on top of it and then access it only through the proxy, not directly.


### Configure the stack

1. Access the instance. Create an admin user.
2. Follow the setup from the initial screen
	1. Create a default application (no need for details now)
	2. Create an API key and save it somewhere safe
	3. Setup an Email Server (with your preferred SMTP server, if you have one)
	4. Get a free (community) license key and activate the server
3. Create a tenant for your server. Ideally you would use a single tenant to login to your home lab server, as a SSO, not necessarily one tenant per each application, but up to you. Tips:
	1. Identity - Enable identity verification (email), select a template (email verification); optionally change the verification strategy to code if you want to
	2. Multi-Factor - set Required at login
	3. Password - setup requirement for length and multi-characters
4. Go to users and generate an user for the tenant (skip verification and select "Do not send password" to be able to set it here)
5. If you want to not allow users to register, disable registration for each application in the applications tab (it should be disabled by default anyways). This way you control what users you can add, manually.
6. Create a theme from the default FusionAuth theme (a copy) from Customizations - Theme.
   1. If you want to change the default page when accessing the home page of the auth website, put something like this in Index (you can customize it for more complexity, like a loader etc.) - it auto-redirects to your main home page
   2. Go to tenant and change the theme, to both yours and the default

```
[#ftl/]
[#import "_helpers.ftl" as helpers/]

[@helpers.html]
  [@helpers.head title="foxbites.net auth"]
	<head>
       <meta http-equiv="Refresh" content="0; URL=https://your-home-page" />
    </head>
  [/@helpers.head]
[/@helpers.html]
```


### Back-up

The configuration and data will be stored in these docker volumes: fusionauth_config, search_data - so this is what you have to back-up.
