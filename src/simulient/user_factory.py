import json, heapq
from user import User

class User_factory:
    """Creates the users

    Creates all the users for all the groups as
    defined in configuratoin and gives them
    their own identifiers.
    """
    id = 1

    def create_users(self, configuration, log_new_line, nivel_configuration, nivel_function):
        """Creates the users

        Creates all the users for all the groups as
        definned in configuratoin and gives them
        their own identifiers.

        Parameters
        ----------
        configuration: dict
            the simulients configuration as a dictionary

        Returns
        --------
        list
            all the created users as a list
        """

        created_users = []
        groups = configuration["groups"]
        users = configuration["users"]
        
		
        number_of_users_by_group = dict()
        for user in users:
            group_id = user["group"]
            group_id_reported = user.get("group_id") or user["group"]
            variables = groups[group_id]["variables"]
            states = groups[group_id]["states"]
            initial_state = groups[group_id]["initial_state"]

            number_of_users_by_group[group_id_reported] = int(user["number_of_users"])

            for i in range(int(user["number_of_users"])):
                u = User(self.id, group_id, initial_state, variables, states, log_new_line, nivel_configuration, nivel_function, group_id_reported)
                created_users.append(u)
                self.id += 1

        return created_users, number_of_users_by_group

    def add_users(self, users, user_group, group_id, number_of_new_users, configuration, log_new_line, nivel_configuration, nivel_function, group_id_reported=None, current_time = 0):
        groups = configuration["groups"]
        group_id = user_group["group"]
        variables = groups[group_id]["variables"]
        states = groups[group_id]["states"]
        initial_state = groups[group_id]["initial_state"]

        for i in range(number_of_new_users):
            u = User(self.id, group_id, initial_state, variables, states, log_new_line, nivel_configuration, nivel_function, group_id_reported = group_id_reported, initial_time=current_time)
            heapq.heappush(users, u)
            self.id += 1
