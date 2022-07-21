"""
The utility script for RUFES evaluation.
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "1.0.0.1"
__date__    = "20 July 2022"

import argparse
import os
import re
import sys
import textwrap
import traceback

from rufeslib import Logger
from rufeslib import Object
from tqdm import tqdm

ALLOK_EXIT_CODE = 0
ERROR_EXIT_CODE = 255

def check_paths(exist=[], donot_exist=[]):
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
    check_for_paths_existance(exist)
    check_for_paths_non_existance(donot_exist)

class GenerateSentenceBoundaries(Object):
    """
    Class for generating sentence boundaries.
    """
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            self.set(k, v)
        check_paths(exist=[self.get('ltf')], donot_exist=[self.get('output')])
        self.logger = Logger(self.get('logfile'), self.get('logspecs'), sys.argv)

    def __call__(self):
        def order(segment_id):
            elements = segment_id.split('-')
            p2 = int(elements.pop())
            p1 = '-'.join(elements)
            return [p1, p2]
        def tostring(fields, entry=None):
            values = []
            for fieldname in fields:
                value = fieldname
                if entry is not None:
                    value = str(entry.get(fieldname))
                values.append(value)
            return '\t'.join(values)
        ltfdir = self.get('ltf')
        sentence_boundaries = {}
        items = os.listdir(ltfdir)
        filenames = [i for i in items if i.endswith('.ltf.xml')]
        for document_id in tqdm(filenames):
            filepath = os.path.join(ltfdir, document_id)
            if os.path.isfile(filepath):
                sentence_boundaries[document_id] = {}
                with open(filepath) as fh:
                    running_offset, start_segment_offset, end_segment_offset, segment_id, start_char, end_char = [0,0,0,0,0,0]
                    for line in fh.readlines():
                        length = len(line)
                        line = line.strip()
                        m = re.match('^<SEG end_char="(\d+)" id="(.*?)" start_char="(\d+)">$', line)
                        if m:
                            start_segment_offset = running_offset
                            end_char, segment_id, start_char = [m.group(i) for i in [1, 2, 3]];
                        if re.match('^<\/SEG>$', line):
                            end_segment_offset = running_offset + length - 1;
                            sentence_boundaries[document_id][segment_id] = {
                                    'START_CHAR': start_char,
                                    'END_CHAR': end_char,
                                    'START_SEGMENT_OFFSET': start_segment_offset,
                                    'END_SEGMENT_OFFSET': end_segment_offset,
                                }
                        running_offset += length
        fields = ['document_id', 'segment_id', 'start_char', 'end_char', 'start_segment_offset', 'end_segment_offset']
        header = tostring(fields)
        lines = [header]
        for document_id in sentence_boundaries:
            for segment_id in sorted(sentence_boundaries.get(document_id), key=order):
                start_char, end_char, start_segment_offset, end_segment_offset = [sentence_boundaries.get(document_id).get(segment_id).get(fn) for fn in ['START_CHAR', 'END_CHAR', 'START_SEGMENT_OFFSET', 'END_SEGMENT_OFFSET']]
                entry = {'document_id': document_id,
                         'segment_id': segment_id,
                         'start_char': start_char,
                         'end_char': end_char,
                         'start_segment_offset': start_segment_offset,
                         'end_segment_offset': end_segment_offset}
                lines.append(tostring(fields, entry=entry))
        with open(self.get('output'), 'w') as program_output:
            program_output.write('\n'.join(lines))
        exit(ALLOK_EXIT_CODE)

    @classmethod
    def add_arguments(myclass, parser):
        parser.add_argument('-l', '--logfile', default='log.txt', help='Specify a file to which log output should be redirected (default: %(default)s)')
        parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, help='Print version number and exit')
        parser.add_argument('logspecs', type=str, help='File containing error specifications')
        parser.add_argument('ltf', type=str, help='Directory containing ltf files')
        parser.add_argument('output', type=str, help='Specify the file to which the output should be written')
        parser.set_defaults(myclass=myclass)
        return parser

myclasses = [
    GenerateSentenceBoundaries,
    ]

def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog='rufesutils',
                                description='RUFES main utility script')
    subparser = parser.add_subparsers()
    subparsers = {}
    for myclass in myclasses:
        hyphened_name = re.sub('([A-Z])', r'-\1', myclass.__name__).lstrip('-').lower()
        help_text = myclass.__doc__.split('\n')[0]
        desc = textwrap.dedent(myclass.__doc__.rstrip())

        class_subparser = subparser.add_parser(hyphened_name,
                            help=help_text,
                            description=desc,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
        myclass.add_arguments(class_subparser)
        subparsers[myclass] = class_subparser

    namespace = vars(parser.parse_args(args))
    try:
        myclass = namespace.pop('myclass')
    except KeyError:
        parser.print_help()
        return
    try:
        obj = myclass(**namespace)
    except ValueError as e:
        subparsers[myclass].error(str(e) + "\n" + traceback.format_exc())
    result = obj()
    if result is not None:
        print(result)

if __name__ == '__main__':
    main()