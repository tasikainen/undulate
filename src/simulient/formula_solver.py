import re
import numpy as np
import numexpr as ne

class ValueNotFoundException(Exception):
    """Raised when solver finds no value for a placeholder."""
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class Formula_solver:
    """Solves formulas

    Formula_solver solves the variables and expressions that need to
    be changed to their actual values before futher calculations are done
    with numexpr or eval().
    """

    def solve_formula(self, user, formula, coefficients):
        """Solves formulas

        Formula_solver solves the variables and expressions that need to
        be changed to their actual values before futher calculations are done
        with numexpr or eval().

        Parameters
        ----------
        user: User
            the user the formula is for
        formula: str
            the formula that needs tp be solved
        coefficients: []float
            coefficients of the formula as a list of floats

        Returns
        -------
        str
            the formula where the variables and expressions 
            have been replaced with their values
        """
        
        exit = False
        body = formula
        variables = []
        missing_variables = set()

        # find all variables between </ >
        while not exit:
            try:
                start = body.index("</")
            except:

                exit = True
                continue
            body = body[start+2:]

            try:
                end = body.index(">")
            except:
                exit = True
                continue

            variable = body[:end]
            variables.append(variable)
            body = body[end+1:]

        # replace variables with their values
        new_formula = formula
        for variable in variables:
            parts = variable.split(".")

            new_variable = "user."
            if parts[0].strip() == "var":
                variable_name = parts[1].strip()
                if parts[2].strip() == "coeff":
                    new_formula = new_formula.replace(
                        f"</{variable}>", str(coefficients[variable_name]))
                    continue
                elif parts[2].strip() == "value":
                    new_variable += "variables"
                    new_variable += f"['{variable_name}']['value']"
                else:
                    print("variable's kind not recognized")
            elif parts[0].strip() == "state":
                new_variable += "current_state['substates']"
                new_variable += f"['{parts[1].strip()}']"
                for index in range(2, len(parts)):
                    try:
                        number = int(parts[index].strip())
                        new_variable += f"[{number}]"
                    except:
                        new_variable += f"['{parts[index]}']"
            elif parts[0].strip() == "user" and parts[1].strip() == "group":
                 new_variable = 'user.group'
            else:
                # What happends here?
                new_variable += parts[0].strip()
                for index in range(1, len(parts)):
                    try:
                        number = int(parts[index].strip())
                        new_variable += f"[{number}]"
                    except:
                        new_variable += f"['{parts[index].strip()}']"

            try:
                value = str(eval(new_variable))
            except KeyError:
                value = "None"

            if value == "None":
                missing_variables.add(f"</{variable}>")
            
            new_formula = new_formula.replace(f"</{variable}>", value)

        new_formula = self.handle_extra_expressions(user, new_formula)
        return new_formula.strip(), missing_variables

    def handle_extra_expressions(self, user, formula):
        """Handles expressions

        Changes expressions to their actual values. Currently finds
        normal(mu, sigma) and replaces it with a sample from
        normal distripution defined by the mu and sigma.

        Parameters
        ----------
        user: User
            the user the formula is for
        formula: str
            the formula that needs tp be solved

        Returns
        -------
        str
            the formula where the expressions 
            have been replaced with their values
        """

        exit = False
        new_formula = formula
        # replace normal()s with random samples from the specified normal distripution
        while not exit:
            body = new_formula
            # find starting point
            try:
                start = body.index("normal(") + 7
            except:
                exit = True
                continue
            body = body[start:]
            brackets = 1
            end = -1
            # find the correct closing bracket and the comma seperating mean and deviation
            while brackets != 0:
                end += 1
                if body[end] == "(":
                    brackets += 1
                    continue
                if body[end] == ")":
                    brackets -= 1
                    continue
                if body[end] == "," and brackets == 1:
                    split = end
            params = new_formula[start:end+start]
            split_params = [params[:split], params[split+1:]]
            # if the even the params have "extra expressions" such as normal(), handle them again
            try:
                mu = float(ne.evaluate(split_params[0].strip()))
            except:
                mu = float(self.handle_extra_expressions(
                    user, split_params[0].strip()))
            try:
                sigma = float(ne.evaluate(split_params[1].strip()))
            except:
                sigma = float(self.handle_extra_expressions(
                    user, split_params[1].strip()))

            value = np.random.normal(mu, sigma)
            new_formula = new_formula.replace(
                f"normal({params})", str(value), 1)

        return new_formula

    def specify_formula(self, info, formula):
        """Specifies a common formula
        
        Specifies the formula when the formula is used for 
        multiple actions with some changes. Currently changes
        the right index in actions created based on a list.

        Parameters
        -----------
        info: {}
            a dictionary containing information such as what index
            the formula is based on and the key to the list in substates.
        formula: str
            the formula that needs to be specified

        Returns
        --------
        str
            the new specified formula
        """
        if "index" in info:
            new_formula = formula.replace("$i$", str(info["index"]))
            return new_formula
        return formula
