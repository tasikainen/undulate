import base64
import random
import mimetypes
import json
from datetime import datetime
from io import StringIO
import logging
import os
import re
import selectors
import subprocess
import argparse
from timeit import default_timer as timer

import requests

class Shellog:
    """  The shellog object processes and sends logs
    :param urls: The arg is a dictionary which contains the endpoints to the
     backend of the logger.
    :type urls: dict
    """

    def __init__(self, urls):
        self.save_output_streams_url = urls['save_output_streams_url']
        self.save_file_output_url = urls['save_file_output_url']
        self.save_processed_output_url = urls['save_processed_output_url']
        self.save_binary_file_url = urls['save_binary_file_url']
        self.check_line_count_from_db_url = urls['check_line_count_from_db_url']

        # Create a buffer for the logger
        self.log_stream = StringIO(newline=None)

        # Create logger for the process stdout and stderr
        self.log = logging.getLogger("Subprocess logger")
        self.log.setLevel(logging.DEBUG)

        # Make sure that the logger is empty
        for handler in self.log.handlers:
            self.log.removeHandler(handler)

        # Initialize the logger to write to the buffer and set other logging parameters
        handler_for_streaming = logging.StreamHandler(self.log_stream)
        handler_for_streaming.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s message_start%(message)s message_end'))
        handler_for_streaming.setLevel(logging.DEBUG)
        handler_for_streaming.terminator = ""
        self.log.addHandler(handler_for_streaming)

        # Create buffers to save outputs for the converting stage
        self.stdout = StringIO()
        self.stderr = StringIO()

    def start_process_and_send_logs(self, cmd, output_files=None, rules=None,
                                    process_time_limit=None,
                                    send_to_db_time_interval=None, run_metadata=None):
        """
        Starts a process and sends the output to the backend

        :param cmd: command to run the program to be logged. A list of
         strings
        :param output_files: output files which are to be logged. A list
         of strings
        :param rules: rules to generate processed output. A list of
         dictionaries
        :param process_time_limit: amount of time the called program can
        run before being terminated. Shellog sends an sigterm signal to the
        subprocess after the time has hit the limit if this parameter is
        initialized.
        :param send_to_db_time_interval: shellog dumps the buffer
        periodically to the backend if this parameter is initialized.
        the minimum interval is 5 second"""
        total_lines_send = 0
        # Get the working directory
        output_of_pwd = subprocess.run(['pwd'], text=True, capture_output=True)
        working_directory = output_of_pwd.stdout.strip()

        # Call the process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=working_directory)

        # Set the task column
        # task = random.randint(0, 10000000)

        # Stream the output to db
        total_lines_send += self.send_log_streams(process, run_metadata, cmd, send_to_db_time_interval, process_time_limit)
        # Read output from a file and send to db
        if output_files is not None:
            total_lines_send += self.send_output_files(run_metadata, output_files)
        # Convert the output and send to db
        if rules is not None:
            total_lines_send += self.convert_and_send_output(run_metadata, rules)
        # Validate the send
        self.check_if_lines_are_send_to_db(run_metadata, total_lines_send)
        # Rewind all the buffers
        self.stdout.seek(0)
        self.stdout.truncate(0)
        self.stderr.seek(0)
        self.stderr.truncate(0)
        self.log_stream.seek(0)
        self.log_stream.truncate(0)
        return total_lines_send

    def send_log_streams(self, process, run_metadata, cmd, send_to_db_time_interval, process_time_limit):
        """
        Stream the output to db

        :param process: process that is being run
        :param cmd: command that the process was started with
        :param send_to_db_time_interval: how often the data will be send to
        backend and a new buffer initialized. The minimum interval is 5 second
        :param process_time_limit: how long the process can run before it is
        terminated
        """
        lines_send = 0
        # Set send interval and set minimum
        if send_to_db_time_interval:
            start_of_send_interval = timer()
            if send_to_db_time_interval < 5:
                send_to_db_time_interval = 5
        else:
            start_of_send_interval = 0
        # Set process time limit
        if process_time_limit:
            start_of_process_timeout = timer()
        else:
            start_of_process_timeout = 0

        # Log the starting command as the first log line
        self.log.info('Subprocess command: ' + ' '.join(cmd) + " \n")

        # A loop to read the output and log them to buffer
        # Found the solution from here https://stackoverflow.com/questions/31833897/python-read-from-subprocess-stdout-and-stderr-separately-while-preserving-order
        sel = selectors.DefaultSelector()
        sel.register(process.stdout, selectors.EVENT_READ)
        sel.register(process.stderr, selectors.EVENT_READ)
        more_data = True
        stdout_output_empty = False
        stderr_output_empty = False
        while more_data is True:
            for key, _ in sel.select():
                data = key.fileobj.read1().decode()
                if not data:
                    # Flags for empty output buffers
                    if key.fileobj is process.stdout:
                        stdout_output_empty = True
                    else:
                        stderr_output_empty = True
                if key.fileobj is process.stdout:
                    # Write to log for streaming
                    self.log.info(str(data))
                    # Write to buffer for converting
                    self.stdout.write(str(data))
                else:
                    # Write to log for streaming
                    self.log.error(str(data))
                    # Write to buffer for converting
                    self.stderr.write(str(data))
                if send_to_db_time_interval and (
                        timer() - start_of_send_interval) >= send_to_db_time_interval:
                    # Dump buffer if the interval has passed
                    start_of_send_interval, add_to_lines_send = self.buffer_dump(
                        run_metadata)
                    lines_send += add_to_lines_send
                if process_time_limit and (
                        timer() - start_of_process_timeout) >= process_time_limit:
                    # Kill the process if the time limit has passed
                    process.terminate()
                    self.log.error(
                        "Timeout limit reached --> Process terminated")
                    more_data = False
                    sel.close()
                    break
                if process.poll() is not None and stderr_output_empty and stdout_output_empty:
                    # Break the loop if the process has finished and there is no more output
                    more_data = False
                    sel.close()
                    break
        # Get the exit code and send it as the last log line
        exitcode = process.wait()
        if exitcode == 0:
            self.log.info("Exitcode: " + str(exitcode))
        else:
            self.log.error("Exitcode: " + str(exitcode))
        output = self.log_stream.getvalue()

        # Rewind the buffer
        self.log_stream.seek(0)
        self.log_stream.truncate(0)

        # Send the all remaining output to db
        # output_json = { 'task': str(task), 'output': output }
        output_json = { 'output': output }
        output_json.update(run_metadata)
        requests.post(self.save_output_streams_url, json=output_json)

        # Count send lines
        lines_send += len(output.splitlines())
        return lines_send

    def buffer_dump(self, run_metadata):
        """
        Dump the buffer to the backend

        :param task: process id
        :return: reset timer and the lines send to backend
        """
        # Reset timer
        reset_timer_start_of_send_interval = timer()
        # Read the buffer
        output = self.log_stream.getvalue()
        # Rewind and clear the buffer
        self.log_stream.seek(0)
        self.log_stream.truncate(0)
        # Send data to backend
        # output_json = {'task': str(task), 'output': output}
        output_json = { 'output': output }
        output_json.update(run_metadata)
        requests.post(self.save_output_streams_url, json=output_json)

        # Count send lines and substract extra line(message_end) from line count that does not go to db
        lines_send = len(output.splitlines()) - 1
        return reset_timer_start_of_send_interval, lines_send

    def send_output_files(self, run_metadata, output_files):
        """
        Sends data from a file to the backend
        :param run_metadata: process id
        :param output_files: the paths to the output files
        """
        lines_send = 0
        # Loop through output files and send to db
        for filepath in output_files:
            filehandle = filepath
            with open(filehandle) as file_to_log:
                file_output = file_to_log.read()
            file_output_json = { # 'task': str(task),
                                'filehandle': filehandle,
                                'file_output': file_output,
                                'process_timestamp': datetime.now().isoformat(
                                    sep=' ', timespec='milliseconds')}

            file_output_json.update(run_metadata)
            requests.post(self.save_file_output_url, json=file_output_json)

            # Count lines send
            lines_send += len(file_output.splitlines())
        return lines_send

    def convert_and_send_output(self, run_metadata, rules):
        """
        Converts the data according to the rules and sends to backend

        :param task: process id
        :param rules: the rules applied to convert the data
        """
        lines_send = 0
        # Placeholder for rule_employed
        rule_employed = random.randint(0, 1000)
        # Apply rules to the data and send it to the backend
        for rule_to_apply in rules:
            # Choose the data output to convert
            filehandle = rule_to_apply['filehandle']
            if filehandle == 'stdout':
                data = str(self.stdout.getvalue())
            elif filehandle == 'stderr':
                data = str(self.stderr.getvalue())
            elif filehandle == 'binary':
                file_path = rule_to_apply["path"]
                # Convert binary into a string and send to db
                with open(file_path, "rb") as file_to_convert:
                    data = file_to_convert.read()
                    data = base64.b64encode(data)
                    data_as_a_string = data.decode('utf-8')
                    file_name = file_path.split("/")[-1]
                    processed_output_json = {"filename": file_name,
                                             "path": file_path,
                                             "mime_type": mimetypes.guess_type(file_path)[0],
                                             "os_timestamp": datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                                             "file_data": data_as_a_string,
                                             "size": os.stat(file_path).st_size,
                                             # 'task': str(task),
                                             'filehandle': filehandle,
                                             'rule_employed': rule_employed,
                                             'identifier': rule_to_apply[
                                                 'identifier'],
                                             'result': "binary file"
                                             }

                    process_output_json.update(run_metadata)
                    requests.post(self.save_binary_file_url, json=processed_output_json)

                    # This processing send a line to two tables the data.process_result and nivel.file_value
                    lines_send += 2
                    continue
            else:
                with open(filehandle) as file_to_convert:
                    data = file_to_convert.read()
            if 'record_separator' in rule_to_apply:
                data = data.split(rule_to_apply['record_separator'])
            else:
                data = [data]
            for result in data:
                # Apply conversion
                processed_output = self.apply_patterns(result, rule_to_apply)
                # Send converted data to db
                processed_output_json = { # 'task': str(task),
                                         'filehandle': filehandle,
                                         'rule_employed': rule_employed,
                                         'identifier': rule_to_apply['identifier'],
                                         'result': processed_output,
                                         'process_timestamp': datetime.now().isoformat(sep=' ', timespec='milliseconds')}
                processed_output_json.update(run_metadata)

                requests.post(self.save_processed_output_url, json=processed_output_json)

                # Count lines
                lines_send += 1
        return lines_send

    def apply_patterns(self, result, convert_rule):
        """
        Converts the data with regex

        :param result: the data to be converted
        :param convert_rule: the rule to convert the data
        :return: converted data
        """
        output = ""
        for line in result.splitlines():
            p = re.compile(convert_rule["input_pattern"])
            match = p.match(line)
            if match is not None:
                replacement = re.sub(convert_rule["input_pattern"],
                                     convert_rule["output_pattern"],
                                     line) + "\n"
                output += replacement
        return output.strip()

    def check_if_lines_are_send_to_db(self, run_metadata, lines_send):
        print("Lines send: {}\n".format(str(lines_send)))
        self.log.debug("Lines send: {}\n".format(str(lines_send)))

        # Check how many rows were written in the database
        print("OOO", run_metadata)
        r = requests.post(self.check_line_count_from_db_url, json = run_metadata)

        print("RRR", r)
        r = r.json()
        lines_received = r['line_count']
        self.log.debug("Lines received in database: {}\n".format(
            str(lines_received)))
        print("Lines received in database: {}\n".format(str(lines_received)))
        # Add error print if the line counts don't match
        if lines_received < lines_send:
            difference = lines_send - lines_received
            print(
                "Not all lines were received at database missing {} lines".format(
                    difference))
            self.log.debug(
                "Not all lines were received at database missing {} lines\n".format(
                    difference))
        elif lines_received > lines_send:
            difference = lines_received - lines_send
            self.log.debug(
                "ERROR. Extra {} lines were received at database\n".format(
                    difference))
            print("ERROR. Extra lines were received at database")

        # Send the results to db
        output = self.log_stream.getvalue()
        output_json = {'output': output}
        output_json.update(run_metadata)
        requests.post(self.save_output_streams_url, json=output_json)
# Class shellog

if __name__ == '__main__':
    # Set the urls for the backend
    servicesDomain = "" if (os.environ.get("SERVICES_DOMAIN") or '' == '') else "." + os.environ.get("SERVICES_DOMAIN")
    log_data_api_Hostname = "localhost" if (os.environ.get("LOG_DATA_API_HOSTNAME") is None) else os.environ.get("LOG_DATA_API_HOSTNAME")
    log_data_api_port = 5000 if (os.environ.get("LOG_DATA_API_PORT") is None) else os.environ.get("LOG_DATA_API_PORT")

    log_data_api = {
        "name": "http://{0}{1}:{2}".format(log_data_api_Hostname, servicesDomain, log_data_api_port),
        "stream_endpoint": "api/save_output_stream",
        "file_output_endpoint": "api/save_file_output",
        "processed_result_endpoint": "api/save_processed_output",
        "binary_file_endpoint": "api/save_binary_file",
        "check_line_count_endpoint": "api/get_line_count"
    }

    urls_for_shellog = {
        'save_output_streams_url': log_data_api['name'] + "/" + log_data_api['stream_endpoint'],
        'save_processed_output_url': log_data_api['name'] + "/" + log_data_api['processed_result_endpoint'],
        'save_file_output_url': log_data_api['name'] + "/" + log_data_api['file_output_endpoint'],
        'save_binary_file_url': log_data_api['name'] + "/" + log_data_api['binary_file_endpoint'],
        'check_line_count_from_db_url': log_data_api['name'] + "/" + log_data_api['check_line_count_endpoint']}
    logger = Shellog(urls_for_shellog)

    # Set the parameter parsing for command line
    parser = argparse.ArgumentParser(description='start and log a process')
    parser.add_argument('-c', '--command', type=str,
                        help='The command to run the process', required=True)
    parser.add_argument('-o', '--output_files', type=str,
                        help='The output files to read the logs from',
                        required=False)
    parser.add_argument('-r', '--rules', type=str,
                        help='The rules to convert the output',
                        required=False)
    parser.add_argument('-i', '--interval', type=float,
                        help='The interval after logs are send to the backend and buffer is flushed',
                        required=False)
    parser.add_argument('-l', '--limit', type=float,
                        help='The time limit after which the process is terminated',
                        required=False)

    # Nivel reference values used in calls to log_data_api
    parser.add_argument('-e', '--entity_id', type=int,
                        help='The id of the Nivel entity to which a function is applied',
                        required=False)
    parser.add_argument('-f', '--function_instance_id', type=int,
                        help='The id of the Nivel function that is being run',
                        required=False)
    parser.add_argument('-a', '--action_instance_id', type=int,
                        help='The id of the Nivel action that is being executed',
                        required=False)

    args = parser.parse_args()

    run_metadata = { "nivel_entity": args.entity_id, "nivel_function": args.function_instance_id, "nivel_action": args.action_instance_id }

    # Parse the command. Separate parts are separated by ,
    parsed_command = [str(item) for item in args.command.split(',')]

    # Parse files separated by ,
    if args.output_files is not None:
        parsed_output_files = [str(item) for item in args.output_files.split(',')]
    else:
        parsed_output_files = None

    # Parse rules separated by ,
    if args.rules is not None:
        parsed_rules = [str(item) for item in args.rules.split(',')]
        json_rules = []
        for rule in parsed_rules:
            f = open(rule, "r")
            rule_as_json = json.load(f)
            json_rules.append(rule_as_json)
    else:
        json_rules = None

    # Set interval and limit
    if args.interval is not None:
        interval = args.interval
    else:
        interval = None
    if args.limit is not None:
        limit = args.limit
    else:
        limit = None

    # Start the process and logging
    logger.start_process_and_send_logs(cmd=parsed_command,
                                       output_files=parsed_output_files,
                                       rules=json_rules,
                                       send_to_db_time_interval=interval,
                                       process_time_limit=limit, run_metadata=run_metadata)
