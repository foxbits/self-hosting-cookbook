This is the docker compose setup for an [Actual](https://actualbudget.org/docs/) server, for money management with envelope budgeting and calendar events.

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
- [The Actual Server](https://actualbudget.org/docs/) at port `9860` - can be accessed in browser at [http://localhost:9860](http://localhost:9860)

If you want to enable multi-user mode, you have to also setup an Open ID Auth server (like [`fusionauth`](../fusionauth/)) and expose the Actual server under a HTTPS reverse proxy like caddy or cloudflared.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- [none for now]


## Running

### Pre-requisites

The stack also needs to be exposed through HTTPS to your connecting devices / services and that part is not included here (using the application as PWA on a phone will not work with HTTP for example). 

You can either add a [`caddy`](https://github.com/caddyserver/caddy) reverse proxy (with self-signed certificate) (example [`here`](../firefly/Caddyfile)) and then import the `.crt` certificate to your devices, or use a tunneling service like [cloudflared](https://github.com/cloudflare/cloudflared).

### Starting the stack

You will have to have `docker` and `docker compose` installed on the host machine.

Make sure that you setup the environment variables correctly.

Then use:
- `make build` - to update the stack images to latest version
- `make run` - to just run the system (basic docker compose up command)
- `make run-update` - to first update the stack (pull), and then run it (run)

Actual will be available at [http://localhost:9860](http://localhost:9860).
You will need to configure your HTTPS reverse proxy on top of it and then access it only through the proxy, not directly.


### Configure the stack

1. Access the server at the https address and create the first / admin account
2. Go to More → Settings:
	1. Enable encryption (End-to-end encryption) and set a password for the budget file
	2. To enable Currencies: Go to Settings → Show Advanced Settings → Click on the I Understand from Experimental features → Enable Currency Support; then refresh the Settings page and set the Currency in the Currency Settings section
3. Connect to an Open ID Auth server to enable better security or multi-user support. Example for [`fusionauth`](../fusionauth/) (if you use other auth provider, do your own)
	1. Create a new application in FusionAuth:
   	1. Add it to the tenant of your server
   	2. Set as Authorized URL to https://your-actual-domain/openid/callback and authorized request origin url to https://your-actual-domain 
	2. In Actual
   	1. Select OpenID provider as Other
   	2. Put in the `client id` and `client secret`
   	3. For auth server URL use `https://<your-fusionauth-server>/.well-known/openid-configuration/<your-tenant-guid>` (make sure to use tenant guid and not the name)
	3. Logout and login back to your Actual Server, so you can become the Admin user


### Back-up

The configuration and data will be stored in the `./data` folder (relative to where you're running the stack) - for the data used by actual - so this is what you have to back-up.
