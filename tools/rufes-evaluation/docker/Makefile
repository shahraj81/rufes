ROOT=/absolute/path/to/rufes/tools/rufes-evaluation
RUNID=test-run
HOST_INPUT_DIR=$(ROOT)/practice/runs/$(RUNID)
HOST_OUTPUT_DIR=$(ROOT)/practice/scores/$(RUNID)
HOST_DATA_DIR=$(ROOT)/practice/data

all:
	@echo "Usage: make [build|run]"	

clean:
	docker system prune -f
	docker image rm rufes-evaluation

build:
	docker build \
	  --build-arg version=$(GRAPHDB_VERSION) \
	  --build-arg edition=$(GRAPHDB_EDITION) \
	-t rufes-evaluation .

rebuild: clean build

run-practice: run-evaluation-pipeline

run-evaluation-pipeline:
	docker run \
	  --env RUNID=$(RUNID) \
	  -v $(HOST_INPUT_DIR):/evaluate:ro \
	  -v $(HOST_OUTPUT_DIR):/score \
	  -v $(HOST_DATA_DIR):/data \
	-it rufes-evaluation
