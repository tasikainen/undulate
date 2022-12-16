# builder - A build pipeline
The component provides a build APi that clones a public repository, builds a Docker image based on the repository (using a Dockerfile included in the repository) and pushes the image thus built to a Docker image registry.

## Setup

The component uses the environment variables `REGISTRY_USER_NAME` to determine the user in [Docker Hub](https://hub.docker.com/) under which the images that are built will be pushed.

The other parameters:

- the repository to be built
- the tag under the repository to be built

are passed as parameters.

## Running builder

Example call for building components **test-app** and **test-app-parameters**:

test-app
```
curl -X POST -H "Content-Type: application/json" -d '{"shellog_params": {"interval":"5.0"},"payload_command": "python3,builder.py,https://version.helsinki.fi/test_group_xcese/test-app.git,v1"}' http://localhost:5000/api/build
```
test-app-parameters
```
curl -X POST -H "Content-Type: application/json" -d '{"shellog_params": {"interval":"5.0"},"payload_command": "python3,builder.py,https://version.helsinki.fi/test_group_xcese/test-app-parameters.git,prod"}' http://localhost:5000/api/build
```

Above it is assumed that the **builder** component is running on `localhost` at port 5000.

## Known errors
```
standard_init_linux.go:211: exec user process caused "no such file or directory"
```
Seems to be raised when on windows systems the run.sh uses CRLF line endings instead of LF. Fixed by changing the line endings to LF.

