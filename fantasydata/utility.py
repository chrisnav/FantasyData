from re import S
from typing import Union
from classes import Player, Team, Squad, Match
import pandas as pd

def string_to_int_list(s:str) -> list[int]:

    s = s.replace("[","")
    s = s.replace("]","")
    s = s.split(",")
    return [int(val) for val in s]

def convert_df_to_int(x):
    try:
        return x.astype(int)
    except:
        return x

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
        history = history.apply(convert_df_to_int)

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
        history = history.apply(convert_df_to_int)

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

        matches.append(m)

    return matches    

def dataframe_to_squad(df:pd.DataFrame) -> Squad:

    squad_id = df["squad_id"].values[-1]
    name = df["name"].values[-1]
    history = df.drop(columns=["squad_id","name"])
    history["player_ids"] = history["player_ids"].apply(string_to_int_list)
    history.reset_index(drop=True, inplace=True)
    
    s = Squad(squad_id,name,history=history)

    return s        