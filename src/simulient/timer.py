import heapq
import numexpr as ne
from formula_solver import Formula_solver, ValueNotFoundException


class Timer:
    """Handles passage of time

    Attributes
    ----------
    formula_solver: Formula_solver
        used to solve formulas
    current_time: int
        the current time in simulation
    """

    formula_solver = Formula_solver()
    current_time = 0

    def delay_time(self, users, configuration):
        """Handles the users' delays
        
        Calculates the delay (minimum of 1) that the active user will have,
        then updates the users activation_time and
        saves the delay in substates.
        Will then also update the heap of users to 
        keep the next user at top.

        Parameters
        ----------
        users: []User
            a list of users
        configucation: {}
            the simulient configuration
        """

        active_user = heapq.heappop(users)
        try:
            time_delay = max(self.__time_delay(active_user, configuration), 1)
        except:
            heapq.heappush(users, active_user)
            raise
        active_user.activation_time += time_delay
        active_user.current_state["substates"]["delay"] = time_delay
        heapq.heappush(users, active_user)

    def __time_delay(self, user, configuration):
        """Calculates the actual delay in time

        Uses the formula_solver to solve formula so it can be
        evaluated. The evalueted is then rounded to become an integer.

        Parameters
        ----------
        user: User
            the user whose delay is calculated

        Returns
        -------
        integer
            the users delay as integer
        """
        time_delay_formula = configuration["groups"][user.group]["states"][user.current_state["main_state"]]["time_delay_formula"]
        formula = time_delay_formula["formula"]
        coefficients = time_delay_formula["coefficients"]
        formula, missing_variables = self.formula_solver.solve_formula(
            user, formula, coefficients)
        try:
            value = float(ne.evaluate(formula))
        except TypeError:
            if len(missing_variables) > 0:
                raise ValueNotFoundException(", ".join(missing_variables))
            else:
                raise
        return round(value)
    
    def error_delay(self, users):
        """Handles the user's delay in case of an error

        Uses the old delay or default delay of 15.

        Parameters
        ----------
        users: []User
            a list of users

        """
        active_user = heapq.heappop(users)
        active_user.current_state["substates"]["delay"] = active_user.current_state["substates"].get("delay") or 15
        active_user.activation_time += active_user.current_state["substates"]["delay"]
        heapq.heappush(users, active_user)
