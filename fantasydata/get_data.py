from concurrent.futures import ThreadPoolExecutor
from typing import Any
import pandas as pd
import requests as req
import json
from fantasydata.classes import Player, Team, Squad, Match
import fantasydata.utility as ut
import time
import numpy as np

def get_data(url:str) -> dict[str,Any]:
        
    r = req.get(url)
    if r.status_code != 200:
        raise RuntimeWarning(f"Error retreiving data from {url}, statuscode: {r.status_code}")
    
    res = json.loads(r.content)

    return res

def retreive_players_and_teams(url_base:str) -> tuple[list[Player],list[Team]]:
   
    url = f"{url_base}bootstrap-static/"    
    res = get_data(url)

    #fixture_data = res["events"]
    
    team_data = res["teams"]
    teams = []
    for t in team_data:
        if t["unavailable"]:
            continue

        name = t["name"]
        _id = t["id"]
        code = t["code"]

        t = Team(_id,name,code)
        teams.append(t)

    player_data = res["elements"]
    players = []    
    for p in player_data:

        #if p["id"] == 237:
        #    for k,v in p.items():
        #        print(k,v)
        #    a=b

        #element_type: 1 = gkp, 2 = def, 3 = mid, 4 = fwd
        p_type = p["element_type"]
        
        if p_type == 1:
            pos = "gkp"
        elif p_type == 2:
            pos = "def"
        elif p_type == 3:
            pos = "mid"
        elif p_type == 4:
            pos = "fwd"
        else:
            raise ValueError(f"Unknown position {p_type} for player {p}")
        
        player_id = p["id"]
        #real_name = p["first_name"]+" "+p["second_name"]
        name = p["web_name"]
        team = ut.get_team_from_code(teams,p["team_code"])
        #value = p["now_cost"]
        chance_of_playing = p["chance_of_playing_next_round"]

        current_value = p["now_cost"]
        #tot_points = p["total_points"]
        #form = p["form"]
        #minutes = p["minutes"]
        #assists = p["assists"]
        #clean_sheets = p["clean_sheets"]
        #goals_conceded = p["goals_conceded"]
        #points_last_round = p["event_points"]
        #goals_scored = p["goals_scored"]

        player = Player(player_id,name,pos,team.id,team.name,current_value)
        team.add_current_player(player)

        if chance_of_playing is not None:
            player.chance_of_playing = chance_of_playing*0.01

        players.append(player)

    return players,teams
 
def retreive_squad(url_base:str, squad_id:int) -> Squad:

    history = pd.DataFrame()

    for game_week in range(1,100):

        url = f"{url_base}entry/{squad_id}/event/{game_week}/picks/"
        try:
            res = get_data(url)
        except RuntimeWarning:
            break
        
        df = pd.DataFrame({k:[v] for k,v in res["entry_history"].items()})
        df.rename(columns={"event":"round"},inplace=True)

        n_transfers = df["event_transfers"].values[0]
        if n_transfers == 0 and res["active_chip"] != "wildcard":
            n_free_transfers = 2
        else:
            n_free_transfers = 1
        df["n_free_transfers"] = [n_free_transfers]

        chosen_player_ids = [pick["element"] for pick in res["picks"]]

        if len(chosen_player_ids) != 15:
            raise RuntimeError(f"All existing players not found, {len(chosen_player_ids)} players in list!")
        
        df["player_ids"] = [chosen_player_ids]
        
        history = pd.concat([history,df])
        time.sleep(0.1)

    history.reset_index(drop=True, inplace=True)

    s = Squad(squad_id,"my_squad",history=history)        
    return s

def retreive_player_history(url_base:str, player:Player, wait_time:float) -> None:            

    url = f"{url_base}element-summary/{player.id}/"
    res = get_data(url)

    #Keys:
    #'fixtures' is upcoming matches
    #'history' is player data from previous rounds
    #'history_past' aggregated season history from the past, not very useful

    history = res["history"]

    #fixture_id = [h["fixture"] for h in history]
    #points = [h["total_points"] for h in history]
    #minutes = [h["minutes"] for h in history]
    #value = [h["value"] for h in history]

    if len(history) != 0:
        df = pd.DataFrame(history)
        df = df.drop(columns=["element"])
        player.history = df
    
    time.sleep(wait_time)

def add_player_history(url_base:str, players:list[Player],wait_time:float) -> None:

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=6) as threadPool:
        for p in players:        
            threadPool.submit(retreive_player_history,url_base,p,wait_time)

    for p in players:
        if p.history is None:
            print("trying again for ",p)
            retreive_player_history(url_base,p,wait_time)
            if p.history is None:
                print(f"Unable to get history for player {p}\n")

    t1 = time.time()

    print(f"Time used to get player history: {t1-t0}")

def retreive_matches(url_base:str, teams:list[Team]) -> list[Match]:
    
    url = f"{url_base}fixtures/"
    res = get_data(url)

    matches = []
    for match in res:

        id = int(match["id"])

        try:
            round = int(match["event"])
        except TypeError:
            round = np.nan

        try:
            home_goals = int(match["team_h_score"])
            away_goals = int(match["team_a_score"])
        except TypeError:
            home_goals = np.nan
            away_goals = np.nan            

        start_time = pd.Timestamp(match["kickoff_time"])
        home = ut.get_team_from_id(teams, match["team_h"])
        away = ut.get_team_from_id(teams, match["team_a"])        
        finished = bool(match["finished"])

        if finished:
            m = Match(id,round,home.name,home.id,away.name,away.id,start_time,home_goals=home_goals,away_goals=away_goals,finished=True)
        else:
            m = Match(id,round,home.name,home.id,away.name,away.id,start_time)
        
        matches.append(m)

    matches = sorted(matches, key=lambda x: x.start_time)

    return matches
 
def retreive_raw_common_data(url_base:str, wait_time:float = 0.2) -> tuple[list[Player],list[Team],list[Match]]:

    players,teams = retreive_players_and_teams(url_base) 
    add_player_history(url_base,players,wait_time)

    matches = retreive_matches(url_base,teams)

    return players,teams,matches

