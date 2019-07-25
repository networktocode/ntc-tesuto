DOCKER_IMG = ntc-tesuto
DOCKER_TAG = latest
CONTAINER_NAME = ntc-tesuto-container

.PHONY: build-image
build-image:       ## Build docker image. One time.
	docker build -t $(DOCKER_IMG):$(DOCKER_TAG) .


.PHONY: init-container
init-container:    ## This is a one-time creation of the container using the image.
	docker run -it \
	--name $(CONTAINER_NAME) \
	-e TESUTO_API_TOKEN=$(TOKEN) \
	$(DOCKER_IMG):$(DOCKER_TAG)

.PHONY: run
run:               ## This starts the container so a new one isn't created each time.
	docker start -ai $(CONTAINER_NAME)

.PHONY: remove-container
remove-container:  ## Remove container with CONTAINER_NAME
	docker stop $(CONTAINER_NAME); \
	docker rm $(CONTAINER_NAME); \

.PHONY: remove-image
remove-image:      ## Remove container imagine with DOCKER_IMG
	docker stop $(CONTAINER_NAME); \
	docker rm $(CONTAINER_NAME); \


help:              ## Show this help!
	@sed -ne '/@sed/!s/## //p' $(MAKEFILE_LIST)