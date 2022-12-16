import subprocess
import base64
import os
import json

from flask import Flask, jsonify, request, Response

app = Flask(__name__)


@app.route('/api', methods=['GET'])
def api_index():
    return jsonify({'message': 'This is simulient-api'})


@app.route('/api', methods=['POST'])
def launch_shellog():
    parameters = request.json
    parameters = json.loads(parameters)

    # Save files
    if "files" in parameters:
        for file in parameters["files"]:
            file_name = file["name"]
            file_data = file["content_base64"]
            file_data = base64.b64decode(file_data)
            with open(file_name, 'wb') as f:
                f.write(file_data)

    # Get the parameters for shellog
    shellog_params = parameters["shellog_params"]
    payload_command = parameters["payload_command"]
    cmd = ["python3", "shellog.py", "-c", payload_command]
    if "output_files" in shellog_params:
        cmd.append("-o")
        cmd.append(shellog_params["output_files"])
    if "rules" in shellog_params:
        cmd.append("-r")
        cmd.append(shellog_params["rules"])
    if "interval" in shellog_params:
        cmd.append("-i")
        cmd.append(shellog_params["interval"])
    if "limit" in shellog_params:
        cmd.append("-l")
        cmd.append(shellog_params["limit"])

    is_async = parameters.get("async")

    if parameters.get("entity_id"):
        cmd.append("-e")
        cmd.append(str(parameters.get("entity_id")))
    if parameters.get("function_instance_id"):
        cmd.append("-f")
        cmd.append(str(parameters.get("function_instance_id")))
    if parameters.get("action_instance_id"):
        cmd.append("-a")
        cmd.append(str(parameters.get("action_instance_id")))

    # Get the working directory
    output_of_pwd = subprocess.run(['pwd'], text = True, capture_output = True)
    working_directory = output_of_pwd.stdout.strip()

    # Run shellog
    if is_async:
        subprocess.Popen(cmd, cwd = working_directory)
        async_text = "async"
    else:
        result = subprocess.run(cmd, capture_output=True, cwd=working_directory)
        print(result.stdout.decode())
        print(result.stderr.decode())
        async_text = "syncrhronous mode"

    # Remove files
    if "files" in parameters:
        for file in parameters["files"]:
            try:
                os.remove(file["name"])
            except OSError as e:
                print("Error: %s : %s" % (file["name"], e.strerror))

    response_file = parameters.get("response_file")
    response_data = None
    if response_file:
        with open(response_file, 'r') as file:
            response_data = file.read()

    return Response(status=200, response = response_data or 'POST operation completed successfully, payload_command = ' + payload_command)

if __name__ == '__main__':
    app.run()
