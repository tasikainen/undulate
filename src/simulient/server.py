# for now just creates some answers
import random
import math


class Server:
    """Emulates a callable server
    
    Attributes
    ----------
    news: []{}
        The current list of news
    values: {}
        The dictionary containing values for the importance of topics
    optimal_magnitude: float
        The assumed magnitude people like reading

    Methods
    -------
    getResponse(action, buy)
        gives response based on the action and optional variable for buying
    get_news(index)
        Used when specific news is selected.
        Gives the news back and updates values and optimal_magnitude
    play_level(skill, level, difficulty)
        gives required score and the player's score
    """

    def __init__(self):
        self.news, self.number_of = self.__generate_news()
        self.values = {
            "sports": 0,
            "culture": 0,
            "financial": 0
        }
        self.optimal_magnitude = 10

    def __generate_news(self):
        """Creates a list of new news
        
        Creates 2-20 sport news, 2-20 culture news and 2-20 financial news
        with random magnitude float between 0 and 10

        Returns
        -------
        list
            a list of dictionaries that are news
        dictionary
            containing the number of each news
        """

        number_of_sports = random.randint(2, 20)
        number_of_culture = random.randint(2, 20)
        number_of_financial = random.randint(2, 20)
        news = []

        for i in range(number_of_sports):
            new = {
                "topic": "sports",
                "magnitude": random.uniform(0, 10)
            }
            news.append(new)

        for i in range(number_of_culture):
            new = {
                "topic": "culture",
                "magnitude": random.uniform(0, 10)
            }
            news.append(new)

        for i in range(number_of_financial):
            new = {
                "topic": "financial",
                "magnitude": random.uniform(0, 10)
            }
            news.append(new)

        random.shuffle(news)
        return news, {"sports": number_of_sports, "culture": number_of_culture, "financial": number_of_financial}

    def getResponse(self, action, buy=None):
        """Gives response based on action

        Current supprted actions are action1, action2, sleep, eat and
        get_all_news.

        Parameters
        ----------
        action: str
            the action that was done
        buy: str
            idnicates what is bought when buying wares

        Returns
        -------
        Response
            a Response class object
        """

        # og_config 
        if action == "action1":
            json = {
                "info1": "nice",
                "likes": 20
            }
            status_code = 200
            response = Response(status_code, json)
            return response
        if action == "action2":
            json = {
                "info1": "not nice",
                "price": 62
            }

        # eat_sleep_config
        if action == "sleep":
            value = random.uniform(1, 3)
            json = {
                "sleeping_conditions": value
            }
        if action == "eat":
            value = random.uniform(1, 3)
            json = {
                "amount_of_food": value
            }
        
        #news_config
        if action == "get_all_news":
            self.__rearrange_news()
            json = {
                "news": self.news
            }
        
        #game_config
        if action == "buy":
            buy_list = ["skill", "items"]
            json = {
                "action": "buy",
                "buy_list": buy_list
            }        
        if action == "go_menu":
            json = {
                "action": "go_menu"
            }
        if action == "take_break":
            new_frustration = random.uniform(0.01, 1.5)
            json = {
                "new_frustration": new_frustration
            }
        if action == "go_play":
            json = {
                "action": "go_play"
            }
        if action == "buy_wares":
            json = {
                "bought": buy,
                "cost": 1
            }

        status_code = 200
        try:
            response = Response(status_code, json)
        except:
            response = Response(
                400, {"error": "error happened because of your horrible request"})
        return response

    def get_news(self, index):
        """User selects specific news
        
        Used when a user selects specific news and the sever will return
        the selected news while adjusting values and optimal_magnitude to
        try to learn what the users like.

        Parameters
        ----------
        index: int
            the index of the news in the list of news

        Returns
        -------
        Response
            a Response object containing the chosen news
        """

        chosen_news = self.news[index]
        status_code = 200
        news_size = len(self.news) * 3
        json = {"chosen_news": chosen_news}
        self.values[chosen_news["topic"]] += (1 + index)/self.number_of[chosen_news["topic"]]
        #self.optimal_magnitude = ((news_size-index-1)/news_size)*self.optimal_magnitude + ((index+1)/news_size)*chosen_news["magnitude"]
        response = Response(status_code, json)
        return response

    def __rearrange_news(self):
        """Rearranges the news list. 
        
        The arrangement is based on the news calculated value and
        orders them in descending order so that the most valuable
        news is at the start in index 0.
        """

        for n in self.news:
            n["value"] = self.values[n["topic"]] - abs(self.optimal_magnitude - n["magnitude"])

        self.news = sorted(self.news, key = lambda i: i["value"], reverse=True)

    def play_level(self, skill, items, level, difficulty):
        """Gives required score and the players score

        Calculates required score based on the level and
        the difficulty. Also calculates the players score based on skill and items.

        Parameters
        ----------
        skill: int
            the player's skill
        items: int
            the players items (just a numerical value)
        level: int
            the current level in the game
        difficulty: float
            the difficulty used by the player
        """

        status_code = 200
        required_score = level * difficulty
        score = (skill + items) * random.uniform(0.5, 2)
        json = {
            "required_score": required_score,
            "score": score
        }

        return Response(status_code, json)

class Response:
    """Object for server responses

    Attributes
    ----------
    status_code: int
        HTTP status code
    json_data: {}
        dictionary containing the information of the response
    headers: {}
        dict for headers to imitate http
    
    Methods
    -------
    json():
        returns the json_data
    """

    def __init__(self, status, json):
        """
        Parameters
        ----------
        status: int
            HTTP status code
        json_data: {}
            dictionary containing the information of the response
        """
        self.status_code = status
        self.json_data = json
        self.headers = {}
    
    def json(self):
        return self.json_data
