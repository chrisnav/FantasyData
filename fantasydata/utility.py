from typing import Union
from classes import Player, Team, Squad, Match
import pandas as pd

def string_to_int_list(s:str) -> list[int]:

    s = s.replace("[","")
    s = s.replace("]","")
    s = s.split(",")
    return [int(val) for val in s]

def get_team_from_id(teams:list[Team], team_id:int) -> Team:
    
    for t in teams:
        if t.id == team_id:
            return t

    raise ValueError(f"Team with id {team_id} not found in list")

def get_team_from_code(teams:list[Team], team_code:int) -> Team:
    
    for t in teams:
        if t.code == team_code:
            return t
            
    raise ValueError(f"Team with code {team_code} not found in list") 

def get_team_from_name(teams:list[Team], name:str) -> Team:
    
    for t in teams:
        if name in t.name:
            return t
            
    raise ValueError(f"Team with name {name} not found in list") 

def get_player_from_id(players:list[Player], player_id:int) -> Player:
    
    for p in players:
        if p.id == player_id:
            return p

    raise ValueError(f"Player with id {player_id} not found in list")

def get_player_from_name(players:list[Player], name:str) -> Player:
    
    for p in players:
        if p.name == name:
            return p
            
    raise ValueError(f"Player with name {name} not found in list")        

def get_match_from_id(matches:list[Match], id:int) -> Match:

    for m in matches:
        if m.id == id:
            return m
            
    raise ValueError(f"Match with id {id} not found in list") 

def get_next_round(matches:list[Match]) -> int:

    for m in matches:
        if not m.finished:
            return m.round
    return -1

def list_to_dataframe(object_list:list[Union[Player,Team,Match]]) -> pd.DataFrame:
    
    df = pd.DataFrame()
    for o in object_list:
        o_as_df = o.to_dataframe()
        df = df.append(o_as_df)

    df.reset_index(drop=True, inplace=True)

    return df

def dataframe_to_players(df:pd.DataFrame) -> list[Player]:

    players = []
    player_ids = set(df["player_id"])

    for player_id in player_ids:
        player_df = df[df["player_id"] == player_id]

        name = player_df["name"].values[-1]
        position = player_df["position"].values[-1]
        current_team_id = player_df["current_team_id"].values[-1]
        current_team_name = player_df["current_team_name"].values[-1]

        p = Player(player_id,name,position,current_team_id,current_team_name)
        history = player_df.drop(columns=["player_id","name","position","current_team_id","current_team_name"])
        history.reset_index(drop=True, inplace=True)

        for attr in history.keys():
            if attr in ["ict_index","threat","creativity","influence"]:
                continue
            else:
                try:
                    history[attr] = history[attr].astype(int)
                except ValueError:
                    pass

        if len(history.keys()) != 0:
            p.history = history

        players.append(p)

    return players


def dataframe_to_teams(df:pd.DataFrame) -> list[Team]:

    teams = []
    team_ids = set(df["team_id"])

    for team_id in team_ids:
        team_df = df[df["team_id"] == team_id]

        name = team_df["name"].values[-1]
        team_code = team_df["team_code"].values[-1]
        current_player_ids = team_df["current_player_ids"].values[-1]

        #The list of ids is read as a string and must be converted back to a list of ints
        current_player_ids = string_to_int_list(current_player_ids)

        t = Team(team_id,name,team_code)
        t.current_player_ids = current_player_ids

        history = team_df.drop(columns=["team_id","name","team_code","current_player_ids"])
        history.reset_index(drop=True, inplace=True)

        if len(history.keys()) != 0:
            t.history = history

        teams.append(t)

    return teams    
    
def dataframe_to_matches(df:pd.DataFrame) -> list[Match]:

    matches = []
    match_ids = set(df["id"])

    for match_id in match_ids:
        match_df = df[df["id"] == match_id]

        round = match_df["round"].values[-1]
        home_team_name = match_df["home_team_name"].values[-1]
        away_team_name = match_df["away_team_name"].values[-1]
        home_team_id = match_df["home_team_id"].values[-1]
        away_team_id = match_df["away_team_id"].values[-1]
        start_time = pd.Timestamp(match_df["start_time"].values[-1])
        home_goals = match_df["home_goals"].values[-1]
        away_goals = match_df["away_goals"].values[-1]
        finished = bool(match_df["finished"].values[-1])
        
        if finished:
            m = Match(match_id,round,home_team_name,home_team_id,away_team_name,away_team_id,start_time,finished=True,home_goals=home_goals,away_goals=away_goals)
        else:
            m = Match(match_id,round,home_team_name,home_team_id,away_team_name,away_team_id,start_time)

        try:
            m.delta_elo = match_df["delta_elo"].values[-1]
            m.delta_form = match_df["delta_form"].values[-1]
            m.expected_home_score = match_df["expected_home_score"].values[-1]
            m.expected_away_score = match_df["expected_away_score"].values[-1]
        except KeyError:
            pass

        matches.append(m)

    matches = sorted(matches, key=lambda x: x.start_time)

    return matches    

def dataframe_to_squad(df:pd.DataFrame) -> Squad:

    squad_id = df["squad_id"].values[-1]
    name = df["name"].values[-1]
    history = df.drop(columns=["squad_id","name"])
    history["player_ids"] = history["player_ids"].apply(string_to_int_list)
    history.reset_index(drop=True, inplace=True)
    
    s = Squad(squad_id,name,history=history)

    return s        

def save_all_data(directory:str, players:list[Player], teams:list[Team], matches:list[Match], squad:Squad, suffix:str = "raw") -> None:

    player_df = list_to_dataframe(players)
    player_df.to_csv(f"{directory}players_{suffix}.csv",sep=";",index=False)

    team_df = list_to_dataframe(teams)
    team_df.to_csv(f"{directory}teams_{suffix}.csv",sep=";",index=False)

    match_df = list_to_dataframe(matches)
    match_df.to_csv(f"{directory}matches_{suffix}.csv",sep=";",index=False)

    squad_df = squad.to_dataframe()
    squad_df.to_csv(f"{directory}squad_{suffix}.csv",sep=";",index=False)

def read_data_from_csv(directory:str, suffix:str = "raw") -> tuple[list[Player],list[Team],list[Match],Squad]:

    player_df = pd.read_csv(f"{directory}players_{suffix}.csv",sep=";")
    players = dataframe_to_players(player_df)

    team_df = pd.read_csv(f"{directory}teams_{suffix}.csv",sep=";")
    teams = dataframe_to_teams(team_df)  

    match_df = pd.read_csv(f"{directory}matches_{suffix}.csv",sep=";")
    matches = dataframe_to_matches(match_df)    

    squad_df = pd.read_csv(f"{directory}squad_{suffix}.csv",sep=";")
    squad = dataframe_to_squad(squad_df)        

    return players,teams,matches,squad    