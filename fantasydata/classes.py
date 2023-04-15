from dataclasses import dataclass
import pandas as pd
class Player:
    
    _id:int
    _name:str
    _position:str    
    _current_value:int

    chance_of_playing:float
    current_team_id:int
    current_team_name:str
    squad_adjusted_value:int
    
    history:pd.DataFrame
    predicted_points:list[float]

    def __init__(self, id:int, name:str, position:str, team_id:int, team_name:str, current_value:int) -> None:
        if id < 1:
            raise ValueError(f"Player id is non-poisitive: {id}")
        if position not in ["fwd","mid","def","gkp"]:
            raise ValueError(f"Player position is not valid: {position}")  

        self._id = id
        self._name = name
        self._position = position
        self._current_value = current_value
        self.squad_adjusted_value = current_value
        self.current_team_id = team_id
        self.current_team_name = team_name
        self.chance_of_playing = 1.0
        self.history = None
        self.predicted_points = []

    @property
    def id(self) -> int:
        return self._id
        
    @property
    def name(self) -> str:
        return self._name   

    @property
    def position(self) -> str:
        return self._position             

    @property
    def current_value(self) -> int:
        return self._current_value

    @property
    def current_form(self) -> float:
        if self.history is None or len(self.history["form"]) < 1:
            return 1.0
        return self.history["form"].values[-1]               

    def to_dataframe(self) -> pd.DataFrame:

        if self.history is None:
            df = pd.DataFrame()
            df["player_id"] = [self.id]
            df["name"] = [self.name]
            df["position"] = [self.position]
            df["current_team_id"] = [self.current_team_id]
            df["current_team_name"] = [self.current_team_name]
            df["predicted_points"] = [self.predicted_points]
            df["current_value"] = [self.current_value]
            df["squad_adjusted_value"] = [self.squad_adjusted_value]
            df["chance_of_playing"] = [self.chance_of_playing]

        else:
            df = pd.DataFrame(self.history)
            df["player_id"] = self.id
            df["name"] = self.name
            df["position"] = self.position
            df["current_team_id"] = self.current_team_id
            df["current_team_name"] = self.current_team_name
            df["predicted_points"] = [self.predicted_points for i in range(len(df))]
            df["current_value"] = self.current_value
            df["squad_adjusted_value"] = self.squad_adjusted_value
            df["chance_of_playing"] = self.chance_of_playing

        return df

    def __str__(self) -> str:
        return f"Player {self.id}, {self.name}, {self.position}, {self.current_team_name}\n"     
class Team:
    
    _id:int
    _name:str
    _code:int
    current_player_ids:list[int]
    history:pd.DataFrame
    initial_elo:float

    def __init__(self, id:int, name:str, code:int) -> None:
        if id < 1:
            raise ValueError(f"Team id is non-poisitive: {id}")

        self._id = id
        self._name = name
        self._code = code
        self.current_player_ids = []
        self.history = None
        self.initial_elo = 1000.0

    @property
    def id(self) -> int:
        return self._id
    
    @property
    def code(self) -> int:
        return self._code

    @property
    def name(self) -> str:
        return self._name 

    @property
    def current_elo(self) -> float:
        if self.history is None or len(self.history["elo_after_match"])<1:
            return self.initial_elo                       
        return self.history["elo_after_match"].values[-1]   

    @property
    def current_form(self) -> float:
        if self.history is None or len(self.history["form"]) < 1:
            return 0.5            
        return self.history["form"].values[-1]                 

    def to_dataframe(self) -> pd.DataFrame:

        if self.history is None:
            df = pd.DataFrame()
            df["team_id"] = [self.id]
            df["name"] = [self.name]
            df["team_code"] = [self.code]
            df["current_player_ids"] = [self.current_player_ids]
        else:
            df = pd.DataFrame(self.history)
            df["team_id"] = self.id
            df["name"] = self.name
            df["team_code"] = self.code
            df["current_player_ids"] = [self.current_player_ids for i in range(len(df))]
            
        return df

    def __str__(self) -> str:
        return f"Team {self.id}, {self.name}, {len(self.current_player_ids)} current players\n"        


    def add_current_player(self, player:Player) -> None:

        if player.id in self.current_player_ids:
            print("player in team already")
            return
        
        self.current_player_ids.append(player.id)

class Squad:
    
    _id:int
    _name:str    
    history:pd.DataFrame

    def __init__(self, id:int, name:str, history:pd.DataFrame=None) -> None:
        if id < 1:
            raise ValueError(f"Squad id is non-poisitive: {id}")

        self._id = id
        self._name = name
        self.history = history

    @property
    def id(self) -> int:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def current_bank(self) -> int:
        if self.history is None:
            return 1000        
        return self.history["bank"].values[-1]

    @property
    def current_free_transfers(self) -> int:
        if self.history is None:
            return 2        
        return self.history["n_free_transfers"].values[-1]

    @property
    def current_players(self) -> list[int]:
        if self.history is None:
            return []
        return self.history["player_ids"].values[-1]       

    def to_dataframe(self) -> pd.DataFrame:

        if self.history is None:
            df = pd.DataFrame()
            df["squad_id"] = [self.id]
            df["name"] = [self.name]
        else:
            df = pd.DataFrame(self.history)
            df["squad_id"] = self.id
            df["name"] = self.name
        
        return df

    def __str__(self) -> str:

        s = f"Squad {self.id}, {self.name}\n"
        s += f"Bank: {self.current_bank}\n"
        s += f"Player ids: {self.current_players}"
        return s

class Match:

    _id:int
    _round:int
    home_team_name:str
    away_team_name:str
    home_team_id:int
    away_team_id:int    

    home_goals:int
    away_goals:int
    finished:bool
    start_time:pd.Timestamp
    delta_elo:float
    delta_form:float
    expected_home_score:float    
    expected_away_score:float

    def __init__(self, id:int, round:int, home_team_name:str, home_team_id:int, away_team_name:str, away_team_id:int, start_time:pd.Timestamp, home_goals:int = 0, away_goals:int = 0, finished:bool = False) -> None:
        self._id = id
        self._round = round
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.home_team_name = home_team_name
        self.away_team_name = away_team_name        
        self.start_time = start_time
        self.home_goals = home_goals
        self.away_goals = away_goals
        self.finished = finished

        self.delta_elo = 0.0
        self.delta_form = 0.0
        self.expected_home_score = 0.5
        self.expected_away_score = 0.5        

    @property
    def id(self) -> int:
        return self._id    

    @property
    def round(self) -> int:
        return self._round      
        
    def to_dataframe(self):
        df = pd.DataFrame()
        df["id"] = [self.id]
        df["round"] = [self.round]
        df["home_team_id"] = [self.home_team_id]
        df["away_team_id"] = [self.away_team_id]
        df["home_team_name"] = [self.home_team_name]
        df["away_team_name"] = [self.away_team_name]        
        df["start_time"] = [self.start_time]
        df["finished"] = [self.finished]
        df["home_goals"] = [self.home_goals]
        df["away_goals"] = [self.away_goals]
        df["delta_elo"] = [self.delta_elo]
        df["delta_form"] = [self.delta_form]
        df["expected_home_score"] = [self.expected_home_score]
        df["expected_away_score"] = [self.expected_away_score]

        return df

    def __str__(self) -> str:
        s = f"Round {self.round}, {self.home_team_name} - {self.away_team_name}: "
        if self.finished:
            s += f"{self.home_goals} - {self.away_goals}\n"
        else:
            s += f"starts {self.start_time}\n"
        return s

@dataclass
class PlayerPointPredictor:

    const:float
    player_form_coeff:float
    opponent_form_coeff:float = 0.0
    team_delta_elo_coeff:float = 0.0

    def predict(self, player:Player, team:Team, opponent_team: Team) -> float:

        delta_elo = team.current_elo - opponent_team.current_elo
        opponent_form = opponent_team.current_form
        player_form = player.current_form

        return self.const + self.player_form_coeff*player_form + self.opponent_form_coeff*opponent_form + self.team_delta_elo_coeff*delta_elo
