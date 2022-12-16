import random
import math
import copy
import json
import time
import requests
import jsonpath_rw as jrw
import numpy as np
import numexpr as ne
from datetime import datetime, timedelta
from formula_solver import Formula_solver, ValueNotFoundException
from timer import Timer
from server import Server, Response

class User:
    """The simulated user

    Repesents a single simulaited user.
    Contains all the information for calculating
    the behaviour of the user.

    Attributes
    ----------
    formula_solver: Formula_solver
        an object used to solve formulas
    timer: Timer
        an object used for handling time
    server: Server
        an object imitating server
    number_of_logs: []int
        Tells the number of times something is added to any user's log_str.
        It is a list with only one value,
        because that way the number is shared by all users
    print_names: []bool
        Tells if the names should be printed (for log_new_line "round").
        It is a list with only one value,
        because that way the number is shared by all users
    identifier: int
        users indentifier
    group: str
        they key/name of the group the user belongs to
    variables: {}
        a dictionary containing user's variables and 
        things used in calculating them
    states: {}
        a dictionary containing user's states and 
        everything related to them
    current_state: {}
        a dictionary containing user's current state and
        data related to the latest action.
    activation_time: int
        The time the user will be active the next time in the simulation
    log_names: []str
        a list of names for the entries of the logs
    log_name_index: int
        index used to keep track which entry name is used in writing
        to log_str
    log_str: str
        a string that is meant to be written in the logs
    log_dict: {}
        a dictionary used for sending the logs to database
    log_new_line: str
        used to tell when new lines are added. It can either be after 
        every round or after every entry (and round).

    Methods
    -------
    update_config(configuration)
        updates the user's 
    do_one_round(users, actions, initial_time, time_format)
        does one round for the user
    error_delay(users)
        Handles the user's delay in case of an error
    """

    formula_solver = Formula_solver()
    timer = Timer()
    server = Server()
    number_of_logs = [0]
    print_names = [True]

    def __init__(self, id, group_id, initial_state, variables, states, log_new_line, nivel_configuration, nivel_function, group_id_reported = None, initial_time = 0):
        """
        Parameters
        ----------
        id: int
            the users personal identifier
        group_id: str
            the key/name of the group the user belongs to
        initial_state: str
            the key/name of the state that the user will start in
        variables: {}
            a dictionary containing user's variables and 
            things used in calculating them 
        states: {}
            a dictionary containing user's states and 
            everything related to them
        log_new_line: str
            used to tell when new lines are added. It can either be after 
            every round or after every entry (and round).
        group_id_reported: str
            an identifier that is used when reporting about the user to the database; 
            enables using the same group definition to create multiple groups (eg. test groups in an experiment or a program thereof)
        """
        
        self.__set_all_personal_coefficients_in_states(states)

        # calculate personal coefficients for variables using their coefficient distibutions
        
        self.identifier = id
        self.group = group_id
        self.group_id_reported = group_id_reported or self.group

        #get variables
        self.variables = {}
        for name in variables:
            personal_coefficients = self.__solve_personal_coefficients(variables[name]["coefficient_distributions"])
            self.variables[name]= {
                "value": variables[name]["initial_value"],
                "personal_coefficients": personal_coefficients
            }

        self.current_state = {
            "main_state": initial_state,
            "substates": {
                "permanents": []
            }
        }
        self.activation_time = initial_time + random.randint(0, 5)
        self.log_name_index = 0
        self.log_str = ""
        self.log_dict = dict()
        self.__set_log_names(self.variables.keys())

        # Save the relevant references with each log line
        self.nivel_configuration = nivel_configuration
        self.nivel_entity = nivel_function

        self.log_dict["nivel_configuration"] = nivel_configuration
        self.log_dict["nivel_function"] = nivel_function

        self.log_new_line = log_new_line
        if (self.log_new_line != "round" and self.log_new_line != "entry"):
            error = f"value of log_new_line was neither 'entry' nor 'round'. It was '{self.log_new_line}'"
            raise Exception(error)
        self.session = requests.Session()
    
    def __set_all_personal_coefficients_in_states(self, states):
        # create states
        personal_states = {}
        for state in states:

            # action weight formulas
            personal_states[state] = {}
            personal_states[state]["action_weight_formulas"] = {}
            for action in states[state]["action_weight_formulas"]:
                personal_states[state]["action_weight_formulas"][action] = {
                    "personal_coefficients": {}
                }
                # calculate action weight formula's coefficients for variables using their coefficient distibutions
                personal_coeffs = self.__solve_personal_coefficients(states[state]["action_weight_formulas"][action]["coefficient_distributions"])
                personal_states[state]["action_weight_formulas"][action]["personal_coefficients"] = personal_coeffs

            # time delay formula
            personal_states[state]["time_delay_formula"] = {
                "personal_coefficients": {},
            }
            # calculate time delay formula's coefficients for variables using their coefficient distibutions
            personal_coeffs = self.__solve_personal_coefficients(states[state]["time_delay_formula"]["coefficient_distributions"])
            personal_states[state]["time_delay_formula"]["personal_coefficients"] = personal_coeffs

            # state transition wieght formulas
            personal_states[state]["state_transition_weight_formulas"] = {}
            for sate_t in states[state]["state_transition_weight_formulas"]:
                personal_states[state]["state_transition_weight_formulas"][sate_t] = {
                    "personal_coefficients": {},
                }
                # calculate state transition weight formula's coefficients for variables using their coefficient distibutions
                personal_coeffs = self.__solve_personal_coefficients(states[state]["state_transition_weight_formulas"][sate_t]["coefficient_distributions"])
                personal_states[state]["state_transition_weight_formulas"][sate_t]["personal_coefficients"] = personal_coeffs
        
        self.states = personal_states

    def __solve_personal_coefficients(self, coeffcient_distributions):
        solved_personal_coefficients = {}
        for name in coeffcient_distributions:
            formula = self.formula_solver.handle_extra_expressions(self, coeffcient_distributions[name])
            value = ne.evaluate(formula)
            solved_personal_coefficients[name] = value

        return solved_personal_coefficients

    def __set_log_names(self, variables):
        self.log_names = ["user", "group", "timestamp", "state"]
        self.log_names.extend(map(lambda name: "_variable_" + name, variables))
        self.log_names.extend(["action", "action_details", "response", "state_new"])
        self.log_names.extend(map(lambda name: "_new_variable_" + name, variables))
        self.log_names.append("delay")

    def update_config(self, configuration, new_variable_names):
        variables = configuration["groups"][self.group]["variables"]
        states = configuration["groups"][self.group]["states"]

        # put values for the new variables
        for name in new_variable_names:
            self.variables[name] = {
                "value": variables[name]["initial_value"]
            }
        
        self.__update_coefficients(variables, states)

        self.__set_log_names(variables.keys())

    def __update_coefficients(self, variables, states):
        # add new personal_coefficients, but keep the old ones if the variable exists (for the variable formulas)
        for name in variables:
            personal_coefficients = copy.deepcopy(variables[name]["coefficients"])
            personal_coefficients = self.__solve_personal_coefficients(personal_coefficients, variables[name]["coefficient_distributions"])

            # use the new coefficient if there is no old one
            for coeff_name in personal_coefficients:
                if coeff_name not in self.variables[name]["personal_coefficients"]:
                    self.variables[name]["personal_coefficients"][coeff_name] = personal_coefficients[coeff_name]

        for state_name in states:
            state = states[state_name]
            # add new personal_coefficients, but keep the old ones if the variable exists (for action weight formulas)
            for awf in state["action_weight_formulas"]:
                awf_personal_coefficients = self.__solve_personal_coefficients(state["action_weight_formulas"][awf]["coefficient_distributions"])

                for coeff_name in awf_personal_coefficients:
                    if coeff_name not in self.states[state_name]["action_weight_formulas"][awf]["personal_coefficients"]:
                        self.states[state_name]["action_weight_formulas"][awf]["personal_coefficients"][coeff_name] = awf_personal_coefficients[coeff_name]

            # add new personal_coefficients, but keep the old ones if the variable exists (for state transition weight formulas) 
            for stwf in state["state_transition_weight_formulas"]:
                stwf_personal_coefficients = self.__solve_personal_coefficients(state["state_transition_weight_formulas"][stwf]["coefficient_distributions"])
                
                for coeff_name in stwf_personal_coefficients:
                    if coeff_name not in self.states[state_name]["state_transition_weight_formulas"][stwf]["personal_coefficients"]:
                        self.states[state_name]["state_transition_weight_formulas"][stwf]["personal_coefficients"][coeff_name] = stwf_personal_coefficients[coeff_name]

            # add new personal_coefficients, but keep the old ones if the variable exists (for time delay formula)
            tdf_personal_coefficients = self.__solve_personal_coefficients(state["time_delay_formula"]["coefficient_distributions"])

            for coeff_name in tdf_personal_coefficients:
                if coeff_name not in self.states[state_name]["time_delay_formula"]["personal_coefficients"]:
                    self.states[state_name]["time_delay_formula"]["personal_coefficients"][coeff_name] = tdf_personal_coefficients[coeff_name]

    def do_one_round(self, users, configuration, initial_time, time_format):
        """Does one round for the user

        One round includes doing an action and deciding the next state.
        All the information needed for the logs will also be added
        to user's log_str.

        Parameters
        ----------
        users: []User
            a list (heap) of all the users
        configuration: {}
            the current simulient configuration
        initial_time: deltatime
            The starting simulation time
        time_format: str
            The format used for telling time
        """

        current_time = self.activation_time
        current_full_time = copy.deepcopy(initial_time) + timedelta(seconds=current_time)
        str_current_full_time = current_full_time.strftime(time_format)

        self.log_str = ""
        self.log_dict = dict()

        self.log_dict["state_details"] = dict()
        self.log_dict["new_state_details"] = dict()

        self.log_name_index = 0
        # add data to a log
        self.__write_log(self.identifier)
        self.__write_log(self.group_id_reported)
        self.__write_log(str_current_full_time)
        self.__write_log(self.current_state["main_state"])
        for variable_name in self.variables:
            self.__write_log(self.variables[variable_name]["value"])
        
        # do action and change state
        self.__do_action(configuration)
        self.__change_state(configuration)
        self.__update_values(configuration)
        self.timer.delay_time(users, configuration)

        # add data to a log
        for variable_name in self.variables:
            self.__write_log(self.variables[variable_name]["value"])
        self.__write_log(self.current_state["substates"].get("delay"))

    def error_delay(self, users):
        """Handles the user's delay in case of an error
        
        Parameters
        ----------
        users: []User
            a list of users
        """
        self.timer.error_delay(users)

    def __do_action(self, configuration):
        """Does an action

        Chooses an action and then does it. The information
        from the action will be stored in the user's substates in 
        current_state. the action and response details will also
        be written to log_str.

        Parameters
        ----------
        configuration: {}
            the current simulient configuration
        """

        server = self.server
        session = self.session
        chosen_action_info = self.__choose_action(configuration)
        actions = configuration["actions"]

        data = ""
        if "l_key" in chosen_action_info["info"]:
            data += "%s[%s][%s]" %(chosen_action_info["key"],
                chosen_action_info["info"]["l_key"],
                chosen_action_info["info"]["index"])
        else:
            data += chosen_action_info["key"]

        chosen_action = actions[chosen_action_info["key"]]

        # check for timeout
        timeout_formula, missing_variables = self.formula_solver.solve_formula(
            self, chosen_action["timeout_formula"]["formula"], chosen_action["timeout_formula"]["coefficients"])
        try:
            timeout_value = ne.evaluate(timeout_formula)
        except TypeError:
            if len(missing_variables) > 0:
                raise ValueNotFoundException(", ".join(missing_variables))
            else:
                raise
        
        timeout = timeout_value >= float(chosen_action["timeout"])
        if timeout:
            chosen_action = actions["timeout_action"]

        self.__write_log(data)

        # solve the pattern and do the action
        pattern = chosen_action["pattern"]
        specified_pattern = self.formula_solver.specify_formula(chosen_action_info["info"], pattern)
        solved_pattern, missing_variables = self.formula_solver.solve_formula(self, specified_pattern, [])
        self.__write_log(json.dumps({**chosen_action, "pattern": solved_pattern}))
        start = time.process_time()
        function = f"def action_function(session, server):  {solved_pattern}"
        exec(function, globals())
        res = action_function(session, server)
        response_time = time.process_time() - start
        status_code = res.status_code

        try:
            res_json = res.json()
        except json.decoder.JSONDecodeError:
            print("Error: Could not extract json from the response:", res.content)
            res_json = {}

        res_dict = json.dumps({"json": res_json, "status": status_code, "headers": dict(res.headers)})
        self.__write_log(res_dict)
        #self.__write_log("{\"status_code\": %s, \"json\": %s" 
        #    %(status_code, json.dumps(res.json)))

        # add data to substates
        new_substates = {
            "permanents": self.current_state["substates"]["permanents"],
            "status_code": status_code,
            "response_time": response_time,
            "delay": self.current_state["substates"].get("delay")
        }

        # keep permanent substates
        for permanent in self.current_state["substates"]["permanents"]:
            new_substates[permanent] = self.current_state["substates"][permanent]

        self.current_state["substates"] = new_substates

        # add data to substates
        for element in chosen_action["response_parsing"]:
            identifier = element["identifier"]
            path = element["jsonpath_expression"]
            if "permanent" in element and element["permanent"]: 
                permanents = self.current_state["substates"]["permanents"]
                if identifier not in permanents: permanents.append(identifier)
            
            par = jrw.parse(path).find(res_json)
            par = None if not par else par[0].value
            self.current_state["substates"][identifier] = par

    def __change_state(self, configuration):
        """Changes the users state

        Gets the state that is chosen and then changes 
        the user's state. It also writes the new state to the log_str.
        """

        chosen_state = self.__choose_state(configuration)
        self.current_state["main_state"] = chosen_state
        self.__write_log(chosen_state)

    def __update_values(self, configuration):
        """Updates the values of the user's variables"""

        for variable_name in self.variables:
            formula = configuration["groups"][self.group]["variables"][variable_name]["formula"]
            coefficients = self.__calculate_coefficients(configuration["groups"][self.group]["variables"][variable_name]["coefficients"], self.variables[variable_name]["personal_coefficients"])
            formula, missing_variables = self.formula_solver.solve_formula(
                self, formula, coefficients)
            
            try:
                self.variables[variable_name]["value"] = ne.evaluate(formula)
            except TypeError:
                if len(missing_variables) > 0:
                    raise ValueNotFoundException(", ".join(missing_variables))
                else:
                    raise


    def __choose_action(self, configuration):
        """Chooses the next action

        Chooses the next action user wants to do and returns its
        information

        Returns
        -------
        dictionary
            the key and info of the action
        """

        state = configuration["groups"][self.group]["states"][self.current_state["main_state"]]
        action_weights, action_infos = self.__action_weights(state)
        chosen_action_info = random.choices(action_infos, weights=action_weights, k=1)[0]
        return chosen_action_info

    def __choose_state(self, configuration):
        """Chooses the next state

        Chooses the next state user wants to change to and returns its
        key/name

        Returns
        -------
        str
            the key/name of the chosen state
        """

        state = configuration["groups"][self.group]["states"][self.current_state["main_state"]]
        state_weights = self.__state_weights(state)
        chosen_state = random.choices(list(
            state["state_transition_weight_formulas"].keys()), weights=state_weights, k=1)[0]

        return chosen_state

    def __action_weights(self, state):
        """Calculates weights for the probability of the actions

        Returns
        -------
        list
            a list of probability weights for the actions
        list
            a list of actions and their information
        """

        weights = []
        action_infos = []
        action_weight_formulas = state["action_weight_formulas"]
        for action in action_weight_formulas:
            formula = action_weight_formulas[action]["formula"]
            coefficients = self.__calculate_coefficients(action_weight_formulas[action]["coefficients"], self.states[self.current_state["main_state"]]["action_weight_formulas"][action]["personal_coefficients"])
            l_key = action_weight_formulas[action]["for_all_in"].strip()
            if l_key:
                l = self.current_state["substates"][l_key]
                for index in range(len(l)):
                    info = {"l_key": l_key, "index": index}
                    specified_formula = self.formula_solver.specify_formula(info, formula)
                    solved_formula, missing_variables = self.formula_solver.solve_formula(self, specified_formula, coefficients)
                    try:
                        weight = ne.evaluate(solved_formula)
                    except TypeError:
                        if len(missing_variables) > 0:
                            raise ValueNotFoundException(", ".join(missing_variables))
                        else:
                            raise
                    
                    action_info = {
                        "info": info,
                        "key": action
                    }
                    weights.append(weight)
                    action_infos.append(action_info)
            else:
                solved_formula, missing_variables = self.formula_solver.solve_formula(
                    self, formula, coefficients)
                try:
                    weight = ne.evaluate(solved_formula)
                except TypeError:
                    if len(missing_variables) > 0:
                        raise ValueNotFoundException(", ".join(missing_variables))
                    else:
                        raise
                
                action= {
                    "info": {},
                    "key": action
                }
                weights.append(max(weight, 0))
                action_infos.append(action)

        return weights, action_infos
    
    def __calculate_coefficients(self, coefficients, peronal_coefficients):
        actual_coefficients = copy.deepcopy(coefficients)
        for variable_name in coefficients:
            actual_coefficients[variable_name] = float(coefficients[variable_name]) * float(peronal_coefficients[variable_name])

        return actual_coefficients



    def __state_weights(self, state):
        """Calculates weights for the probability of the states

        Returns
        -------
        list
            a list of probability weights for the states
        """

        weights = []
        state_transition_weight_formulas = state["state_transition_weight_formulas"]
        for state in state_transition_weight_formulas:
            formula = state_transition_weight_formulas[state]["formula"]
            coefficients = self.__calculate_coefficients(state_transition_weight_formulas[state]["coefficients"], self.states[self.current_state["main_state"]]["state_transition_weight_formulas"][state]["personal_coefficients"])
            formula, missing_variables = self.formula_solver.solve_formula(
                self, formula, coefficients)
            try:
                weight = ne.evaluate(formula)
            except TypeError:
                if len(missing_variables) > 0:
                    raise ValueNotFoundException(", ".join(missing_variables))
                else:
                    raise
            
            weights.append(weight)
        return weights

    def __write_log(self, data):
        """Writes more data to user's log_str and log_dict

        adds data to the user's log_str and log_dict, based on the data given and
        the list of log names. All the users' log_names should be same and
        the data is assumed to be given in the correct order, so that
        the method knows which name the data relates to.
        The variable log_new_line determinates the format for the log.

        Parameters
        ----------
        data: str
            data is the string that will be added to the log_str and log_dict
        """

        def filter_name(name):
            if name.startswith("_variable_"):
                return name[10:]
            elif name.startswith("_new_variable_"):
                return name[14:]
            else:
                return name
        
        name = self.log_names[self.log_name_index]
        
        # write log_dict
        if type(data) is np.ndarray:
            # check if the data is an old or new variable
            if name.startswith("_variable_"):
                self.log_dict["state_details"][name[10:]] = data.tolist()
            elif name.startswith("_new_variable_"):
                self.log_dict["new_state_details"][name[14:]] = data.tolist()
            else:
                self.log_dict[name] = data.tolist()
        else:
            # check if the data is an old or new variable
            if name.startswith("_variable_"):
                self.log_dict["state_details"][name[10:]] = data
            elif name.startswith("_new_variable_"):
                self.log_dict["new_state_details"][name[14:]] = data
            else:
                self.log_dict[name] = data
        
        # write log_str
        if self.log_new_line == "entry":
            self.log_str += f"{filter_name(name)}:\t{data}\n"
            self.log_name_index += 1
            self.number_of_logs[0] += 1
        elif self.log_new_line == "round":
            if self.print_names[0]:
                self.log_str += "\t".join(map(filter_name, self.log_names)) + "\n"
                self.print_names[0] = False
            self.log_str += f"{data}\t"
            self.log_name_index += 1
            self.number_of_logs[0] += 1
        
        # check if it is the last log of the round (delay)
        if self.log_name_index == len(self.log_names):
            self.log_str += "\n"

    def __lt__(self, other):
        return self.activation_time < other.activation_time

    def __eq__(self, other):
        return self.activation_time == other.activation_time

    def __gt__(self, other):
        return self.activation_time > other.activation_time
