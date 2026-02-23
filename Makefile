IMAGE_NAME ?= smauto
CONTAINER_NAME ?= smauto
API_PORT ?= 8080
LSP_PORT ?= 2087
API_KEY ?=

DOCKER_BUILD = DOCKER_BUILDKIT=1 docker build --ssh default -f docker/Dockerfile -t $(IMAGE_NAME) .

DOCKER_RUN_FLAGS = -d --name $(CONTAINER_NAME) \
	-p $(API_PORT):8080 \
	-p $(LSP_PORT):2087

ifdef API_KEY
DOCKER_RUN_FLAGS += -e TX_LSP_API_KEY=$(API_KEY)
endif

.PHONY: docker-build docker-rebuild docker-run docker-stop docker-restart docker-logs docker-shell docker-clean

docker-build:
	$(DOCKER_BUILD)

docker-rebuild:
	$(DOCKER_BUILD) --no-cache

docker-run:
	docker run $(DOCKER_RUN_FLAGS) $(IMAGE_NAME)

docker-stop:
	docker stop $(CONTAINER_NAME) && docker rm $(CONTAINER_NAME)

docker-restart: docker-stop docker-run

docker-logs:
	docker logs -f $(CONTAINER_NAME)

docker-shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

docker-clean: docker-stop
	docker rmi $(IMAGE_NAME)
