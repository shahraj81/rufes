"""
Script for RUFES evaluation pipeline.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "18 May 2021"

from logger import Logger

import argparse
import datetime
import json
import os
import re
import sys

ALLOK_EXIT_CODE = 0
ERROR_EXIT_CODE = 255

EXPECTED_NUM_OF_TYPING_SCORE_FILES = 6

choices = ['complete', 'NAM', 'NOM', 'PRO', 'NAM-NOM', 'NAM-PRO', 'NOM-PRO']

def call_system(cmd):
    cmd = ' '.join(cmd.split())
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ": running system command: '{}'".format(cmd))
    os.system(cmd)

def get_problems(logs_directory):
    num_errors = 0
    stats = {}
    for filename in os.listdir(logs_directory):
        filepath = '{}/{}'.format(logs_directory, filename)
        fh = open(filepath)
        for line in fh.readlines():
            if 'ERROR' in line:
                num_errors += 1
                error_type = line.split('-')[3].strip()
                stats[error_type] = stats.get(error_type, 0) + 1
        fh.close()
    return num_errors, stats

def record_and_display_message(logger, message):
    print("----------------------------------------------------------")
    print(message)
    print("----------------------------------------------------------")
    logger.record_event('DEFAULT_INFO', message)

def get_leaderboard_metric_mapping(scores):
    mapping = {}
    for metric_name in scores:
        if metric_name.startswith('complete:'):
            new_metric_name = metric_name.replace('complete:', '')
            if new_metric_name in ['ClusterTypesMetricV1', 'MentionTypesMetricV1']:
                mapping[new_metric_name] = metric_name
            if new_metric_name.endswith(':fscore'):
                new_metric_name = new_metric_name.replace(':fscore', '')
                mapping[new_metric_name] = metric_name
    return mapping

def generate_results_file_and_exit(logger, logs_directory, exit_code=ALLOK_EXIT_CODE):
    if exit_code == ERROR_EXIT_CODE:
        exit_message = 'Error(s) encountered.'
        record_and_display_message(logger, exit_message)
        exit(exit_code)

    num_problems, problem_stats = get_problems(logs_directory)
    if num_problems:
        exit_code = ERROR_EXIT_CODE
        exit_message = 'Submission format validation error(s) encountered: {} errors'.format(num_problems)
        record_and_display_message(logger, exit_message)
        exit(exit_code)

    scores = {}
    for dir_name in choices:
        typing = []
        expected = EXPECTED_NUM_OF_TYPING_SCORE_FILES
        for filename in os.listdir(os.path.join(args.output, dir_name, 'typing')):
            if filename.endswith('-scores.txt'):
                typing.append(os.path.join(args.output, dir_name, 'typing', filename))
                expected -= 1
        if expected != 0:
            exit_code = ERROR_EXIT_CODE

        for filename in typing:
            metric_name = filename.split('/')[-1].split('-')[0]
            with open(filename) as fh:
                last_line = None
                for line in fh.readlines():
                    line = line.strip()
                    last_line = line
                if last_line.startswith('Summary'):
                    scores['{prefix}:{metric_name}'.format(prefix=filename.split('/')[2], metric_name=metric_name)] = float(last_line.split()[-1])
                else:
                    exit_code = ERROR_EXIT_CODE

        found = False
        for filename in os.listdir(os.path.join(args.output, dir_name)):
            if os.path.isfile(os.path.join(args.output, dir_name, filename)):
                if filename.endswith('.evaluation'):
                    with open(os.path.join(args.output, dir_name, filename)) as fh:
                        header = None
                        for line in fh.readlines():
                            line = line.strip()
                            if header is None:
                                header = line.split()
                            else:
                                entry = dict(zip(header, line.split()))
                                metric_names = [k for k in entry.keys() if k != 'measure']
                                for name in metric_names:
                                    if name not in ['precis', 'recall', 'fscore']: continue
                                    metric_name = '{prefix}:{measure}:{name}'.format(prefix=dir_name, measure=entry['measure'], name=name)
                                    scores[metric_name] = float(entry[name])
                                    found = True

        if not found:
            exit_code = ERROR_EXIT_CODE

    if exit_code == ERROR_EXIT_CODE:
        exit_message = 'Error(s) encountered.'
        record_and_display_message(logger, exit_message)
        exit(exit_code)

    fatal_error = 'Yes' if exit_code == ERROR_EXIT_CODE else 'No'
    scores['RunID'] = args.run
    scores['Errors'] = num_problems
    scores['ErrorStats'] = problem_stats
    scores['FatalError'] = fatal_error

    # add leaderboard specific metrics copies
    leaderboard_metric_mapping = get_leaderboard_metric_mapping(scores)
    for new_metric_name in leaderboard_metric_mapping:
        source_metric_name = leaderboard_metric_mapping[new_metric_name]
        scores[new_metric_name] = scores[source_metric_name]

    output = {'scores' : [
                            scores
                         ]
            }

    outputdir = "/score/"
    with open(outputdir + 'results.json', 'w') as fp:
        json.dump(output, fp, indent=4, sort_keys=True)

    exit_message = 'Done.'

    if num_problems:
        exit_code = ERROR_EXIT_CODE
    if exit_code == ERROR_EXIT_CODE:
        exit_message = 'Fatal error encountered.'
    record_and_display_message(logger, exit_message)

    exit(exit_code)

def main(args):

    #############################################################################################
    # check input/output directory for existence
    #############################################################################################
    print("Checking if input/output directories exist.")
    for path in [args.input, args.output]:
        if not os.path.exists(path):
            print('ERROR: Path {} does not exist'.format(path))
            exit(ERROR_EXIT_CODE)
    print("Checking if output directory is empty.")
    files = [f for f in os.listdir(args.output)]
    if len(files) > 0:
        print('ERROR: Output directory {} is not empty'.format(args.output))
        exit(ERROR_EXIT_CODE)

    #############################################################################################
    # create logger
    #############################################################################################

    logs_directory = '{output}/{logs}'.format(output=args.output, logs=args.logs)
    run_log_file = '{logs_directory}/run.log'.format(logs_directory=logs_directory)
    call_system('mkdir {logs_directory}'.format(logs_directory=logs_directory))
    logger = Logger(run_log_file, args.spec, sys.argv)

    #############################################################################################
    # inspect the input directory
    #############################################################################################

    record_and_display_message(logger, 'Inspecting the input directory.')
    items = [f for f in os.listdir(args.input)]

    num_files = 0
    num_directories = 0
    num_others = 0

    filename = None

    for item in items:
        if not item.endswith('.tab'):
            num_others += 1
        if item.startswith('.'):
            num_others += 1
        if os.path.isfile(os.path.join(args.input, item)):
            if item.endswith('.tab'):
                filename = re.match(r"^(.*?)\.tab$", item).group(1)
            else:
                num_others += 1
            num_files += 1
        elif os.path.isdir(os.path.join(args.input, item)):
            num_directories += 1

    if num_directories > 0 or num_others > 0 or num_files > 1:
        logger.record_event('UNEXPECTED_ITEM_FOUND')
        record_and_display_message(logger, 'Unexpected item found in input directory.')
        generate_results_file_and_exit(logger, logs_directory, exit_code=ERROR_EXIT_CODE)

    if num_files == 0:
        logger.record_event('NOTHING_TO_SCORE')
        record_and_display_message(logger, 'Nothing to score.')
        generate_results_file_and_exit(logger, logs_directory, exit_code=ERROR_EXIT_CODE)

    #############################################################################################
    # Copy system response file into appropriate location, apply coredocs filter and validate
    #############################################################################################

    record_and_display_message(logger, 'Copying system response file into appropriate location.')
    destination = '{output}/run-out'.format(output=args.output)
    call_system('mkdir {destination}'.format(destination=destination))
    call_system('cp -r {input}/{filename}.tab {destination}/{filename}-raw.tab'.format(input=args.input, filename=filename, destination=destination))

    # apply coredocs filter
    call_system('grep -f {data}/{coredocs} {destination}/{filename}-raw.tab > {destination}/{filename}-unvalidated.tab'.format(data=args.data, coredocs=args.coredocs, destination=destination, filename=filename))

    # validate responses
    validate_command = 'python rufesutils.py validate-responses \
                         -l {logs_directory}/validate-responses.log \
                         ./log_specifications.txt \
                         {data}/segment_boundaries.tab \
                         {data}/ontology_types.txt \
                         {destination}/{filename}-unvalidated.tab \
                         {destination}/{filename}.tab'
    call_system(validate_command.format(logs_directory=logs_directory, data=args.data, destination=destination, filename=filename))

    #############################################################################################
    # Copy gold annotations file into appropriate location and apply coredocs filter
    #############################################################################################

    gold_destination = '/gold'.format(output=args.output)
    gold_filename =  re.match(r"^(.*?)\.tab$", args.gold).group(1)
    record_and_display_message(logger, 'Copying gold annotations file into appropriate location.')
    destination = '{gold_destination}'.format(gold_destination=gold_destination)
    call_system('mkdir {destination}'.format(destination=destination))
    call_system('cp -r {data}/{gold_filename}.tab {destination}/{gold_filename}-raw.tab'.format(data=args.data, gold_filename=gold_filename, destination=destination))

    # apply coredocs filter
    call_system('grep -f {data}/{coredocs} {destination}/{gold_filename}-raw.tab > {destination}/{gold_filename}.tab'.format(data=args.data, coredocs=args.coredocs, gold_filename=gold_filename, destination=destination))

    #############################################################################################
    # Generate filtered data
    #############################################################################################

    record_and_display_message(logger, 'Generating filtered data.')
    destination = '{output}'.format(output=args.output)
    for filter_name in choices:

        filter_destination = '{output}/{filter_name}'.format(output=args.output, filter_name=filter_name)
        call_system('mkdir {filter_destination}'.format(filter_destination=filter_destination))

        filter_gold_destination = '{gold_destination}/{filter_name}'.format(gold_destination=gold_destination, filter_name=filter_name)
        call_system('mkdir {filter_gold_destination}'.format(filter_gold_destination=filter_gold_destination))

        call_system('python filter.py {filter_name} {output}/run-out/{filename}.tab {output}/{filter_name}/{filename}.tab'.format(filter_name=filter_name,
                                                                                                                                  output=args.output,
                                                                                                                                  filename=filename))
        call_system('python filter.py {filter_name} {gold_destination}/{gold_filename}.tab {filter_gold_destination}/{gold_filename}.tab'.format(filter_name=filter_name,
                                                                                                                                         output=args.output,
                                                                                                                                         gold_destination=gold_destination,
                                                                                                                                         filter_gold_destination=filter_gold_destination,
                                                                                                                                         gold_filename=gold_filename))
        call_system('cat {output}/{filter_name}/{filename}.tab | perl genTSV.pl > {output}/{filter_name}/{filename}.combined.tsv'.format(filter_name=filter_name,
                                                                                                                                output=args.output,
                                                                                                                                filename=filename))
        call_system('cat {filter_gold_destination}/{gold_filename}.tab | perl genTSV.pl > {filter_gold_destination}/{gold_filename}.tsv'.format(filter_name=filter_name,
                                                                                                                                          filter_gold_destination=filter_gold_destination,
                                                                                                                                          gold_filename=gold_filename))

    #############################################################################################
    # Score filtered data directories 
    #############################################################################################

    record_and_display_message(logger, 'Scoring filtered data.')
    for filter_name in choices:
        destination = '{output}/{filter_name}'.format(output=args.output, filter_name=filter_name)
        filter_gold_destination = '{gold_destination}/{filter_name}'.format(gold_destination=gold_destination, filter_name=filter_name)
        score_command = 'python score_submission.py -l {logs_directory}/{filter_name}.log -r {runid} ./log_specifications.txt {filter_gold_destination}/{gold_filename}.tab {destination}/{filename}.tab {destination}/typing'
        call_system(score_command.format(logs_directory=logs_directory, filter_name=filter_name, runid=args.run, filter_gold_destination=filter_gold_destination, gold_filename=gold_filename, destination=destination, filename=filename))

        score_command = "neleval evaluate -m strong_mention_match -m strong_typed_mention_match -m mention_ceaf  -m typed_mention_ceaf -m entity_ceaf -m b_cubed -m muc -m pairwise -f 'tab' "
        score_command += "-g {filter_gold_destination}/{gold_filename}.tsv {destination}/{filename}.combined.tsv > {destination}/{filename}.evaluation"
        call_system(score_command.format(filter_gold_destination=filter_gold_destination, gold_filename=gold_filename, destination=destination, filename=filename))
    generate_results_file_and_exit(logger, logs_directory)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the RUFES evaluation pipeline.")
    parser.add_argument('-c', '--coredocs', default='coredocs.txt', help='Specify the name of the coredocs file placed inside the data directory (default: %(default)s)')
    parser.add_argument('-d', '--data', default='/data', help='Specify the data directory (default: %(default)s)')
    parser.add_argument('-g', '--gold', default='gold.tab', help='Specify the name of the gold annotation data file placed inside the data directory (default: %(default)s)')
    parser.add_argument('-i', '--input', default='/evaluate', help='Specify the input directory (default: %(default)s)')
    parser.add_argument('-l', '--logs', default='logs', help='Specify the name of the logs directory to which different log files should be written (default: %(default)s)')
    parser.add_argument('-o', '--output', default='/score', help='Specify the input directory (default: %(default)s)')
    parser.add_argument('-r', '--run', default='system', help='Specify the run name (default: %(default)s)')
    parser.add_argument('-s', '--spec', default='/scripts/log_specifications.txt', help='Specify the log specifications file (default: %(default)s)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__,  help='Print version number and exit')
    args = parser.parse_args()
    main(args)