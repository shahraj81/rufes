"""
Score RUFES output
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "v2020.0.1"
__date__    = "2 December 2020"

import argparse
import logging
import os
import re
import sys
import traceback

from inspect import currentframe, getouterframes
from munkres import Munkres

ALLOK_EXIT_CODE = 0
ERROR_EXIT_CODE = 255

def multisort(xs, specs):
    for key, reverse in reversed(specs):
        xs.sort(key=lambda x: x.get(key), reverse=reverse)
    return xs

def expanded_types(entity_types):
    def expand(entity_type):
        """
        If the type is:
            'A.B.C' return ['A', 'A.B', 'A.B.C']
            'A.B'   return ['A', 'A.B']
            'A'     return ['A']
        """
        metatype = 'Entity'
        expanded_types = {}
        elements = entity_type.split('.')
        for end_index in range(len(elements)):
            if metatype != 'Entity' and end_index == 0: continue
            start_index = 0
            expanded_type_elements = []
            while start_index <= end_index:
                expanded_type_elements.append(elements[start_index])
                start_index += 1
            if len(expanded_type_elements):
                expanded_types['.'.join(expanded_type_elements)] = 1
        return list(expanded_types.keys())
    expanded_types = set()
    for entity_type in entity_types:
        for expanded_type in expand(entity_type):
            expanded_types.add(expanded_type)
    return expanded_types

def parse_entries(entries, cluster_id_columnname):
        parsed_entries = {}
        for entry in entries:
            document_id = entry.get('mention_span').split(':')[0]
            entity_id = entry.get(cluster_id_columnname)
            if document_id not in parsed_entries:
                parsed_entries[document_id] = {}
            if entity_id not in parsed_entries[document_id]:
                parsed_entries[document_id][entity_id] = []
            parsed_entries[document_id][entity_id].append(entry)
        return parsed_entries

class Object(object):
    """
    This class represents an AIDA object which is envisioned to be the parent of most of the AIDA related classes.
    
    At a high level this class is a wrapper around a single dictionary object which provides support for complex getters.
    """

    def __init__(self, logger):
        """
        Initializes this instance, and sets the logger for newly created instance.

        Arguments:
            logger (aida.Logger):
                the aida.Logger object
        """
        self.logger = logger
            
    def get(self, *args, **kwargs):
        """
        Gets the value for the key using the given args.

        If method get_{key} is defined for this object, call that method with
        args as its arguments, and return what it returns, otherwise if there
        is an attribute whose name matches the value stored in key then return
        it. None is returned otherwise.
        """
        key = args[0]
        if key is None:
            self.get('logger').record_event('KEY_IS_NONE', self.get('code_location'))
        method = self.get_method("get_{}".format(key))
        if method is not None:
            args = args[1:]
            return method(*args, **kwargs)
        else:
            value = getattr(self, key, None)
            return value

    def get_method(self, method_name):
        """
        Returns the method whose name matches the value stored in method_name,
        None otherwise.
        """
        try:
            method = getattr(self, method_name)
            if not hasattr(method, "__call__"):
                raise AttributeError()
        except AttributeError:
            method = None
        return method
    
    def get_code_location(self):
        """
        Returns the filename and line number where this method is called.

        Used for recording an event in the logger.

        The return value is a dictionary with the following two keys:
            filename
            lineno
        """
        caller_frame_info = getouterframes(currentframe(), 2)[2]
        where = {'filename': caller_frame_info.filename, 'lineno': caller_frame_info.lineno}
        return where

    def record_event(self, event_code, *args):
        """
        Record an event in the log.

        Arguments:
            event_code (str):
                the name of the event.
            args:
                the arguments that are passed to the logger's record_event method.
        """
        self.get('logger').record_event(event_code, *args)

    def set(self, key, value):
        """
        Sets the value of an attribute, of the current, whose name matches the value stored in key.
        """
        setattr(self, key, value)

class Container(Object):
    """
    The container class.

    Internally, the instance of this class stores objects in a dictionary.
    """

    def __init__(self, logger):
        """
        Initializes this instance, and sets the logger for newly created instance.

        This is where the empty store is initialized.

        Arguments:
            logger (aida.Logger):
                the aida.Logger object
        """
        super().__init__(logger)
        self.store = {}

    def __iter__(self):
        """
        Returns the iterator over the store.
        """
        return iter(self.store)

    def get(self, *args, **kwargs):
        """
        Gets the value for the key using the given args, if found. Returns None otherwise.

        The value is looked up first in the parent object, returned if found. Otherwise,
        the value is looked up in the store, again returned if found. Otherwise, the
        key is added, to the store, with its value set to the default value provided
        or None, if no default value was provided.
        """
        key = args[0]
        default = kwargs['default'] if 'default' in kwargs else None
        value = super().get(*args, **kwargs)
        if value:
            return value
        elif key in self.store:
            return self.store[key]
        else:
            if value is None and default is not None:
                value = default
                self.add(key=key, value=value)
            return value

    def set(self, key, value):
        """
        Sets the value of the key in the store if key is found in the store, otherwise,
        the object's setter is called.
        """
        if key in self.store:
            self.store[key] = value
        else:
            super().set(key, value)

    def exists(self, key):
        """
        Returns True if key is found in the store, False otherwise.
        """
        return key in self.store

    def add(self, value, key=None):
        """
        Adds the value to the store and map it to the key if provided, otherwise,
        use the length of the store as the key.
        """
        if key is None:
            self.store[len(self.store)] = value
        else:
            self.store[key] = value

    def add_member(self, member):
        """
        Add a member to the container using the member.get('ID') as the key corresponding
        to which the member is stored.
        """
        if member.get('ID') not in self:
            self.add(key=member.get('ID'), value=member)
        else:
            self.logger.record_event('DUPLICATE_VALUE', member.get('ID'), member.get('where'))

    def keys(self):
        """
        Returns a new view of the store's keys.
        """
        return self.store.keys()

    def values(self):
        """
        Returns a new view of the store's values.
        """
        return self.store.values()

class Entry(Object):
    """
    The Entry represents a line in a tab separated file.
    """

    def __init__(self, logger, keys, values, where):
        """
        Initializes this instance.

        Arguments:
            logger (aida.Logger):
                the aida.Logger object.
            keys (list of str):
                the list representing header fields.
            values (list of str):
                the list representing values corresponding to the keys.
            where (dict):
                a dictionary containing the following two keys representing the file location:
                    filename
                    lineno

        NOTE: The length of keys and values must match.
        """
        super().__init__(logger)
        if len(keys) != len(values):
            logger.record_event('UNEXPECTED_NUM_COLUMNS', len(keys), len(values), where)
        self.where = where
        for i in range(len(keys)):
            self.set(keys[i], values[i].strip())

    def get_filename(self):
        """
        Gets the name of the file which this instance corresponds to.
        """
        return self.get('where').get('filename')
    
    def get_lineno(self):
        """
        Gets the line number which this instance corresponds to.
        """
        return self.get('where').get('lineno')

    def __str__(self):
        return '{}\n'.format('\t'.join([self.get(column) for column in self.get('schema').get('columns')]))

class FileHandler(Object):
    """
    File handler for reading tab-separated files.
   """

    def __init__(self, logger, filename, header=None, encoding=None):
        """
        Initializes this instance.
        Arguments:
            logger (aida.Logger):
                the aida.Logger object
            filename (str):
                the name of the file including the path
            header (aida.Header or None):
                if provided, this header will be used for the file,
                otherwise the header will be read from the first line.
            encoding (str or None):
                the encoding to be used for opening the file.
        """
        super().__init__(logger)
        self.encoding = encoding
        self.filename = filename
        self.header = header
        self.logger = logger
        # lines from the file are read into entries (aida.Entry)
        self.entries = []
        self.load_file()
    
    def load_file(self):
        """
        Load the file.
        """
        with open(self.get('filename'), encoding=self.get('encoding')) as file:
            for lineno, line in enumerate(file, start=1):
                if self.get('header') is None:
                    self.header = FileHeader(self.get('logger'), line.rstrip())
                else:
                    where = {'filename': self.get('filename'), 'lineno': lineno}
                    entry = Entry(self.get('logger'), self.get('header').get('columns'),
                                   line.rstrip('\r\n').split('\t', len(self.get('header').get('columns'))-1), where)
                    entry.set('where', where)
                    entry.set('header', self.get('header'))
                    entry.set('line', line)
                    self.get('entries').append(entry)
    
    def __iter__(self):
        """
        Returns iterator over entries.
        """
        return iter(self.get('entries'))

class FileHeader(Object):
    """
    The object represending the header of a tab separated file.
    """

    def __init__(self, logger, header_line):
        """
        Initializes the FileHeader using header_line.

        Arguments:
            logger (aida.Logger):
                the aida.Logger object.
            header_line (str):
                the line used to generate the FileHeader object.
        """
        super().__init__(logger)
        self.logger = logger
        self.line = header_line
        self.columns = list(re.split(r'\t', header_line))
    
    def __str__(self, *args, **kwargs):
        """
        Returns the string representation of the header.
        """
        return self.get('line')

class Logger:
    """
    A wrapper around the Python 'logging' module which is internally used to
    record events of interest.
    """
    
    # the dictionary used to store event specifications for recording log events
    # the content of this dictionary are read from file: event_specs_filename
    event_specs = {}
    num_errors = 0
    num_warnings = 0
    
    def __init__(self, log_filename, event_specs_filename, argv, debug_level=logging.DEBUG):
        """
        Initialize the logger object.
        
        Arguments:
            log_filename (str):
                Name of the file to which log output is written
            event_specs_filename (str):
                Name of the file containing events handled by the logger
            argv (list):
                sys.argv as received by the invoking script
            debug_level (logging.LEVEL, OPTIONAL):
                Minimum logging.LEVEL to be reported.
                LEVEL is [CRITICAL|ERROR|WARNING|INFO|DEBUG].
                Default debug level is logging.DEBUG.
                The 'logging' module defines the following weights to different levels:
                    CRITICAL = 50
                    FATAL = CRITICAL
                    ERROR = 40
                    WARNING = 30
                    WARN = WARNING
                    INFO = 20
                    DEBUG = 10
                    NOTSET = 0
        """
        
        self.log_filename = log_filename
        self.event_specs_filename = event_specs_filename
        self.path_name = os.getcwd()
        self.file_name = argv[0]
        self.arguments = " ".join(argv[1:])
        self.script_codename = self.file_name
        self.debug_level = debug_level
        self.logger_object = logging.getLogger(self.file_name)
        self.configure_logger()
        self.record_program_invokation()
        self.load_event_specs()
        
    def configure_logger(self):
        """
        Set the output file of the logger, the debug level, format of log output, and
        format of date and time in log output.
        """
        logging.basicConfig(filename=self.log_filename, 
                            encoding='utf-8',
                            level=self.debug_level,
                            format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
    
    def get_logger(self):
        """
        Returns the logger object which can be used for recording events.
        """
        return self.logger_object

    def get_num_errors(self):
        """
        Returns the number of errors encountered.
        """
        return self.num_errors
    
    def get_num_warnings(self):
        """
        Returns the number of warnings encountered.
        """
        return self.num_warnings
    
    def get_stats(self):
        """
        Return a tuple (num_warnings, num_errors)
        """
        return (self.num_warnings, self.num_errors)

    def load_event_specs(self):
        """
        Load specifications of events that the logger supports.
        """
        with open(self.event_specs_filename, 'r') as event_specs_file:
            lines = event_specs_file.readlines()
        header = lines[0].strip().split(None, 2)
        for line in lines[1:]:
            line_dict = dict(zip(header, line.strip().split(None, 2)))
            self.event_specs[line_dict['code']] = line_dict

    def record_event(self, event_code, *args):
        """
        Record an event.
        
        The method can be called as:
            record_event(EVENT_CODE)
            record_event(EVENT_CODE, ARG1, ...)
            record_event(EVENT_CODE, WHERE)
            record_event(EVENT_CODE, ARG1, ARG2, ..., ARGN, WHERE)
        
        WHERE is always the last argument, and is optional. It is expected to be a dictionary 
        containing two keys: 'filename' and 'lineno'.
        
        EVENT_CODE is used to lookup an event object which is a dictionary containing the following
        keys: TYPE, CODE and MESSAGE.
        
        TYPE can have one of the following values: CRITICAL, DEBUG, ERROR, INFO, and WARNING.
        
        CODE is a unique ID of an event.
         
        MESSAGE is the message written to the log file. It has zero or more arguments to be filled 
        by ARG1, ARG2, ...
        """
        argslst = []
        where = None
        if len(args):
            argslst = list(args)
            if isinstance(argslst[-1], dict):
                where = argslst.pop()
        if event_code in self.event_specs:
            event_object = self.event_specs[event_code]
            event_type = event_object['type']
            event_message = event_object['message'].format(*argslst)
            event_message = '{code} - {message}'.format(code=event_code, message=event_message)
            if where is not None:
                event_message += " at " + where['filename'] + ":" + str(where['lineno'])
            if event_type.upper() == "CRITICAL":
                self.logger_object.critical(event_message + "\n" + "".join(traceback.format_stack()))
                sys.exit(event_message + "\n" + "".join(traceback.format_stack()))
            elif event_type.upper() == "DEBUG":
                self.logger_object.debug(event_message)
            elif event_type.upper() == "ERROR":
                self.logger_object.error(event_message)
                self.num_errors = self.num_errors + 1
            elif event_type.upper() == "INFO":
                self.logger_object.info(event_message)
            elif event_type.upper() == "WARNING":
                self.logger_object.warning(event_message)
                self.num_warnings = self.num_warnings + 1
            else:
                error_message = "Unknown event type '" + event_type + "' for event: " + event_code
                self.logger_object.error(error_message + "\n" + "".join(traceback.format_stack()))
                sys.exit(error_message + "\n" + "".join(traceback.format_stack()))
        else:
            error_message = "Unknown log event: " + event_code
            self.logger_object.error(error_message + "\n" + "".join(traceback.format_stack()))
            sys.exit(error_message + "\n" + "".join(traceback.format_stack()))

    def record_program_invokation(self):
        """
        Record how this program was invoked.
        """
        debug_message = "Execution begins {current_dir:" + self.path_name + ", script_name:" + self.file_name + ", arguments:" + self.arguments +"}"
        self.logger_object.info(debug_message)

class Alignment(Object):
    """
    Class for performing alignment, and supporting lookup.
    """

    def __init__(self, logger, gold, system, cluster_by_columnname):
        super().__init__(logger)
        self.cluster_by_columnname = cluster_by_columnname
        self.gold = gold
        self.system = system
        self.document_alignment = {}
        self.align_clusters()

    def get_parsed_entries(self, entries):
        return(parse_entries(entries, self.get('cluster_by_columnname')))

    def align_clusters(self):
        def get_max_similarity(similarities):
            max_similarity = -1 * sys.maxsize
            for i in similarities:
                for j in similarities[i]:
                    if similarities[i][j] > max_similarity:
                        max_similarity = similarities[i][j]
            return max_similarity
        def get_cost_matrix(similarities, mappings):
            def conditional_transpose(cost_matrix):
                m = {}
                rm = {}
                row_index = 0
                col_index = 0
                is_transposed = False
                for row in cost_matrix:
                    row_index = 0
                    for value in row:
                        if row_index not in m:
                            m[row_index] = {}
                        m[row_index][col_index] = value
                        row_index += 1
                    col_index += 1
                if col_index >= row_index:
                    return is_transposed, cost_matrix
                else:
                    is_transposed = True
                    transposed_matrix = []
                    for row_index in sorted(m):
                        transposed_matrix_row = []
                        for col_index in sorted(m[row_index]):
                            transposed_matrix_row += [m[row_index][col_index]]
                        transposed_matrix += [transposed_matrix_row]
                    return is_transposed, transposed_matrix
            max_similarity = get_max_similarity(similarities)
            cost_matrix = []
            for gold_index in sorted(mappings['gold']['index_to_id']):
                cost_row = []
                gold_id = mappings['gold']['index_to_id'][gold_index]
                for system_index in sorted(mappings['system']['index_to_id']):
                    system_id = mappings['system']['index_to_id'][system_index]
                    similarity = 0
                    if gold_id in similarities and system_id in similarities[gold_id]:
                        similarity = similarities[gold_id][system_id]
                    cost_row += [max_similarity - similarity]
                cost_matrix += [cost_row]
            return conditional_transpose(cost_matrix)
        def get_alignment(similarities, mappings):
            alignment = {'gold_to_system': {}, 'system_to_gold': {}}
            if len(similarities) > 0:
                is_transposed, cost_matrix = get_cost_matrix(similarities, mappings)
                for gold_entity_index, system_entity_index in Munkres().compute(cost_matrix):
                    if is_transposed:
                        temp = gold_entity_index
                        gold_entity_index = system_entity_index
                        system_entity_index = temp
                    gold_entity_id = mappings['gold']['index_to_id'][gold_entity_index]
                    system_entity_id = mappings['system']['index_to_id'][system_entity_index]
                    similarity = similarities[gold_entity_id][system_entity_id]
                    if similarity > 0:
                        alignment.get('gold_to_system')[gold_entity_id] = {
                                'aligned_to': system_entity_id,
                                'aligned_similarity': similarity
                            }
                        alignment.get('system_to_gold')[system_entity_id] = {
                                'aligned_to': gold_entity_id,
                                'aligned_similarity': similarity
                            }
            return alignment
        annotations = self.get('parsed_entries', self.get('gold').get('entries'))
        responses = self.get('parsed_entries', self.get('system').get('entries'))
        document_alignment = self.get('document_alignment')
        for document_id in annotations:
            data = {
                'gold': annotations.get(document_id),
                'system': responses.get(document_id, [])
                }
            similarities = {}
            for gold_entity_id in data['gold']:
                for system_entity_id in data['system']:
                    if gold_entity_id not in similarities:
                        similarities[gold_entity_id] = {}
                    if system_entity_id not in similarities[gold_entity_id]:
                        similarities[gold_entity_id][system_entity_id] = 0
                    gold_mention_spans = set([e.get('mention_span') for e in data['gold'][gold_entity_id]])
                    system_mention_spans = set([e.get('mention_span') for e in data['system'][system_entity_id]])
                    common_mentions = gold_mention_spans.intersection(system_mention_spans)
                    similarity = len(common_mentions)
                    similarities[gold_entity_id][system_entity_id] = similarity
                    if similarity > 0:
                        self.record_event('SIMILARITY_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, similarity, ';'.join(common_mentions))
            mappings = {}
            for gold_or_system in ['gold', 'system']:
                mappings[gold_or_system] = {'id_to_index': {}, 'index_to_id': {}}
                index = 0;
                for entity_id in sorted(data[gold_or_system]):
                    mappings[gold_or_system]['id_to_index'][entity_id] = index
                    mappings[gold_or_system]['index_to_id'][index] = entity_id
                    index += 1
            document_alignment[document_id] = get_alignment(similarities, mappings)

class Score(Object):
    """
    AIDA base class for query-specific derived score class.
    """
    def __init__(self, logger):
        super().__init__(logger)

class ScorePrinter(Container):
    """
    The score printer.
    """

    separators = {
        'pretty': None,
        'tab': '\t',
        'space': ' '
        }

    def __init__(self, logger, printing_specs, separator=None):
        super().__init__(logger)
        self.printing_specs = printing_specs
        self.separator = separator
        self.widths = {column.get('name'):len(column.get('header')) for column in printing_specs}
        self.lines = []

    def prepare_lines(self):
        widths = self.get('widths')
        scores = self.values()
        for score in scores:
            elements_to_print = {}
            for field in self.printing_specs:
                field_name = field.get('name')
                value = score.get(field_name)
                format_spec = field.get('mean_format') if score.get('summary') and field.get('mean_format') else field.get('format')
                text = '{0:{1}}'.format(value, format_spec)
                elements_to_print[field_name] = text
                widths[field_name] = len(text) if len(text)>widths[field_name] else widths[field_name]
            self.get('lines').append(elements_to_print)

    def get_header_text(self):
        return self.get_line_text()

    def get_line_text(self, line=None):
        text = ''
        separator = ''
        for field in self.printing_specs:
            text += separator
            field_name = field.get('name')
            value = line.get(field_name) if line is not None else field.get('header')
            num_spaces = 0 if self.separators[self.get('separator')] is not None else self.widths[field_name] - len(str(value))
            spaces_prefix = ' ' * num_spaces if field.get('justify') == 'R' and self.separators[self.get('separator')] is None else ''
            spaces_postfix = ' ' * num_spaces if field.get('justify') == 'L' and self.separators[self.get('separator')] is None else ''
            text = '{}{}{}{}'.format(text, spaces_prefix, value, spaces_postfix)
            separator = ' ' if self.separators[self.get('separator')] is None else self.separators[self.get('separator')]
        return text
    
    def __str__(self):
        self.prepare_lines()
        string = self.get_header_text()
        for line in self.get('lines'):
            string = '{}\n{}'.format(string, self.get_line_text(line))
        return string

class Scorer(Object):
    """
    The Scorer class.
    """

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger)
        self.separator = separator
        for key in kwargs:
            self.set(key, kwargs[key])
        self.separator = separator
        self.score_responses()

    def print_scores(self, filename):
        fh = open(filename, 'w')
        fh.write(self.__str__())
        fh.close()

    def __str__(self):
        return self.get('scores').__str__()

class TypeMetricScoreV1(Score):
    """
    AIDA class for type metric score corresponding to the TypeMetricScorerV1.
    """
    def __init__(self, logger, run_id, document_id, gold_entity_id, system_entity_id, precision, recall, f1, summary=False):
        super().__init__(logger)
        self.run_id = run_id
        self.document_id = document_id
        self.gold_entity_id = gold_entity_id if gold_entity_id is not None else 'None'
        self.system_entity_id = system_entity_id if system_entity_id is not None else 'None'
        self.precision = precision
        self.recall = recall
        self.f1 = f1
        self.summary = summary

class TypeMetricScorerV1A(Scorer):
    """
    Class for variant # 1A of the type metric scores.

    This variant of the scorer considers all types asserted on the cluster as a set, and uses this set to compute
    precision, recall and F1.
    
    Clustering is based on entity_id.
    """

    printing_specs = [{'name': 'document_id',      'header': 'DocID',           'format': 's',    'justify': 'L'},
                      {'name': 'run_id',           'header': 'RunID',           'format': 's',    'justify': 'L'},
                      {'name': 'gold_entity_id',   'header': 'GoldEntityID',    'format': 's',    'justify': 'L'},
                      {'name': 'system_entity_id', 'header': 'SystemEntityID',  'format': 's',    'justify': 'L'},
                      {'name': 'precision',        'header': 'Prec',            'format': '6.4f', 'justify': 'R', 'mean_format': 's'},
                      {'name': 'recall',           'header': 'Recall',          'format': '6.4f', 'justify': 'R', 'mean_format': 's'},
                      {'name': 'f1',               'header': 'F1',              'format': '6.4f', 'justify': 'R', 'mean_format': '6.4f'}]

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def order(self, k):
        return k

    def get_alignment(self):
        return self.get('cluster_alignment')

    def get_cluster_by_columnname(self):
        return 'entity_id'

    def get_document_scores(self, document_id, document_annotations, document_responses, document_alignment):
        def get_max_similarity(similarities):
            max_similarity = -1 * sys.maxsize
            for i in similarities:
                for j in similarities[i]:
                    if similarities[i][j] > max_similarity:
                        max_similarity = similarities[i][j]
            return max_similarity

        def get_cost_matrix(similarities, mappings):
            def conditional_transpose(cost_matrix):
                m = {}
                rm = {}
                row_index = 0
                col_index = 0
                is_transposed = False
                for row in cost_matrix:
                    row_index = 0
                    for value in row:
                        if row_index not in m:
                            m[row_index] = {}
                        m[row_index][col_index] = value
                        row_index += 1
                    col_index += 1
                if col_index >= row_index:
                    return is_transposed, cost_matrix
                else:
                    is_transposed = True
                    transposed_matrix = []
                    for row_index in sorted(m):
                        transposed_matrix_row = []
                        for col_index in sorted(m[row_index]):
                            transposed_matrix_row += [m[row_index][col_index]]
                        transposed_matrix += [transposed_matrix_row]
                    return is_transposed, transposed_matrix
            max_similarity = get_max_similarity(similarities)
            cost_matrix = []
            for gold_index in sorted(mappings['gold']['index_to_id']):
                cost_row = []
                gold_id = mappings['gold']['index_to_id'][gold_index]
                for system_index in sorted(mappings['system']['index_to_id']):
                    system_id = mappings['system']['index_to_id'][system_index]
                    similarity = 0
                    if gold_id in similarities and system_id in similarities[gold_id]:
                        similarity = similarities[gold_id][system_id]
                    cost_row += [max_similarity - similarity]
                cost_matrix += [cost_row]
            return conditional_transpose(cost_matrix)

        def get_precision_recall_and_f1(relevant, retrieved):
            precision = len(relevant & retrieved) / len(retrieved) if len(retrieved) else 0
            recall = len(relevant & retrieved) / len(relevant)
            f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
            return precision, recall, f1

        def get_type_scores(logger, document_id, gold_entity_id, gold_entries, system_entity_id, system_entries):
            types = {'gold': set(), 'system': set()}
            entries = {'gold': gold_entries, 'system': system_entries}
            entity_ids = {'gold': gold_entity_id, 'system': system_entity_id}
            for gold_or_system in types:
                entity_types = set()
                for entry in entries[gold_or_system]:
                    for entity_type in entry.get('entity_types').split(';'):
                        entity_types.add(entity_type)
                    for expanded_entity_type in expanded_types(list(entry.get('entity_types').split(';'))):
                        types[gold_or_system].add(expanded_entity_type)
                logger.record_event('ENTITY_TYPES_INFO',
                                    self.__class__.__name__,
                                    gold_or_system.upper(),
                                    document_id,
                                    entity_ids[gold_or_system],
                                    ';'.join(entity_types),
                                    ';'.join(types[gold_or_system])
                                    )
            return get_precision_recall_and_f1(types['gold'], types['system'])

        data = {
                'gold': self.get('parsed_entries', self.get('gold').get('entries')).get(document_id),
                'system': self.get('parsed_entries', self.get('system').get('entries')).get(document_id, [])
                }
        scores = {}
        for gold_entity_id in data['gold']:
            system_entity_id = 'None'
            similarity = 'None'
            if gold_entity_id in document_alignment.get('gold_to_system'):
                system_entity_id = document_alignment.get('gold_to_system').get(gold_entity_id).get('aligned_to')
                similarity = document_alignment.get('gold_to_system').get(gold_entity_id).get('aligned_similarity')
            precision, recall, f1 = 0,0,0
            self.record_event('ALIGNMENT_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, similarity)
            if system_entity_id != 'None':
                precision, recall, f1 = get_type_scores(self.get('logger'),
                                                        document_id,
                                                        gold_entity_id,
                                                        data['gold'][gold_entity_id],
                                                        system_entity_id,
                                                        data['system'][system_entity_id])
            score = {
                'precision': precision,
                'recall'   : recall,
                'f1'       : f1
                }
            scores['{}::[SEP]::{}'.format(gold_entity_id, system_entity_id)] = score
        for system_entity_id in data['system']:
            gold_entity_id = 'None'
            if system_entity_id not in document_alignment.get('system_to_gold'):
                precision, recall, f1 = 0,0,0
                score = {
                    'precision': precision,
                    'recall'   : recall,
                    'f1'       : f1
                    }
                scores['{}::[SEP]::{}'.format(gold_entity_id, system_entity_id)] = score
                self.record_event('ALIGNMENT_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, similarity)
        return scores

    def get_parsed_entries(self, entries):
        return(parse_entries(entries, self.get('cluster_by_columnname')))

    def score_responses(self):
        annotations = self.get('parsed_entries', self.get('gold').get('entries'))
        responses = self.get('parsed_entries', self.get('system').get('entries'))
        scores = []
        mean_f1 = 0
        count = 0
        for document_id in annotations:
            document_annotations = annotations.get(document_id)
            document_responses = responses.get(document_id, [])
            document_alignment = self.get('alignment').get('document_alignment').get(document_id)
            document_scores = self.get('document_scores', document_id, document_annotations, document_responses, document_alignment)
            for gold_entity_id_and_system_entity_id in document_scores:
                gold_entity_id, system_entity_id = gold_entity_id_and_system_entity_id.split('::[SEP]::')
                precision = document_scores[gold_entity_id_and_system_entity_id]['precision']
                recall = document_scores[gold_entity_id_and_system_entity_id]['recall']
                f1 = document_scores[gold_entity_id_and_system_entity_id]['f1']
                mean_f1 += f1
                count += 1
                score = TypeMetricScoreV1(self.logger,
                                        self.get('run_id'),
                                        document_id,
                                        gold_entity_id,
                                        system_entity_id,
                                        precision,
                                        recall,
                                        f1)
                scores.append(score)

        scores_printer = ScorePrinter(self.logger, self.printing_specs, self.separator)
        for score in multisort(scores, (('document_id', False),
                                        ('gold_entity_id', False),
                                        ('system_entity_id', False))):
            scores_printer.add(score)
        mean_f1 = mean_f1 / count if count else 0
        mean_score = TypeMetricScoreV1(self.logger,
                                   self.get('run_id'),
                                   'Summary',
                                   '',
                                   '',
                                   '',
                                   '',
                                   mean_f1,
                                   summary = True)
        scores_printer.add(mean_score)
        self.scores = scores_printer

class TypeMetricScoreV2(Score):
    """
    AIDA class for type metric score corresponding to the TypeMetricScorerV2.
    """
    def __init__(self, logger, run_id, document_id, gold_entity_id, system_entity_id, average_precision, summary=False):
        super().__init__(logger)
        self.run_id = run_id
        self.document_id = document_id
        self.gold_entity_id = gold_entity_id if gold_entity_id is not None else 'None'
        self.system_entity_id = system_entity_id if system_entity_id is not None else 'None'
        self.average_precision = average_precision
        self.summary = summary

class TypeMetricScorerV2A(Scorer):
    """
    Class for variant # 2A of the type metric scores.

    This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
        * ranking is induced using weights on types, and
        * the weights on a type is the number of mentions asserting that type.

    Clustering is based on entity_id.
    """

    printing_specs = [{'name': 'document_id',      'header': 'DocID',           'format': 's',    'justify': 'L'},
                      {'name': 'run_id',           'header': 'RunID',           'format': 's',    'justify': 'L'},
                      {'name': 'gold_entity_id',   'header': 'GoldEntityID',    'format': 's',    'justify': 'L'},
                      {'name': 'system_entity_id', 'header': 'SystemEntityID',  'format': 's',    'justify': 'L'},
                      {'name': 'average_precision','header': 'AveragePrecision','format': '6.4f', 'justify': 'R', 'mean_format': '6.4f'}]

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def order(self, k):
        return k

    def get_alignment(self):
        return self.get('cluster_alignment')

    def get_cluster_by_columnname(self):
        return 'entity_id'

    def get_parsed_entries(self, entries):
        return(parse_entries(entries, self.get('cluster_by_columnname')))

    def get_document_type_scores(self, document_id, gold_entity_id, gold_entries, system_entity_id, system_entries):
        average_precision = 0.0
        entity_types = {'gold': {}, 'system': {}}
        entries = {'gold': gold_entries, 'system': system_entries}
        for gold_or_system in entity_types:
            for entry in entries.get(gold_or_system):
                for expanded_entity_type in expanded_types(list(entry.get('entity_types').split(';'))):
                    if expanded_entity_type not in entity_types.get(gold_or_system):
                        entity_types.get(gold_or_system)[expanded_entity_type] = list()
                    entity_types.get(gold_or_system).get(expanded_entity_type).append(entry)

        type_weights = list()
        for expanded_entity_type in entity_types.get(gold_or_system):
            type_weight = {
                'type': expanded_entity_type,
                'weight': len(entity_types.get(gold_or_system).get(expanded_entity_type))
                }
            type_weights.append(type_weight)

        rank = 0
        num_correct = 0
        sum_precision = 0.0
        for type_weight in multisort(type_weights, (('weight', True),
                                                    ('type', False))):
            rank += 1
            label = 'WRONG'
            if type_weight.get('type') in entity_types.get('gold'):
                label = 'RIGHT'
                num_correct += 1
                sum_precision += (num_correct/rank)
            self.record_event('AP_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, rank, type_weight.get('type'), label, type_weight.get('weight'), num_correct, sum_precision)

        average_precision = sum_precision/len(entity_types.get('gold'))
        return average_precision

    def get_document_scores(self, document_id, document_annotations, document_responses, document_alignment):
        data = {
                'gold': self.get('parsed_entries', self.get('gold').get('entries')).get(document_id),
                'system': self.get('parsed_entries', self.get('system').get('entries')).get(document_id, [])
                }
        scores = {}
        for gold_entity_id in data['gold']:
            system_entity_id = 'None'
            similarity = 'None'
            if gold_entity_id in document_alignment.get('gold_to_system'):
                system_entity_id = document_alignment.get('gold_to_system').get(gold_entity_id).get('aligned_to')
                similarity = document_alignment.get('gold_to_system').get(gold_entity_id).get('aligned_similarity')
            average_precision = 0
            self.record_event('ALIGNMENT_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, similarity)
            if system_entity_id != 'None':
                average_precision = self.get('document_type_scores', document_id, gold_entity_id, data['gold'][gold_entity_id], system_entity_id, data['system'][system_entity_id])
            score = {
                'average_precision': average_precision,
                }
            scores['{}::[SEP]::{}'.format(gold_entity_id, system_entity_id)] = score
        for system_entity_id in data['system']:
            gold_entity_id = 'None'
            if system_entity_id not in document_alignment.get('system_to_gold'):
                average_precision = 0
                score = {
                    'average_precision': average_precision,
                    }
                scores['{}::[SEP]::{}'.format(gold_entity_id, system_entity_id)] = score
                self.record_event('ALIGNMENT_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, similarity)
        return scores

    def score_responses(self):
        annotations = self.get('parsed_entries', self.get('gold').get('entries'))
        responses = self.get('parsed_entries', self.get('system').get('entries'))
        scores = []
        mean_average_precision = 0
        count = 0
        for document_id in annotations:
            document_annotations = annotations.get(document_id)
            document_responses = responses.get(document_id, [])
            document_alignment = self.get('alignment').get('document_alignment').get(document_id)
            document_scores = self.get('document_scores', document_id, document_annotations, document_responses, document_alignment)
            for gold_entity_id_and_system_entity_id in document_scores:
                gold_entity_id, system_entity_id = gold_entity_id_and_system_entity_id.split('::[SEP]::')
                average_precision = document_scores[gold_entity_id_and_system_entity_id]['average_precision']
                mean_average_precision += average_precision
                count += 1
                score = TypeMetricScoreV2(self.logger,
                                        self.get('run_id'),
                                        document_id,
                                        gold_entity_id,
                                        system_entity_id,
                                        average_precision)
                scores.append(score)

        scores_printer = ScorePrinter(self.logger, self.printing_specs, self.separator)
        for score in multisort(scores, (('document_id', False),
                                        ('gold_entity_id', False),
                                        ('system_entity_id', False))):
            scores_printer.add(score)
        mean_average_precision = mean_average_precision / count if count else 0
        mean_score = TypeMetricScoreV2(self.logger,
                                   self.get('run_id'),
                                   'Summary',
                                   '',
                                   '',
                                   mean_average_precision,
                                   summary = True)
        scores_printer.add(mean_score)
        self.scores = scores_printer

class TypeMetricScorerV3A(TypeMetricScorerV2A):
    """
    Class for variant # 3A of the type metric scores.

    This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
        * ranking is induced using weights on types, and
        * the weight on a type is computed as the sum of confidences on mentions asserting that type.

    Clustering is based on entity_id.
    """

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def get_document_type_scores(self, document_id, gold_entity_id, gold_entries, system_entity_id, system_entries):
        average_precision = 0.0
        entity_types = {'gold': {}, 'system': {}}
        entries = {'gold': gold_entries, 'system': system_entries}
        for gold_or_system in entity_types:
            for entry in entries.get(gold_or_system):
                for expanded_entity_type in expanded_types(list(entry.get('entity_types').split(';'))):
                    if expanded_entity_type not in entity_types.get(gold_or_system):
                        entity_types.get(gold_or_system)[expanded_entity_type] = 0
                    entity_types.get(gold_or_system)[expanded_entity_type] += float(entry.get('confidence'))

        type_weights = list()
        for expanded_entity_type in entity_types.get(gold_or_system):
            type_weight = {
                'type': expanded_entity_type,
                'weight': entity_types.get(gold_or_system).get(expanded_entity_type)
                }
            type_weights.append(type_weight)

        rank = 0
        num_correct = 0
        sum_precision = 0.0
        for type_weight in multisort(type_weights, (('weight', True),
                                                    ('type', False))):
            rank += 1
            label = 'WRONG'
            if type_weight.get('type') in entity_types.get('gold'):
                label = 'RIGHT'
                num_correct += 1
                sum_precision += (num_correct/rank)
            self.record_event('AP_INFO', self.__class__.__name__, document_id, gold_entity_id, system_entity_id, rank, type_weight.get('type'), label, type_weight.get('weight'), num_correct, sum_precision)

        average_precision = sum_precision/len(entity_types.get('gold'))
        return average_precision

class TypeMetricScorerV1B(TypeMetricScorerV1A):
    """
    Class for variant # 1B of the type metric scores.

    This variant of the scorer considers all types asserted on the cluster as a set, and uses this set to compute
    precision, recall and F1.
    
    Clustering is based on mention_span.
    """

    printing_specs = [{'name': 'document_id',      'header': 'DocID',           'format': 's',    'justify': 'L'},
                      {'name': 'run_id',           'header': 'RunID',           'format': 's',    'justify': 'L'},
                      {'name': 'gold_entity_id',   'header': 'GoldMentionID',   'format': 's',    'justify': 'L'},
                      {'name': 'system_entity_id', 'header': 'SystemMentionID', 'format': 's',    'justify': 'L'},
                      {'name': 'precision',        'header': 'Prec',            'format': '6.4f', 'justify': 'R', 'mean_format': 's'},
                      {'name': 'recall',           'header': 'Recall',          'format': '6.4f', 'justify': 'R', 'mean_format': 's'},
                      {'name': 'f1',               'header': 'F1',              'format': '6.4f', 'justify': 'R', 'mean_format': '6.4f'}]

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def get_alignment(self):
        return self.get('mention_alignment')

    def get_cluster_by_columnname(self):
        return 'mention_span'

class TypeMetricScorerV2B(TypeMetricScorerV2A):
    """
    Class for variant # 2B of the type metric scores.

    This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
        * ranking is induced using weights on types, and
        * the weights on a type is the number of mentions asserting that type.

    Clustering is based on mention_span.
    """

    printing_specs = [{'name': 'document_id',      'header': 'DocID',           'format': 's',    'justify': 'L'},
                      {'name': 'run_id',           'header': 'RunID',           'format': 's',    'justify': 'L'},
                      {'name': 'gold_entity_id',   'header': 'GoldMentionID',   'format': 's',    'justify': 'L'},
                      {'name': 'system_entity_id', 'header': 'SystemMentionID', 'format': 's',    'justify': 'L'},
                      {'name': 'average_precision','header': 'AveragePrecision','format': '6.4f', 'justify': 'R', 'mean_format': '6.4f'}]

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def get_alignment(self):
        return self.get('mention_alignment')

    def get_cluster_by_columnname(self):
        return 'mention_span'

class TypeMetricScorerV3B(TypeMetricScorerV3A):
    """
    Class for variant # 3B of the type metric scores.

    This variant of the scorer ranks the types asserted on the cluster, and computes AP where:
        * ranking is induced using weights on types, and
        * the weight on a type is computed as the sum of confidences on mentions asserting that type.

    Clustering is based on mention_span.
    """

    def __init__(self, logger, separator=None, **kwargs):
        super().__init__(logger, separator=separator, **kwargs)

    def get_alignment(self):
        return self.get('mention_alignment')

    def get_cluster_by_columnname(self):
        return 'mention_span'

class ScoresManager(Object):
    """
    The class for managing scores.
    """

    def __init__(self, logger, arguments, separator=None):
        super().__init__(logger)
        for key in arguments:
            self.set(key, arguments[key])
        self.metrics = {
            'TypeMetricV1A': TypeMetricScorerV1A,
            'TypeMetricV2A': TypeMetricScorerV2A,
            'TypeMetricV3A': TypeMetricScorerV3A,
            'TypeMetricV1B': TypeMetricScorerV1B,
            'TypeMetricV2B': TypeMetricScorerV2B,
            'TypeMetricV3B': TypeMetricScorerV3B,
            }
        self.separator = separator
        self.scores = Container(logger)
        self.score_responses()

    def score_responses(self):
        for metric in self.get('metrics'):
            scorer = self.get('metrics')[metric](logger=self.get('logger'),
                                                 run_id=self.get('run_id'),
                                                 gold=self.get('gold'),
                                                 system=self.get('system'),
                                                 cluster_alignment=self.get('cluster_alignment'),
                                                 mention_alignment=self.get('mention_alignment'),
                                                 separator=self.get('separator'))
            self.get('scores').add(key=metric, value=scorer)

    def print_scores(self, output_directory):
        os.mkdir(output_directory)
        for metric in self.get('scores'):
            scores = self.get('scores').get(metric)
            output_file = '{}/{}-scores.txt'.format(output_directory, metric)
            scores.print_scores(output_file)

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

def main(args):
    check_for_paths_existance([
                 args.log_specifications,
                 args.gold,
                 args.system])
    check_for_paths_non_existance([args.scores])
    logger = Logger(args.log, args.log_specifications, sys.argv)
    header = ['run_id', 'mention_id', 'mention_string', 'mention_span', 'entity_id', 'entity_types', 'mention_type', 'confidence']
    gold = FileHandler(logger, args.gold, header=FileHeader(logger, '\t'.join(header)), encoding='utf-8')
    system = FileHandler(logger, args.system, header=FileHeader(logger, '\t'.join(header)), encoding='utf-8')
    cluster_alignment = Alignment(logger, gold, system, 'entity_id')
    mention_alignment = Alignment(logger, gold, system, 'mention_span')
    arguments = {
        'run_id': args.run,
        'cluster_alignment': cluster_alignment,
        'mention_alignment': mention_alignment,
        'gold': gold,
        'system': system
        }
    scores = ScoresManager(logger, arguments, args.separator)
    scores.print_scores(args.scores)

    exit(ALLOK_EXIT_CODE)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Score RUFES output")
    parser.add_argument('-l', '--log', default='log.txt', help='Specify a file to which log output should be redirected (default: %(default)s)')
    parser.add_argument('-r', '--run', default='runID', help='Specify the run ID (default: %(default)s)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, help='Print version number and exit')
    parser.add_argument('-S', '--separator', default='pretty', choices=['pretty', 'tab', 'space'], help='Column separator for scorer output? (default: %(default)s)')
    parser.add_argument('log_specifications', type=str, help='File containing error specifications')
    parser.add_argument('gold', type=str, help='Input gold annotations file')
    parser.add_argument('system', type=str, help='Input system response file')
    parser.add_argument('scores', type=str, help='Output scores directory (note that this directory should not exist)')
    args = parser.parse_args()
    main(args)
