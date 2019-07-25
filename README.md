## NTC Tesuto Management

This menu-driven script streamlines operating and managing Tesuto network emulations. It can be run as a Python script or as a Docker image.

### Python Script

**Step 1: Install dependencies**

This will install the Python packages required by the script. (Note: You might opt to do this within a Python virtual environment.)

```
pip install -r requirements.txt
```

**Step 2: Run the script**

Execute the script, specifing your Tesuto API token with `--token`:

```
python ntc_tesuto.py --token <TOKEN>
```

### Docker Container

Note: The first two steps need to be performed only once. The container will be reused for future instances.

**Step 1 (one time): Build the image**

```
make build-image
```

**Step 2 (one time): Initialize the container**

Initialize the Docker container, passing your Tesuto API token as an environment variable.

```
make init-container TOKEN=<TOKEN>
```

**Step 3: Run the container**

```
make run
```

Two additional `make` targets are also available:

* `remove-container`: Remove the Docker container
* `remove-image`: Remove the Docker image

These can be used to clean up your Docker environment in the event you need to upgrade the application or no longer require this app.
