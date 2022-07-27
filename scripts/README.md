# RUFESUILS

(created: 7/27/2022, last revised: 7/27/2022)

## NAME
    rufesutils - the RUFES utilities

## RUFESUILS COMMANDS
    We divide RUFESUILS into the following commands:

### 1. rufesutils-validate-responses
    Validate a response (or gold annotations) file

#### Prerequisites

    - Python (version 3.9 or later) with the following packages:
        tqdm

#### How to validate a response (or gold annotations) file
    In order to validate a response (or gold annotations) file, you need to run the command of the form:

~~~
    python rufesutils validate-responses [-h] [-l LOGFILE] [-v] logspecs segment_boundaries ontology_types input output
~~~

    The usage is given below:

~~~
    python rufesutils.py validate-responses -h

    usage: rufesutils validate-responses [-h] [-l LOGFILE] [-v] logspecs segment_boundaries ontology_types input output
    
    Validating responses (or gold annotations) file.
    
    positional arguments:
      logspecs              File containing error specifications
      segment_boundaries    File containing segment boundaries information.
      ontology_types        File containing list of valid ontology types.
      input                 File to be validated.
      output                Specify the file to which the validated output should be written
    
    optional arguments:
      -h, --help            show this help message and exit
      -l LOGFILE, --logfile LOGFILE
                            Specify a file to which log output should be redirected (default: log.txt)
      -v, --version         Print version number and exit
~~~

    The code comes with an example input file, auxiliary data and output file. In order to validate the example input file, run the following command:
    
~~~
    python3.9 rufesutils.py validate-responses \
      -l example/validate-responses/validate-responses.log \
      ../input/log_specifications.txt \
      example/validate-responses/example_segment_boundaries.tab \
      ../input/AUX-data/TAC_KBP_RUFES2020/TAC_KBP_RUFES2020_Ontology_Types.txt \
      example/validate-responses/system_output_dev.tab \
      example/validate-responses/system_output_dev_valid.tab
~~~
    
# Revision History

## 7/27/2022
- Initial version
