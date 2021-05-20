"""
Script for filtering lines from system response, and gold annotation.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "18 May 2021"

import argparse
import os

ALLOK_EXIT_CODE = 0
ERROR_EXIT_CODE = 255

def check_for_paths_existance(paths):
    for path in paths:
        if not os.path.exists(path):
            print('Error: Path {} does not exist'.format(path))
            exit(ERROR_EXIT_CODE)

def check_for_paths_non_existance(paths):
    for path in paths:
        if os.path.exists(path):
            print('Error: Path {} exists'.format(path))
            exit(ERROR_EXIT_CODE)

def filter_lines(filter_name, input_file, output_file):
    def check(line, filter_name):
        elements = line.split('\t')
        criteria = {
            'NAM': ['NAM'],
            'NOM': ['NOM'],
            'PRO': ['PRO'],
            'NAM-NOM': ['NAM', 'NOM'],
            'NAM-PRO': ['NAM', 'PRO'],
            'NOM-PRO': ['NOM', 'PRO']
            }
        if filter_name == 'complete':
            return True
        if elements[6] in criteria[filter_name]:
            return True
        return False
    program_output = open(output_file, 'w')
    with open(input_file) as fh:
        for line in fh.readlines():
            if check(line, filter_name):
                program_output.write(line)
    program_output.close()

def main(args):
    check_for_paths_existance([args.input])
    check_for_paths_non_existance([args.output])
    filter_lines(args.filter, args.input, args.output)
    exit(ALLOK_EXIT_CODE)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Script for filtering lines from system response, and gold annotation.")
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, help='Print version number and exit')
    parser.add_argument('filter', choices=['complete', 'NAM', 'NOM', 'PRO', 'NAM-NOM', 'NAM-PRO', 'NOM-PRO'], help='Specify the name of the filter to be applied')
    parser.add_argument('input', type=str, help='Specify the input file')
    parser.add_argument('output', type=str, help='Specify the output file')
    args = parser.parse_args()
    main(args)