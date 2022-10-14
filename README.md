# Introduction

October 14, 2022

This document describes the usage of the type metric score for RUFES track organized in sections given below:

1. Pre-requisites,
2. Latest version,
3. How to run the scorer,
4. How to run the scorer on a demo run,
5. How to read the scorer output,
6. How to read the log file,
7. Revision history

# Pre-requisites

In order to run the script you would need to:

~~~
* use python3.9,
* have python package Munkres installed (use `pip install munkres`).
~~~

# Latest version

The latest version of the code is `v2020.2.0` which can be found in branch: `TYPEMETRIC-v2020.2.0`.

# How to run the scorer

The main scoring script is at: `tools/scorer/score_submission.py`.

## Usage of the scorer

~~~
score_submission.py [-h] [-l LOG] [-r RUN] [-v] [-S {pretty,tab,space}] log_specifications gold system scores

Score RUFES output

positional arguments:
  log_specifications    File containing error specifications
  gold                  Input gold annotations file
  system                Input system response file
  scores                Output scores directory (note that this directory should not exist)

optional arguments:
  -h, --help            show this help message and exit
  -l LOG, --log LOG     Specify a file to which log output should be redirected (default: log.txt)
  -r RUN, --run RUN     Specify the run ID (default: runID)
  -v, --version         Print version number and exit
  -S {pretty,tab,space}, --separator {pretty,tab,space}
                        Column separator for scorer output? (default: pretty)
~~~

In order to run the scorer, you may use the following command:

~~~
cd tools/scorer
python3 score_submission.py -l logfile.txt -r yourRunID ../../input/log_specifications.txt /path/to/gold/annotations/file /path/to/system/output/file /path/to/scores/directory
~~~

# How to run the scorer on a demo run

In order to run the scorer over the (included) demo run, you may use the following command:

~~~
python score_submission.py -l ../../input/demo/log.txt -r demo ../../input/log_specifications.txt ../../input/demo/gold.tab ../../input/demo/system_output.tab ../../input/demo/scores/
~~~

# How to read the scorer output

The scorer produces the following scoring variants:

## ClusterTypesMetricV1

This variant uses all the types asserted on the cluster as a set, and uses this set to compute Precision, Recall and F1.

The scores corresponding to this variant can be found in file: `ClusterTypesMetricV1-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Entity ID
- Column # 4: System Entity ID
- Column # 5: Precision
- Column # 6: Recall
- Column # 7: F1

## ClusterTypesMetricV2

This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
* ranking is induced using weights on types, and
* the weights on a type is the number of mentions asserting that type.

The scores corresponding to this variant can be found in file: `ClusterTypesMetricV2-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Entity ID
- Column # 4: System Entity ID
- Column # 5: Average Precision

## ClusterTypesMetricV3

This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
* ranking is induced using weights on types, and
* the weight on a type is computed as the sum of confidences on mentions asserting that type.

The scores corresponding to this variant can be found in file: `ClusterTypesMetricV3-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Entity ID
- Column # 4: System Entity ID
- Column # 5: Average Precision

## MentionTypesMetricV1

This variant uses all the types asserted on a mention as a set, and uses this set to compute Precision, Recall and F1.

The scores corresponding to this variant can be found in file: `MentionTypesMetricV1-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Mention ID
- Column # 4: System Mention ID
- Column # 5: Precision
- Column # 6: Recall
- Column # 7: F1

## MentionTypesMetricV2

This variant of the scorer ranks the types asserted on a mention, and computes AP where:
* ranking is induced using weights on types, and
* the weights on a type is the number of mentions asserting that type.

The scores corresponding to this variant can be found in file: `MentionTypesMetricV2-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Mention ID
- Column # 4: System Mention ID
- Column # 5: Average Precision

## MentionTypesMetricV3

This variant of the scorer ranks the types asserted on a mention, and computes AP where:
* ranking is induced using weights on types, and
* the weight on a type is computed as the sum of confidences on mentions asserting that type.

The scores corresponding to this variant can be found in file: `MentionTypesMetricV3-scores.txt` which contains the following columns:

- Column # 1: Document ID
- Column # 2: Run ID
- Column # 3: Gold Mention ID
- Column # 4: System Mention ID
- Column # 5: Average Precision

# How to read the log file

The log file produced by the scorer generates the following types of entries:

## AP_INFO

This type of log entry contains information about the ranked list of types, their correctness, weights, and other information needed to compute AP.

## ALIGNMENT_INFO

This log entry contains information about which gold-entity was aligned to which system-entity, and the corresponding alignment similarity which is the number of matching mentions.

## SIMILARITY_INFO

This type of log entry contains the similarity information, and common mentions between a gold cluster, and a system cluster. This entry exists only if there is any similarity.

## ENTITY_TYPES_INFO

This log entry contains information about gold or system entity types provided and the expanded types used for scoring.

# Revision history

## 10/14/2022:
* Added new metrics
* Metric names changed

## 02/05/2021:
* Version # 2020.2.0 released in its own branch.
* Additional scoring variants added.

## 12/03/2020:
* Initial version.
