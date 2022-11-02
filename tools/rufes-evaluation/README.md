# How to run the RUFES evaluation pipeline

* [Introduction](#introduction)
* [How to build the docker image?](#how-to-build-the-docker-image)
* [How to run the docker on a test run?](#how-to-run-the-docker-on-a-test-run)
* [How to apply the docker on your run?](#how-to-apply-the-docker-on-your-run)
* [Revision History](#revision-history)

# Introduction

This document describes how to run the RUFES evaluation pipeline using the RUFES-Evaluation docker as a standalone utility.

[top](#how-to-run-the-rufes-evaluation-pipeline)

# How to build the docker image?

Follow the steps given below to build the docker image:

  1. Go inside the directory named `docker`, and modify the value of the variable named `ROOT` (on line#1) in `Makefile` to reflect the `rufes` code directory,

  2. Run the following command while inside the directory named `docker`:
  ~~~
  make build
  ~~~
  Alternatively, you may run the following command:
  ~~~
  docker build -t rufes-evaluation .
  ~~~

[top](#how-to-run-the-rufes-evaluation-pipeline)

# How to run the docker on a test run?

An example run and corresponding scoring output has been placed respectively inside the directory named: `example/run/test-run` and `example/scores/test-run` .

In order to run the docker on the `test-run`, you may run the following command:

~~~
make run-example
~~~

Alternatively, you may run the following command:

~~~
run-evaluation-pipeline:
	docker run \
	  --env RUNID=test-run \
	  --env GOLD=gold.tab \
	  --env COREDOCS=coredocs.txt \
	  -v /absolute/path/to/rufes/tools/rufes-evaluation/example/runs/test-run:/evaluate:ro \
	  -v /absolute/path/to/rufes/tools/rufes-evaluation/example/data:/data \
	  -v /absolute/path/to/rufes/tools/rufes-evaluation/example/scores/test-run:/score \
	-it rufes-evaluation

* Note: modify the `/absolute/path/to` in the above command to reflect location of the rufes repository on your system.
~~~

Scoring output will be placed inside `example/scores/test-run`.

[top](#how-to-run-the-rufes-evaluation-pipeline)

# How to apply the docker on your run?

In order to run the docker on your run, you may run the following command:

~~~
make run-evaluation-pipeline \
  RUNID=your_run_id \
  GOLD=gold_filename \
  COREDOCS=coredocs_filename \
  HOST_INPUT_DIR=/absolute/path/to/your/run/directory \
  HOST_DATA_DIR=/absolute/path/to/data/directory \
  HOST_OUTPUT_DIR=/absolute/path/to/output/directory
~~~

Note, that you would need to make sure that the `gold_filename` is present inside the `HOST_DATA_DIR`.

Alternatively, you may run the following command:

~~~
docker run \
  --env RUNID=your_run_id \
  --env GOLD=gold_filename \
  --env COREDOCS=coredocs_filename \
  -v /absolute/path/to/your/run/directory:/evaluate:ro \
  -v /absolute/path/to/data/directory:/data \
  -v /absolute/path/to/output/directory:/score \
-it rufes-evaluation
~~~

[top](#how-to-run-the-rufes-evaluation-pipeline)

# Revision History

## 11/02/2022:
* Following new metrics (copies of other existing metrics) add in support of the leaderboard:

  ClusterTypesMetricV1 <- complete:ClusterTypesMetricV1
  MentionTypesMetricV1 <- complete:MentionTypesMetricV1
  b_cubed <- complete:b_cubed:fscore
  entity_ceaf <- complete:entity_ceaf:fscore
  mention_ceaf <- complete:mention_ceaf:fscore
  muc <- complete:muc:fscore
  pairwise <- complete:pairwise:fscore
  strong_mention_match <- complete:strong_mention_match:fscore
  strong_typed_mention_match <- complete:strong_typed_mention_match:fscore
  typed_mention_ceaf <- complete:typed_mention_ceaf:fscore

## 05/27/2021:
* Coredocs filtering added.
* Alternative ways to build and run docker added.

## 05/21/2021:
* Initial version.

[top](#how-to-run-the-rufes-evaluation-pipeline)
