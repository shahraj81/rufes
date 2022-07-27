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

from rufeslib import FileHandler, FileHeader, RUFESObject, TextBoundaries, Normalizer, Validator
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

class GenerateSegmentBoundaries(RUFESObject):
    """
    Class for generating segment boundaries.
    """
    def __init__(self, **kwargs):
        check_paths(exist=[kwargs.get('logspecs'), kwargs.get('ltf')], donot_exist=[kwargs.get('output')])
        super().__init__(**kwargs)

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
        segment_boundaries = {}
        items = os.listdir(ltfdir)
        filenames = [i for i in items if i.endswith('.ltf.xml')]
        for filename in tqdm(filenames):
            document_id = filename.replace('.ltf.xml', '')
            filepath = os.path.join(ltfdir, document_id)
            if os.path.isfile(filepath):
                segment_boundaries[document_id] = {}
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
                            segment_boundaries[document_id][segment_id] = {
                                    'START_CHAR': start_char,
                                    'END_CHAR': end_char,
                                    'START_SEGMENT_OFFSET': start_segment_offset,
                                    'END_SEGMENT_OFFSET': end_segment_offset,
                                }
                        running_offset += length
        fields = ['document_id', 'segment_id', 'start_char', 'end_char', 'start_segment_offset', 'end_segment_offset']
        header = tostring(fields)
        lines = [header]
        for document_id in sorted(segment_boundaries):
            for segment_id in sorted(segment_boundaries.get(document_id), key=order):
                start_char, end_char, start_segment_offset, end_segment_offset = [segment_boundaries.get(document_id).get(segment_id).get(fn) for fn in ['START_CHAR', 'END_CHAR', 'START_SEGMENT_OFFSET', 'END_SEGMENT_OFFSET']]
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

class ValidateResponses(RUFESObject):
    """
    Validating responses (or gold annotations) file.
    """

    schemas = {
        'TAC2020': {
            'columns': ['run_id', 'mention_id', 'mention_string', 'mention_span', 'entity_id', 'entity_types', 'mention_type', 'confidence'],
            }
        }

    attributes = {
        'confidence': {
            'name': 'confidence',
            'validate': 'validate_confidence'
            },
        'entity_id': {
            'name': 'entity_id',
            },
        'entity_types': {
            'name': 'entity_types',
            'validate': 'validate_entity_types',
            },
        'mention_id': {
            'name': 'mention_id',
            },
        'mention_span': {
            'name': 'mention_span',
            'normalize': 'normalize_mention_span',
            'validate': 'validate_mention_span',
            },
        'mention_string': {
            'name': 'mention_string',
            },
        'mention_type': {
            'name': 'mention_type',
            'validate': 'validate_mention_type',
            },
        'run_id': {
            'name': 'run_id',
            'validate': 'validate_run_id',
            },
        }

    def __init__(self, **kwargs):
        check_paths(exist=[kwargs.get('logspecs'), kwargs.get('segment_boundaries'), kwargs.get('input')], donot_exist=[kwargs.get('output')])
        super().__init__(**kwargs)
        self.normalizer = Normalizer(self.get('logger'))
        self.validator = Validator(self.get('logger'))

    def __call__(self):
        # the entrypoint method
        def validate(self, schema, entry, columns, data):
            # the method for validating an entry (i.e. a line in responses or gold file)
            valid = True
            # normalize and validate all fields in the entry
            for column_name in columns:
                column_spec = self.attributes[column_name]
                normalizer_name = column_spec.get('normalize')
                if normalizer_name:
                    self.get('normalizer').normalize(self, normalizer_name, entry, self.attributes[column_name])
                validator_name = column_spec.get('validate')
                if validator_name:
                    valid_attribute = self.get('validator').validate(self, validator_name, schema, entry, self.attributes[column_name], data)
                if normalizer_name:
                    self.get('normalizer').normalize(self, normalizer_name, entry, self.attributes[column_name], undo=True)
                if not valid_attribute:
                    valid = False
            return valid
        logger = self.get('logger')
        # load allowed entity types
        allowed_entity_types = [e.get('type') for e in FileHandler(logger, self.get('ontology_types'), header=FileHeader(logger, 'type'))]
        # load text boundaries
        text_boundaries = TextBoundaries(logger, self.get('segment_boundaries'))
        # initialize allowed mention types
        allowed_mention_types = ['NAM', 'NOM', 'PRO']
        data = {'allowed_entity_types': allowed_entity_types,
                'allowed_mention_types': allowed_mention_types,
                'text_boundaries': text_boundaries}
        schema = self.get('schema')
        columns = schema.get('columns')
        header = FileHeader(logger, '\t'.join(columns))
        # read input file
        entries = FileHandler(logger, self.get('input'), header=header, encoding='utf-8')
        with open(self.get('output'), 'w') as program_output:
            # validate all entries
            for entry in entries:
                valid = True
                valid_attribute = validate(self, schema, entry, columns, data)
                if not valid_attribute: valid = False
                entry.set('valid', valid)
                # write entry to output file if it is valid
                if valid:
                    program_output.write(entry.__str__())
        self.record_event('DEFAULT_INFO', 'Execution ends')

    def get_schema(self):
        return self.schemas.get('TAC2020')

    @classmethod
    def add_arguments(myclass, parser):
        parser.add_argument('-l', '--logfile', default='log.txt', help='Specify a file to which log output should be redirected (default: %(default)s)')
        parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, help='Print version number and exit')
        parser.add_argument('logspecs', type=str, help='File containing error specifications')
        parser.add_argument('segment_boundaries', type=str, help='File containing segment boundaries information.')
        parser.add_argument('ontology_types', type=str, help='File containing list of valid ontology types.')
        parser.add_argument('input', type=str, help='File to be validated.')
        parser.add_argument('output', type=str, help='Specify the file to which the validated output should be written')
        parser.set_defaults(myclass=myclass)
        return parser

myclasses = [
    GenerateSegmentBoundaries,
    ValidateResponses,
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