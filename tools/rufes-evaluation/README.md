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

# How to run the docker on a test run?

An example run and corresponding scoring output has been placed respectively inside the directory named: `example/run/test-run` and `example/scores/test-run` .

In order to run the docker on the `test-run`, you may run the following command:

~~~
make run-example
~~~

Scoring output will be placed inside `example/scores/test-run`.

# How to apply the docker on your run?

In order to run the docker on your run, you may run the following command:

~~~
make run-evaluation-pipeline \
  RUNID=your_run_id \
  GOLD=gold_filename \
  HOST_INPUT_DIR=/absolute/path/to/your/run \
  HOST_DATA_DIR=/absolute/path/to/data/dir \
  HOST_OUTPUT_DIR=/absolute/path/to/output
~~~

Note, that you would need to make sure that the `gold_filename` is present inside the `HOST_DATA_DIR`.

[top](#how-to-run-the-rufes-evaluation-pipeline)

# Revision History

## 05/21/2021:
* Initial version.

[top](#how-to-run-the-rufes-evaluation-pipeline)
