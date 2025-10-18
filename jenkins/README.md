This is the docker compose setup for a simple jenkins stack with a controller and an agent that runs the jobs (CI/CD). This is build based on the documentation available at [jenkins](https://github.com/jenkinsci/docker/blob/master/README.md). The agent is custom made - it is given access to docker on the host machine (DooS - to run builds in containers and be able to deploy) and can run `make` commands.

A full guideline and articles on setting up jenkins, the agent and connecting it to GitHub repositories + troubleshooting, can be found on [thefoxdiaries.substack.com](https://thefoxdiaries.substack.com).

- [Understanding the setup](#understanding-the-setup)
  - [Environment variables](#environment-variables)
- [Running](#running)
  - [Starting the stack](#starting-the-stack)
  - [Configuring the stack](#configuring-the-stack)
  - [Back-up](#back-up)


## Understanding the setup
The setup starts 2 services:
- [The Jenkins Controller](https://hub.docker.com/r/jenkins/jenkins) at port `9830` - the main jenkins application
- [The Jenkins SSH Agent](https://hub.docker.com/r/jenkins/ssh-agent) [no port] - an SSH agent customized on top of the official image for docker socket and make access

The two services store their data into their own volumes - `jenkins_home` and `jenkins_agent_home` respectively.

The stack is configured to restart automatically, so on a machine restart, it always starts back automatically (assuming docker service also always starts automatically).

The **agent [`Dockerfile`](Dockerfile)** builds on top of the official ssh agent image from jenkins, adding `make` capability and installing the `docker-cli` that will use the docker socket (mounted in the compose setup) to communicate with docker on the host. To be able to do that successfully, it also sets the `DOCKER_GID` to the host docker group id (env var is set through make), to add the jenkins user inside the container to the same group. To see the current group (on host or on agent) run `grep docker /etc/group`

### Environment variables

The setup uses the [`.env`](.env) file to define settings used in the docker compose. [`.env.default`](.env.default) can be used as example. Possible variables:
- [JENKINS_AGENT_SSH_PUBKEY](https://hub.docker.com/r/jenkins/ssh-agent): generate a new ssh key on your machine with `ssh-keygen -t ed25519 -C "Jenkins Private Runner Key"` and pass the public key here

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

1. Open the logs for the controller to get the initial password: `docker logs jenkins-controller`
2. Access jenkins at `http://your-server:9830` (or whichever port you put it), use the default password, install the recommended plugins, setup a new admin user
3. Click on the jenkins Settings icon - go to Credentials Manager, and Global Credentials, to add the SSH key (Add SSH username and key, put in an unique id that you remember - `jenkins-agent-key` and select to input the key directly - use `cat ./.ssh/.id_xxxx` to get the key you created at the beginning)
4. Then go again to Settings - you will see an agent setup notification. Click on it to create a new node. Put a nice name e.g. `ssh-agent-with-docker` and select *Permanent*.
	1. For Remote root directory use `/home/jenkins/agent`  (this is what is setup in the docker compose)
	2. Launch method - Launch agents via SSH. Host = `jenkins-agent` (the container name, since they are with docker compose on the same network) and select No verification
	3. Save; then go to the list of agents and you should see it says in sync and green; otherwise you did something wrong
	4. Then go and disable running jobs on the controller (Jenkins will notify you to disable it anyway)

You can add multiple agents and configure them in the controller in the same way.

### Back-up

The two volumes - `jenkins_home` and `jenkins_agent_home` - contain all of the data. This is waht you have to back-up / copy across installations (but ideally cleaning up job data for the runner, or not backing up the agent at all).
