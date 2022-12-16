import shutil
import subprocess
import sys
import os
import requests
import ast

# inplace replace in files
import fileinput
import re

def build(repository, tag, variables, group_id = None):
    dir_path_to_temp = '/app/temp'
    registry_user_name = server = os.environ['REGISTRY_USER_NAME']

    # Get the repository name and path
    # The input parameter repository is eg. https://version.helsinki.fi/test_group_xcese/test-app-parameters.git
    repository_name = repository.split("/")[-1].split(".")[0]
    dir_path_to_repo = dir_path_to_temp + '/' + repository_name

    try:
        os.mkdir(dir_path_to_repo)
    except:
        pass

    # Clone the repo to the /temp folder
    print("preparing to clone from the repository", repository, "tag", tag)
    cmd = ['git', 'clone', '--single-branch', '--depth', '1', '-b', tag, repository]
    subprocess.run(cmd, cwd = dir_path_to_temp, universal_newlines = True)

    # 2021-01-25
    # Convert the variables to the desired format, ie. a simple key-value dictionary
    var_output = {}
    if False: # for st in variables:
        key = st['key']
        value = st['value']
        var_output[key] = value

    # NB The parameter should alread be in the correct form (dictionary)
    var_output = variables

    _,_, filenames = next(os.walk(dir_path_to_repo))

    # Replace the occurrances of $$ in Python files (.py) with the variables as a dictionary {...}'
    for file in filenames:
        if re.search(".*\.py$", file):
            with open(dir_path_to_repo + "/" + file) as f:
                content = f.readlines()
                print("the file is", file)
                filename = str(file)
                for line in content:
                    print(line, end = '')
            with fileinput.FileInput(dir_path_to_repo + "/" + file, inplace = True, backup='.bak') as file:
                for line in file:
                    print(line.replace("$$", str(var_output)), end='')
            with open(dir_path_to_repo + "/" + filename) as f:
                content = f.readlines()
                print("after editing the file is", filename)
                for line in content:
                    print(line, end = '')
    if group_id:
        build_tag = "g" + str(group_id)
    else:
        build_tag = tag

    # Build and tag the image
    image_name = registry_user_name + '/' + repository_name + ':' + build_tag # + tag + repository_tag_extension
    print("starting docker build", image_name)
    cmd = ['docker', 'build', '.', '-t', image_name]
    subprocess.run(cmd, cwd = dir_path_to_repo, universal_newlines = True)

    # Get the Dockerhub registry token
    registry_token = os.environ["REGISTRY_TOKEN"]

    # Login to docker
    cmd = 'docker login --username ' + registry_user_name + ' --password ' + registry_token
    print("logging in to docker")
    subprocess.run(cmd, shell = True, cwd = dir_path_to_repo, universal_newlines = True)

    # Push to Dockerhub
    print("pushing to docker hub", image_name)
    cmd = ['docker', 'push', image_name]
    subprocess.run(cmd, cwd=dir_path_to_repo, universal_newlines = True)

    # Logout from docker
    print("logging out from docker")
    cmd = ['docker', 'logout']
    subprocess.run(cmd, cwd=dir_path_to_repo, universal_newlines = True)

    # Remove the repo
    print("removing the local copy of the repository")
    try:
        # pass
        shutil.rmtree(dir_path_to_repo)
    except OSError as e:
        print("Error: %s : %s" % (dir_path_to_repo, e.strerror))

    print("builder is ready")

if __name__ == '__main__':
    # print("argv[1]/mode", sys.argv[1], "argv[2]/repository(link)", data_url, "argv[3]/tag", sys.argv[3], "argv[4]/datapi/data/_entity_id", sys.argv[4])
    # eg. ['builder.py', 'experiment', 'http://localhost:5004/data/1002257'] <- 0, 1, 2
    print(sys.argv)

    mode = sys.argv[1]

    groups = []
    control_group = None

    data_url = sys.argv[2] # for mode == service || experiment

    # Calls of these forms can be found in the database
    # {$_nivel_function_config,"shellog_params": {"interval":"5.0"},"payload_command": "python3,builder.py,single,$repository,$tag,http://localhost:5004/data/$_entity_id"}
    # {$_nivel_function_config,"shellog_params": {"interval":"5.0"},"payload_command": "python3,builder.py,experiment,http://localhost:5004/data/$_entity_id"}
    # {$_nivel_function_config,"shellog_params": {"interval":"5.0"},"payload_command": "python3,builder.py,service,http://localhost:5004/data/$_entity_id"}
    # mode == 'experiment': somehow goes through the active groups in an experiment and builds the required images
    # .. single: apparently builds a single image based on the parameters
    # .. service: this is unclear (2022-09-29)
    if mode == 'single':
        response = requests.get(sys.argv[4])
        if response.status_code == 200:
            variables = response.json()["data"]["build_variables"]
            print("Variables", variables)
        else:
            raise Exception("Could not get the entity data using the API (sys.argv[3])")

        print("Building a single repository")
        build(sys.argv[2], sys.argv[3], variables) # , source_repository_address = sys.argv[3])
    elif mode == 'experiment':
        response = requests.get(data_url)
        if response.status_code == 200:
            experiment_data = response.json()["data"]
        else:
            print(response)
            raise Exception("Could not get the entity data using the API " + data_url + ")")

        control_group = experiment_data["control_group"]
        groups = experiment_data["test_group"]
        groups.append(control_group)
    elif mode == 'service':
        response = requests.get(data_url)
        if response.status_code == 200:
            experiment_data = response.json()["data"]
        else:
            print(response)
            raise Exception("Could not get the entity data using the API " + data_url + ")")

        routes = experiment_data['routes']
        print("RRR", routes, type(routes))

        res = ast.literal_eval(routes)
        print("QQQ", res, type(res))

        # for el in res:
        #    print("EEE", el, type(el))

        tg = ast.literal_eval(res[0]['test_groups'])
        # tg = ast.literal_eval(tgstr)
        print("TTT", tg, type(tg))

        for el in tg:
            address = re.sub('[0-9]+$', el, data_url)
            response = requests.get(address)
            if response.status_code == 200:
                group = response.json()["data"]
                groups.append(group)
    else:
        raise Exception("Unrecognized mode (" + mode + ")")

    if groups != []:
        for group in groups:
            variables = {}
            # This results in the variables of the control group to be used as default
            # This semantics has not actually been in use, so let's add an if to that
            if control_group:
                for var_str in control_group["variables"][:]:
                    variables[var_str["key"]] = var_str["value"]

            for var in group["variables"]:
                variables[var["key"]] = var["value"]

            implementations = group.get("implementation")

            if not implementations:
                print("No implementation:", group["identifier"], group["_id"], variables)
                next

            if type(implementations) != list:
                implementations = [implementations]

            for impl in implementations:
                build_vars = {}
                bv_source = impl.get("build_variables")
                for bv in bv_source:
                    build_vars[bv["key"]] = bv["value"]
                    group_value = variables[bv["key"]]
                    if group_value:
                        build_vars[bv["key"]] = group_value

                print("build", impl["repository"], impl["tag"], build_vars, group["_id"])
                build(impl["repository"], impl["tag"], build_vars, group["_id"])

        print("About to build an experiment with data", experiment_data)

