ROOT=/absolute/path/to/rufes/tools/rufes-evaluation
RUNID=test-run
GOLD=gold.tab
COREDOCS=coredocs.txt
HOST_INPUT_DIR=$(ROOT)/example/runs/$(RUNID)
HOST_OUTPUT_DIR=$(ROOT)/example/scores/$(RUNID)
HOST_DATA_DIR=$(ROOT)/example/data

all:
	@echo "Usage: make [build|run]"	

clean:
	docker system prune -f
	docker image rm rufes-evaluation

build:
	docker build \
	-t rufes-evaluation .

rebuild: clean build

run-example: run-evaluation-pipeline

run-evaluation-pipeline:
	docker run \
	  --env RUNID=$(RUNID) \
	  --env GOLD=$(GOLD) \
	  --env COREDOCS=$(COREDOCS) \
	  -v $(HOST_INPUT_DIR):/evaluate:ro \
	  -v $(HOST_OUTPUT_DIR):/score \
	  -v $(HOST_DATA_DIR):/data \
	-it rufes-evaluation
