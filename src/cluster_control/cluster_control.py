import json
import os
import subprocess
import sys
import re
from flask import Flask, request, jsonify

required = {}
running = {}

def apply_yaml(path_to_yaml, action):
    cmd = "kubectl {} -f {}".format(action, path_to_yaml)
    print("Executing command", cmd)
    subprocess.run(cmd, shell = True)

def get_deployments():
    result = subprocess.run(['kubectl', 'get', 'deployments'], stdout=subprocess.PIPE)
    str = result.stdout.decode('ascii')
    lines = re.split('\\n', str)

    header = True
    for line in lines:
        if header:
            header = False
            continue

        parts = re.split(' +', line)

        m = re.match(r'(.+)-(g[0-9]+)', parts[0])
        if m:
           app = m.group(1)
           group = m.group(2)

           running_groups = running.get(app)
           if running_groups:
               running_groups.append(group)
           else:
               running[app] = [group]

def process_configuration(data):
    try:
        data = json.loads(data)
    except:
        print("data.get('kind') failed, type = ", type(data), "data =", data)
        raise

    data.get('kind')
    if data.get('kind') == 'Deployment':
        if not running:
            get_deployments()

        print("processing configuration as a deployment")
        try:
            spec = data.get('spec')
            template = spec.get('template')
            metadata = template.get('metadata')
            labels = metadata.get('labels')
            app = labels.get('app')
            group_id = labels.get('group_id')

            if app and group_id and group_id != 'prod':
                groups = required.get(app)
                if not groups:
                    groups = [group_id]
                    required[app] = groups
                else:
                    groups.append(group_id)
        except:
            print("failed to process the file as a deployment configuration")

if __name__ == '__main__':
    print("This is cluster_control.py with arguments:", sys.argv)

    action = sys.argv[2] if len(sys.argv) >= 3 else 'apply'
    print("The action is ", action)

    with open(sys.argv[1], 'r') as file:
        data = file.read()
        parts = data.split("---")
        for i,part in enumerate(parts):
            filename = "part" + str(i) + '.json'
            print(filename, "is", part)

            process_configuration(part)

            with open(filename, "w") as text_file:
                text_file.write(part)
            apply_yaml(filename, action)
            # os.unlink(filename)

    print("RRR", required)
    print("QQQ", running)
    if required != {}:
        # If test groups have been deployed, removed those deployments that relate to groupd other than production
        for app,groups in running.items():
            req_groups = required.get(app)
            for grp in groups:
                if not grp in req_groups:
                    print("will delete", grp, "with:", "kubectl delete deployment", app+"-" + grp)
                    subprocess.run(['kubectl', 'delete', 'deployment', app + "-" + grp], stdout=subprocess.PIPE)
                else:
                    print("passing", grp)

