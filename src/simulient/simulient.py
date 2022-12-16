# import pyodbc
import heapq
import json
import numexpr as ne
import time
import os, sys
import requests
from datetime import datetime, timedelta
from user import User
from user_factory import User_factory
from formula_solver import ValueNotFoundException
import re

servicesDomain = "" if (os.environ.get("SERVICES_DOMAIN") or '' == '') else "." + os.environ.get("SERVICES_DOMAIN")
log_data_api_Hostname = "localhost" if (os.environ.get("LOG_DATA_API_HOSTNAME") is None) else os.environ.get("LOG_DATA_API_HOSTNAME")
log_data_api_port = 5002 if (os.environ.get("LOG_DATA_API_PORT") is None) else os.environ.get("LOG_DATA_API_PORT")

log_data_api_url = "http://{0}{1}:{2}/api".format(log_data_api_Hostname, servicesDomain, log_data_api_port)

def check_for_simulient_shut_down(conf):
    if conf.get("shut_down_simulient") == "1":
        print("Recieved order to shut down. Shutting dowm.")
        sys.exit(0)

def change_to_float(num):
    return float(num)

def transform_coefficients(coefficients, f=None):
    coeff_dict = dict()
    for coeff in coefficients:
        value = f(coeff["value"]) if f is not None else coeff["value"]
        coeff_dict[coeff["key"]] = value

    return coeff_dict

def transform_variables(variables):
    t_variables = dict()
    if variables is None:
        return t_variables

    for variable in variables if isinstance(variables, list) else [variables]:
        t_variable = {}
        key = variable["key"]

        t_variable["initial_value"] = variable["initial_value"]
        t_variable["formula"] = variable["formula"]
        t_variable["coefficients"] = transform_coefficients(variable["coefficients"], f=float)
        t_variable["coefficient_distributions"] = transform_coefficients(variable["coefficient_distributions"])

        t_variables[key] = t_variable
    
    return t_variables

# Change the data gotten from the api to the correct form of the configuration
def reform_config_data(configuration):
    def change_to_float(num):
        return float(num)

    # Makes sure it is a list and change the list of groups to a dictionary
    groups_dict = dict()
    for group in configuration["groups"] if isinstance(configuration["groups"], list) else [configuration["groups"]]:
        key = group["key"]

        variables = group["variables"]
        variables = transform_variables(variables)
        group["variables"] = variables


        # Makes sure it is a list and change the list of States to a dictionary
        state_dict = dict()
        for state in group["states"] if isinstance(group["states"], list) else [group["states"]]:
            state_key = state["key"]

            # Makes sure it is a list and change the list of action weight formulas (awf) to a dictionary
            awf_dict = dict()
            for awf in state["action_weight_formulas"] if isinstance(state["action_weight_formulas"], list) else [state["action_weight_formulas"]]:
                awf_key = awf["key"]
                t_awf = dict()

                # make sure for_all_in exists
                t_awf["for_all_in"] = awf.get("for_all_in") or ""
                t_awf["formula"] = awf.get("formula") or ""

                # transform coefficients
                t_awf["coefficients"] = transform_coefficients(awf.get("coefficients"), float)
                t_awf["coefficient_distributions"] = transform_coefficients(awf.get("coefficient_distributions"))

                awf_dict[awf_key] = t_awf
            state["action_weight_formulas"] = awf_dict


            # time_delay_formula (tdf)
            tdf = state["time_delay_formula"]
            t_tdf = dict()

            t_tdf["formula"] = tdf.get("formula") or ""

            t_tdf["coefficients"] = transform_coefficients(tdf.get("coefficients"), f=float)
            t_tdf["coefficient_distributions"] = transform_coefficients(tdf.get("coefficient_distributions"))


            state["time_delay_formula"] = t_tdf

            # Makes sure it is a list and change the list of state transition weight formulas (stwf) to a dictionary
            stwf_dict = dict()
            for stwf in state["state_transition_weight_formulas"] if isinstance(state["state_transition_weight_formulas"], list) else [state["state_transition_weight_formulas"]]:
                stwf_key = stwf["key"]

                t_stwf = dict()

                t_stwf["formula"] = stwf.get("formula") or ""
                
                t_stwf["coefficients"] = transform_coefficients(stwf.get("coefficients"), f=float)
                t_stwf["coefficient_distributions"] = transform_coefficients(stwf.get("coefficient_distributions"))

                stwf_dict[stwf_key] = t_stwf
            state["state_transition_weight_formulas"] = stwf_dict

            state_dict[state_key] = state
        
        group["states"] = state_dict
        groups_dict[key] = group
 
    configuration["groups"] = groups_dict

    # make use users is a list
    if not isinstance(configuration["users"], list):
        configuration["users"] = [configuration["users"]]

    # make sure "number_of_users" is integer
    for user in configuration["users"]:
        user["number_of_users"] = int(user["number_of_users"])

    # change list of actions to a dictionary
    actions_dict = dict()
    for action in configuration["actions"] if isinstance(configuration["actions"], list) else [configuration["actions"]]:
        key = action["key"]
        action["timeout"] = float(action["timeout"])

        # correct the key
        action["timeout_formula"] = action.pop("timeout_formula_ref", None)
        
        tf = action["timeout_formula"]
        # make sure the coefficients exist
        tf["coefficients"] = tf.get("coefficients") or []
        tf["coefficient_distributions"] = tf.get("coefficient_distributions") or []
        # make sure it's also a list
        if not isinstance(tf["coefficients"], list): tf["coefficients"] = [tf["coefficients"]]
        tf["coefficients"] = list(map(change_to_float, tf["coefficients"]))

        if not isinstance(tf["coefficient_distributions"], list): tf["coefficient_distributions"] = [tf["coefficient_distributions"]]

        # make sure that response_parsing exists and that it is a list
        action["response_parsing"] = action.get("response_parsing") or []
        if not isinstance(action["response_parsing"], list): action["response_parsing"] = [action["response_parsing"]]

        action["timeout_formula"] = tf
        actions_dict[key] = action

    configuration["actions"] = actions_dict
    configuration["delay"] = float(configuration["delay"])
    configuration["total_time"] = int(configuration["total_time"])

def refresh_config(users, configuration, number_of_users_by_group, current_time, user_factory, configuration_name, log_new_line, configuration_id, function_instance_id):

    if configuration_name.startswith("http://") or configuration_name.startswith("https://"):
        response = requests.get(configuration_name)
        if response.status_code == 200:
            new_configuration = response.json()["data"]
            reform_config_data(new_configuration)
        else:
            print("Fetching the configuration failed, returning the previous configuration.")
            return configuration, number_of_users_by_group
    else:
        new_configurationJson = open(configuration_name)
        new_configuration = json.load(new_configurationJson)

    # make a dictionary where you can find old and new index of a variable
    # seperated by groups
    names_to_idexes = dict()
    change = False

    new_variable_names = {}
    for group in new_configuration["groups"]:
        names_to_idexes[group] = dict()

        # get old and new variables
        variables = new_configuration["groups"][group]["variables"]
        if group in configuration["groups"]:
            old_variables = configuration["groups"][group]["variables"]
            new_variable_names[group] = set(variables.keys()) - set(old_variables.keys())
            if new_variable_names[group]:
                change = True
        else:
            change = True

    if change:
        if len(users) > 0:
            users[0].print_names[0] = True
        for user in users:
            user.update_config(new_configuration, new_variable_names[user.group])

    configuration = new_configuration
        

    # add more users into a group if necessary
    for index, user_group in enumerate(configuration["users"]):
        group_id = user_group["group"]
        group_id_reported = user_group.get("group_id") or user_group["group"]

        # if there is a new group add the required amount
        if group_id_reported not in number_of_users_by_group:
            user_factory.add_users(users, user_group, group_id, user_group["number_of_users"], configuration, log_new_line, configuration_id, function_instance_id, group_id_reported=group_id_reported, current_time=current_time)
            number_of_users_by_group[group_id_reported] = user_group["number_of_users"]

        # if the number of users in a group has risen add the amount needed
        elif user_group["number_of_users"] > number_of_users_by_group[group_id_reported]:
            amount_of_new_users = user_group["number_of_users"] - number_of_users_by_group[group_id_reported]
            user_factory.add_users(users, user_group, group_id, amount_of_new_users, configuration, log_new_line, configuration_id, function_instance_id, group_id_reported=group_id_reported, current_time=current_time)
            number_of_users_by_group[group_id_reported] = user_group["number_of_users"]

    return configuration, number_of_users_by_group

def main():
    overall_start = time.time()

    user_factory = User_factory()

    # get some variables from configurations
    run_id = None
    configuration_id = None
    function_instance_id = None
    action_instance_id = None

    try:
        configuration_name = sys.argv[1]
        log_new_line = sys.argv[2]
        if configuration_name.startswith("http://") or configuration_name.startswith("https://"):
            parts = re.split("/", configuration_name)
            configuration_id = parts[-1]
            function_instance_id = sys.argv[5]
            action_instance_id = sys.argv[6]
            response = requests.get(configuration_name)

            if response.status_code == 200:
                configuration = response.json()["data"]
                reform_config_data(configuration)
        else:
            configurationJson = open(configuration_name)
            configuration = json.load(configurationJson)
    except IndexError:
        print(f"You need at least two arguments: {os.path.basename(__file__)} <configuration.json or endpoint url> <log_new_line(round/entry)> <OPTIONAL time_scale) <OPTIONAL output(file/stdout/database)> <OPTIONAL function_instance_id> <OPTIONAL action_instance_id> <OPTIONAL starting_time (YYYY-mm-dd HH:MM:SS)>")
        print("function_instance_id must be provided if configuration is obtained using an endpoint")
        sys.exit(1)

    check_for_simulient_shut_down(configuration)

    # 2020-12-22 Verify that the parameters are passed in correctly
    # print("configuration_name", configuration_name, "function_instance_id", function_instance_id, "action_instance_id", action_instance_id)
    actions = configuration["actions"]
    total_time = int(configuration["total_time"])
    delay = float(configuration["delay"])

    time_format = "%Y-%m-%d %H:%M:%S"
    # interval in which the configuration is checked again
    configuration_interval = 10

    try:
        time_scale = float(sys.argv[3])
    except IndexError:
        time_scale = 0

    try:
        output = sys.argv[4]
    except IndexError:
        try:
            output = configuration["output"]
        except KeyError:
            output = "file"

    try:
        starting_time = sys.argv[7]
        configuration["initial_time"] = starting_time
        starting_time = datetime.strptime(starting_time, time_format)
    except:
        print("No starting time was set or given. Starting immediately.")
        starting_time = 0

    initial_time = datetime.strptime(configuration["initial_time"], time_format)

    # create users
    users, number_of_users_by_group = user_factory.create_users(configuration, log_new_line, configuration_id, function_instance_id)
    number_of_users = len(users)
    heapq.heapify(users)

    # pass time
    current_time = 0
    log_time = 0
    round_times = []
    real_time = datetime.now().strftime("%Y-%m-%d %H.%M.%S")
    if output == "file":
        if not os.path.exists('logs'):
            os.mkdir("./logs")
        log = open("./logs/" + real_time + ".txt", "w")

    # wait till starting time
    t = time.time()
    if starting_time != 0 and starting_time.timestamp() > t:
        time.sleep(starting_time.timestamp() - t)

    simulation_start = time.time()
    last_config_refresh = time.time()
    while (current_time <= total_time):
        round_start = time.time()

        # get active user and check if going overtime
        active_user = users[0]
        current_time = active_user.activation_time

        if current_time > total_time:
            continue

        # refresh simulient configuration
        if time.time() - last_config_refresh > configuration_interval:
            print("Refreshing configuration...")
            configuration, number_of_users_by_group = refresh_config(users, configuration, number_of_users_by_group, current_time, user_factory, configuration_name, log_new_line, configuration_id, function_instance_id)
            number_of_users = len(users)
            delay = float(configuration["delay"])
            total_time = int(configuration["total_time"])
            last_config_refresh = time.time()
            print("Configuration was refreshed.")
            check_for_simulient_shut_down(configuration)

        simulation_time = time.time() - simulation_start

        if time_scale > 0 and (simulation_time*time_scale) < (current_time):
            time.sleep((current_time - simulation_time*time_scale)/time_scale)

        time.sleep(delay)
        # time_format, actions, 
        try:
            active_user.do_one_round(users, configuration, initial_time, time_format)
        except ValueNotFoundException as e:
            active_user.error_delay(users)
            active_user.log_str += f"Error: Couldn't evaluate a formula with the following missing placeholder values: {e}.\n"
            active_user.log_dict["error"] = {"message": "Couldn't evaluate a formula with missing placeholder values.", "value": str(e)}

        # actually write the log
        log_time_start = time.time()
        if output == "file":
            log.write(active_user.log_str)

        elif output == "stdout":
            print(active_user.log_str, end="")

        elif output == "database":
            required_log_dict_values = ["user", "timestamp", "state", "action", "action_details","response", "state_new", "delay", "group"]
            log_dict = active_user.log_dict
            run_dict = dict()
            run_dict["run_id"] = run_id

            for required_log_dict_value in required_log_dict_values:
                if required_log_dict_value not in log_dict:
                    log_dict[required_log_dict_value] = None

            if not run_id:
                run_dict["nivel_configuration"] = configuration_id
                run_dict["nivel_function"] = function_instance_id
                run_dict["nivel_action"] = action_instance_id
                run_dict["initial_time"] = initial_time.strftime(time_format)
                run_dict["time_scale"] = time_scale
                run_dict["total_time"] = total_time
                run_dict["delay"] = delay
                run_dict["output"] = output

            response = requests.post(url=f"{log_data_api_url}/log_simulient", headers={"Content-Type": "application/json"}, json={"log":log_dict, "run": run_dict, "time_format": time_format})

            if response.status_code == 200:
                response_dict = response.json()
                run_id = response_dict["run_id"]
            elif response.status_code == 400:
                error = response.json()["error"]
                print(error)
        else:
            raise ValueError('The output channel', output, 'is not supported.')
        log_time += time.time() - log_time_start

        round_times.append(time.time() - round_start)
    if output == "file":
        log.close()

    exit_time = initial_time + timedelta(seconds=total_time)

    print("---END STATS---")
    if (len(round_times) != 0):
        round_times.sort()
        shortest_round_time = round_times[0]
        longest_round_time = round_times[-1]
        average_round_time = sum(round_times) / len(round_times)
        print(f"Longest round time was {longest_round_time} seconds, \nthe shortest was {shortest_round_time} seconds and \nthe average was {average_round_time} seconds.")
    print(f"There were total of {len(round_times)} rounds.")
    print(f"Time spent on writing logs: {log_time}")
    print(f"simulation took {time.time() - overall_start} seconds")
    users_str = "User groups: "
    for index, user in enumerate(configuration["users"]):
        users_str += f"{user['group']} {user['number_of_users']}"
        if (index != (len(configuration["users"]) - 1)):
            users_str += ", "
    print(users_str)
    print(f"Created {number_of_users} users, for {total_time}s. The exit (simulated) time was {exit_time.strftime(time_format)}")
    print("-----------------")
    for user in users:
        print(f"Variables of user {user.identifier}:")
        for  variable_name in user.variables:
            print(f"{variable_name}: {user.variables[variable_name]['value']}")
        print("-----------------")

if __name__ == "__main__":
    main()
