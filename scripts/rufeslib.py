"""
The object class to serve as the base class
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "0.0.0.1"
__date__    = "20 July 2022"

import logging
import os
import re
import sys
import traceback

from inspect import currentframe, getouterframes
from tqdm import tqdm

class Object(object):
    """
    This class represents an object which is envisioned to be the parent of most of the related classes.
    
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
        self.get('logger').record_event(event_code, *args, classname=self.__class__.__name__)

    def set(self, key, value):
        """
        Sets the value of an attribute, of the current, whose name matches the value stored in key.
        """
        setattr(self, key, value)

class Container(Object):
    """
    The AIDA container class.

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

class DocumentBoundaries(Container):
    """
    This class serves as the base class for:
        TextDocumentBoundaries
        ImageBoundaries
        KeyFrameBoundaries
    
    It provides implementation of method(s) common to these derived classes.

    NOTE: The derived classes will need to provide the implementation of
    corresponding load() method.
    """

    def __init__(self, logger, filename):
        """
        Initializes this instance, and sets the logger and filename for newly created instance.
        """
        super().__init__(logger)
        self.filename = filename
        # the implementation of load needs to come from the derived classes.
        self.load()

    def get_boundary(self, span_string):
        """
        Given a span_string of the form:
            document_id:(start_x,start_y)-(end_x,end_y)
        Return the document boundary corresponding to the document element whose id is doceid.
        """
        document_boundary = None
        search_obj = re.search( r'^(.*?):\((\d+),(\d+)\)-\((\d+),(\d+)\)$', span_string)
        if search_obj:
            document_id = search_obj.group(1)
            if self.exists(document_id):
                document_boundary = self.get(document_id)
        return document_boundary

class Span(Object):
    """
    Span class to be used for storing a text span, or an image or video bounding box.

    TODO: Update this class for future use of the audio-only bounding box.
    """

    def __init__(self, logger, start_x, start_y, end_x, end_y):
        """
        Initialize the Span object.
        
        Arguments:
            logger (aida.Logger):
                the aida.Logger object
            start_x (string):
                the start character position of a text document, or
                the top-left-x coordinate for an image
            start_y (string):
                zero ('0') for a text document, or
                the top-left-y coordinate for an image
            end_x (string):
                the end character position of a text document, or
                the bottom-right-x coordinate for an image
            end_y (string):
                zero ('0') for a text document, or
                the bottom-right-y coordinate for an image
        """
        super().__init__(logger)
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y

    def __str__(self, *args, **kwargs):
        """
        Return a string containing the bounding box in the form:
            START-END
        where
            START=(start_x,start_y)
            END=(end_x,end_y)
        """
        return "{}-{}".format(self.get('START'), self.get('END'))

    def get_copy(self):
        return type(self)(self.get('logger'), self.get('start_x'), self.get('start_y'), self.get('end_x'), self.get('end_y'))

    def get_START(self):
        """
        Return a string containing the start of the bounding box
        in the form:
            (start_x,start_y)
        """
        return "({},{})".format(self.start_x, self.start_y)

    def get_END(self):
        """
        Return a string containing the end of the bounding box
        in the form:
            (end_x,end_y)
        """
        return "({},{})".format(self.end_x, self.end_y)

class DocumentBoundary(Span):
    """
    AIDA DocumentBoundary class to be used for storing
    text document boundary, or image or video bounding box
    information.
    
    The DocumentBoundary inherits from the Span class, and
    adds a method called 'validate' for validating if a span
    passed as argument is inside the object boundary
    """

    def __init__(self, logger, start_x, start_y, end_x, end_y):
        """
        Initialize the DocumentBoundary object.
        """
        super().__init__(logger, start_x, start_y, end_x, end_y)

    def get_corrected_span(self, span):
        min_x, min_y, max_x, max_y = map(lambda arg:float(self.get(arg)),
                             ['start_x', 'start_y', 'end_x', 'end_y'])
        sx, sy, ex, ey = map(lambda arg:float(span.get(arg)),
                             ['start_x', 'start_y', 'end_x', 'end_y'])
        # if the span is (0,0)-(0,0) return document boundary
        if sx+sy+ex+ey == 0:
            return self.get('span')
        if sx > max_x or sy > max_y or ex < min_x or ey < min_y:
            # can't correct, return None
            return
        sx = self.get('start_x') if sx < min_x else span.get('start_x')
        sy = self.get('start_y') if sy < min_y else span.get('start_y')
        ex = self.get('end_x') if ex > max_x else span.get('end_x')
        ey = self.get('end_y') if ey > max_y else span.get('end_y')
        return Span(self.get('logger'), sx, sy, ex, ey)

    def get_span(self):
        sx, sy, ex, ey = [self.get(arg) for arg in ['start_x', 'start_y', 'end_x', 'end_y']]
        return Span(self.get('logger'), sx, sy, ex, ey)

    def validate(self, span):
        """
        Validate if the span is inside the document boundary
        
        Arguments:
            span:
                span could be an aida.Span object, or a string of the
                form:
                    (start_x,start_y)-(end_x,end_y)

        Returns True if the span is inside the document, False otherwise.
        
        This method throws exception if span is not as mentioned above.
        """
        if isinstance(span, str):
            search_obj = re.search( r'^\((\d+),(\d+)\)-\((\d+),(\d+)\)$', span)
            if search_obj:
                start_x = search_obj.group(1)
                start_y = search_obj.group(2)
                end_x = search_obj.group(3)
                end_y = search_obj.group(4)
                span = Span(self.logger, start_x, start_y, end_x, end_y)
            else:
                raise Exception('{} is not of a form (start_x,start_y)-(end_x,end_y)'.format(span))

        if isinstance(span, Span):
            min_x, min_y, max_x, max_y = map(lambda arg:float(self.get(arg)),
                                 ['start_x', 'start_y', 'end_x', 'end_y'])
            sx, sy, ex, ey = map(lambda arg:float(span.get(arg)),
                                 ['start_x', 'start_y', 'end_x', 'end_y'])
            is_valid = False
            if min_x <= sx <= max_x and min_x <= ex <= max_x and min_y <= sy <= max_y and min_y <= ey <= max_y:
                is_valid = True
            return is_valid
        else:
            raise TypeError('{} called with argument of unexpected type'.format(isinstance.__name__))

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
            self.set(keys[i].strip(), values[i].strip())

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
        return '{}\n'.format('\t'.join([self.get(column) for column in self.get('header').get('columns')]))

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
        self.entries = []
        self.load_file()

    def load_file(self):
        """
        Load the file.
        """
        filename = self.get('filename')
        with open(filename, encoding=self.get('encoding')) as file:
            for lineno, line in enumerate(tqdm(file, desc='loading {}'.format(filename)), start=1):
                if self.get('header') is None:
                    self.header = FileHeader(self.get('logger'), line.rstrip())
                else:
                    where = {'filename': filename, 'lineno': lineno}
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

class RUFESObject(Object):
    """
    Class that serves as Object for RUFES library.
    """
    def __init__(self, **kwargs):
        for k,v in kwargs.items():
            self.set(k, v)
        self.logger = Logger(self.get('logfile'), self.get('logspecs'), sys.argv)

class TextBoundaries(DocumentBoundaries):
    """
    This class provides easy access to text document boundaries, and is inherited
    from the DocumentBoundaries class which is a container customized for storing
    document boundaries, and providing methods to provide access to these document
    boundaries.
    """

    def __init__(self, logger, filename):
        """
        Initialize TextDocumentBoundaries.

        Arguments:
            logger (aida.Logger):
                the aida.Logger object
            filename (str):
                the file containing information about boundaries of text documents.
        """
        super().__init__(logger, filename)

    def load(self):
        """
        Read the segment boundary file to load document boundary
        information.
        """
        for entry in tqdm(FileHandler(self.logger, self.filename), desc='processing segment boundaries'):
            doceid, start_char, end_char = map(
                    lambda arg: entry.get(arg),
                    'document_id,start_char,end_char'.split(','))
            document_boundary = self.get(doceid,
                                         default=DocumentBoundary(self.logger,
                                                                  start_char, 0, end_char, 0))
            tb_start_char = document_boundary.get('start_x')
            tb_end_char = document_boundary.get('end_x')
            if int(start_char) < int(tb_start_char):
                document_boundary.set('start_x', start_char)
            if int(end_char) > int(tb_end_char):
                document_boundary.set('end_x', end_char)

"""
The logger class.
"""

class Logger:
    """
    The logger for RUFES related scripts.
    
    This module is a wrapper around the Python 'logging' module which is internally used to
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
        self.recorded = {}
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

    def record_event(self, event_code, *args, classname=None):
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
            classname = 'NO_CLASS_NAME' if classname is None else classname
            event_message = '{classname} - {code} - {message}'.format(classname=classname, code=event_code, message=event_message)
            if event_message in self.recorded:
                return
            self.recorded[event_message] = 1
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
        arguments = self.arguments.split()
        if '--aws_access_key_id' in arguments and '--aws_secret_access_key' in arguments:
            arguments[arguments.index('--aws_access_key_id')+1] = '__XXXXXXXXX__'
            arguments[arguments.index('--aws_secret_access_key')+1] = '__XXXXXXXXX__'
        debug_message = "Execution begins {current_dir:" + self.path_name + ", script_name:" + self.file_name + ", arguments:" + ' '.join(arguments) +"}"
        self.logger_object.info(debug_message)

class Normalizer(Object):
    """
    Normalizer for values in AIDA response.
    """

    def __init__(self, logger):
        super().__init__(logger)

    def normalize(self, caller, method_name, entry, attribute, undo=False):
        method = self.get_method(method_name)
        method(caller, entry, attribute, undo)

    def normalize_mention_span(self, caller, entry, attribute, undo):
        if undo:
            attribute_name = attribute.get('name')
            value = entry.get(attribute_name)
            search_obj = re.search('^(.*?):\((\S+),(\S+)\)-\((\S+),(\S+)\)$', value)
            if search_obj:
                document_id = search_obj.group(1)
                start_x = search_obj.group(2)
                end_x = search_obj.group(4)
                unnormalized_value = '{}:{}-{}'.format(document_id, start_x, end_x)
                entry.set(attribute_name, unnormalized_value)
        else:
            attribute_name = attribute.get('name')
            value = entry.get(attribute_name)
            search_obj = re.search(r'^(.*?):(-?[0-9]+)-(-?[0-9]+)$', value)
            if search_obj:
                document_id = search_obj.group(1)
                start_x = search_obj.group(2)
                end_x = search_obj.group(3)
                normalized_value = '{}:({},0)-({},0)'.format(document_id, start_x, end_x)
                entry.set(attribute_name, normalized_value)

class Validator(Object):
    """
    This class is used for validating the following type of files:
    
    (1) Gold annotations,
    (2) System responses
    """

    def __init__(self, logger):
        super().__init__(logger)

    def parse_provenance(self, provenance):
        # parse a string of the form "document_id:(start_x,start_y)-(end_x,end_y)" and
        # return a dictionary object containing parsed fields.
        search_obj = re.search('^(.*?):\((\S+),(\S+)\)-\((\S+),(\S+)\)$', provenance)
        if not search_obj: return
        document_id = search_obj.group(1)
        start_x, start_y, end_x, end_y = map(lambda ID: int(search_obj.group(ID)), [2, 3, 4, 5])
        return {
            'document_id': document_id,
            'start_x':start_x,
            'start_y':start_y,
            'end_x':end_x,
            'end_y':end_y}

    def validate(self, caller, method_name, schema, entry, attribute, data):
        # this is the main method called by the validator script
        method = self.get_method(method_name)
        if method is None:
            self.record_event('UNDEFINED_METHOD', method_name)
        return method(caller, schema, entry, attribute, data)

    def validate_confidence(self, caller, schema, entry, attribute, data):
        # validate if the confidence is 0 (noninclusive) and 1 (inclusive)
        confidence = entry.get(attribute.get('name'))
        try:
            if not 0 < float(confidence) <= 1.0:
                self.record_event('INVALID_CONFIDENCE', confidence, entry.get('where'))
                entry.set(attribute.get('name'), '1.0')
        except ValueError:
            self.record_event('INVALID_CONFIDENCE_ERROR', confidence, entry.get('where'))
            return False
        return True

    def validate_entity_types(self, caller, schema, entry, attribute, data):
        # validate if the entity types are one of the allowed types
        allowed_values = data['allowed_entity_types']
        provided_values = ','.join(entry.get(attribute.get('name')).split(';'))
        return self.validate_set_membership('entity_type', allowed_values, provided_values, entry.get('where'))

    def validate_mention_span(self, caller, schema, entry, attribute, data):
        # validate that mention span:
        # - contains a valid document ID,
        # - has offsets mentioned in proper order,
        # - has positive offsets,
        # - falls within document bounds
        def parse(span):
            return span.split(':')
        mention_span = entry.get(attribute.get('name'))
        text_boundary = data.get('text_boundaries').get('boundary', mention_span)
        parsed_provenance = self.parse_provenance(mention_span)
        if not data.get('text_boundaries').exists(parsed_provenance.get('document_id')):
            self.record_event('UNKNOWN_DOCUMENT', mention_span, parsed_provenance.get('document_id'), entry.get('where'))
            return False
        if parsed_provenance.get('start_x') > parsed_provenance.get('end_x'):
            self.record_event('IMPROPER_OFFSET_ORDER', mention_span, entry.get('where'))
            return False
        for start_or_end_x in ['start_x', 'end_x']:
            if parsed_provenance.get(start_or_end_x) < 0:
                self.record_event('NEGATIVE_OFFSET', start_or_end_x, mention_span, entry.get('where'))
                return False
        if not text_boundary.validate(mention_span.split(':')[1]):
            self.record_event('SPAN_OFF_BOUNDARY', mention_span, text_boundary, entry.get('where'))
            return False
        return True

    def validate_mention_type(self, caller, schema, entry, attribute, data):
        # validate if mention type is one of the allowed type
        allowed_values = data['allowed_mention_types']
        return self.validate_set_membership('mention_type', allowed_values, entry.get(attribute.get('name')), entry.get('where'))

    def validate_run_id(self, caller, schema, entry, attribute, data):
        # all run IDs are valid
        return True

    def validate_set_membership(self, name, allowed_values, values, where):
        # this method is used by other methods to check if all values are in allowed values
        for value in sorted(values.split(',')):
            if value not in allowed_values:
                self.record_event('UNKNOWN_VALUE', name, value, ', '.join(sorted(allowed_values)), where)
                return False
        return True