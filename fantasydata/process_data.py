from math import floor
from classes import Player, Match, Squad, Team
import utility as ut
import get_data as gd
import pandas as pd
import numpy as np
import sys

def calc_expected_elo_score(elo:float, opponent_elo:float) -> float:
    return 1.0/(1.0+10**((opponent_elo-elo)/400.0))

def calc_team_elo_update(start_elo:float, opponent_elo:float, score:float) -> float:

    expected_score = calc_expected_elo_score(start_elo,opponent_elo)
    K = 30.0
    return start_elo + K*(score - expected_score)

def calc_norm_form(past_scores:list[float]) -> float:

    N = len(past_scores)
    form = 0.0
    coeff = 0.60 
    for i,score in enumerate(past_scores[::-1]):
        form += score * (1.0-coeff) * coeff**i
    return form/(1-coeff**N)

def add_previous_team_to_player(p:Player, matches:list[Match]) -> None:
    
    #The previous match ids that the player participated in
    matches_played = p.history["fixture"].values
    
    if np.isnan(matches_played).any():
        p.history["team_id"] = [np.nan]*len(p.history) 
        return

    #Only played 1 match
    if len(matches_played) == 1:
        p.history["team_id"] = [p.current_team_id]
        return

    opponents = p.history["opponent_team"].values
    prev_teams = []
    for m_id,opp_id in zip(matches_played,opponents):
        m = ut.get_match_from_id(matches,m_id)
        
        if m.home_team_id == opp_id:
            team_id = m.away_team_id
        elif m.away_team_id == opp_id:
            team_id = m.home_team_id
        else:
            raise RuntimeError(f"Unable to find team for {p} in match {m}")
        
        prev_teams.append(team_id)

    p.history["team_id"] = prev_teams

def add_rounds_to_player(p:Player, matches:list[Match]) -> None:
    
    #The previous match ids that the player participated in
    matches_played = p.history["fixture"].values

    if np.isnan(matches_played).any():
        p.history["round"] = [np.nan]*len(p.history)
        return

    rounds = []
    for m_id in matches_played:
        m = ut.get_match_from_id(matches,m_id)
        rounds.append(m.round)

    p.history["round"] = rounds
   
def add_result_and_form_to_team(teams:list[Team], matches:list[Match]) -> None:

    for t in teams:

        team_matches = [m for m in matches if t.id in [m.home_team_id,m.away_team_id] and m.finished]

        rounds = [m.round for m in team_matches]
        match_id = [m.id for m in team_matches]
        results = []
        form = []
        for m in team_matches:

            r = 0.5
            if m.home_goals > m.away_goals:
                if t.id == m.home_team_id:
                    r = 1.0
                else:
                    r = 0.0
            elif m.home_goals < m.away_goals:
                if t.id == m.home_team_id:
                    r = 0.0
                else:
                    r = 1.0

            results.append(r)     

            f = calc_norm_form(results)
            form.append(f)

        
        if t.history is None:
            t.history = pd.DataFrame()
        
        t.history["rounds"] = rounds
        t.history["match_id"] = match_id
        t.history["results"] = results
        t.history["form"] = form

    next_round = ut.get_next_round(matches)
    
    for m in matches:
        
        if not m.finished and m.round != next_round:
            continue

        home = ut.get_team_from_id(teams,m.home_team_id)
        away = ut.get_team_from_id(teams,m.away_team_id)

        home_form = home.history["form"].values
        away_form = away.history["form"].values

        if m.round == next_round:
            m.delta_form = home_form[-1] - away_form[-1]
            continue

        found_match = False
        for i,hf in enumerate(home_form):
            if home.history["match_id"].values[i] == m.id:
                if i == 0:
                    m.delta_form = 0.5
                else:
                    m.delta_form = home_form[i-1]

                found_match = True
                break

        if not found_match:
            print("Did not find match for home team:",m)
            m.delta_form = 0.5

        found_match = False
        for i,af in enumerate(away_form):
            if away.history["match_id"].values[i] == m.id:
                if i == 0:
                    m.delta_form -= 0.5
                else:
                    m.delta_form -= away_form[i-1]  

                found_match = True
                break

        if not found_match:
            print("Did not find match for away team:",m,away)
            m.delta_form -= 0.5            

def add_sum_points_to_team(t:Team, players:list[Player]) -> None:

    participating_players = [p for p in players if t.id in p.history["team_id"].values]

    team_points = [0]*len(t.history)
    n_players = [0]*len(t.history)

    for p in participating_players:
        
        for points,minutes,team_id,match_id in zip(p.history["total_points"],p.history["minutes"],p.history["team_id"],p.history["fixture"]):
            if team_id == t.id:
                try:
                    i = list(t.history["match_id"].values).index(match_id)
                except ValueError:
                    print(t,match_id,p)
                    print(t.history)
                    print(p.history)
                    sys.exit()
                team_points[i] += points
                if minutes > 0:
                    n_players[i] += 1
    
    t.history["team_points"] = team_points
    t.history["n_players"] = n_players

def add_team_elo(teams:list[Team], matches:list[Match], initial_elo:pd.DataFrame) -> None:

    elo = {}
    expected_result = {}
    for t in teams:
        df = initial_elo[initial_elo["team_name"]==t.name]
        elo[t.id] = [df["elo"].values[0]]
        expected_result[t.id] = []

    next_round = ut.get_next_round(matches)
    
    for m in matches:
        
        if not m.finished and m.round != next_round:
            continue

        home_team = ut.get_team_from_id(teams, m.home_team_id)
        away_team = ut.get_team_from_id(teams, m.away_team_id)

        prev_home_elo = elo[home_team.id][-1]
        prev_away_elo = elo[away_team.id][-1]

        home_expected_score = calc_expected_elo_score(prev_home_elo,prev_away_elo)
        away_expected_score = 1.0 - home_expected_score

        m.expected_home_score = home_expected_score
        m.expected_away_score = away_expected_score
        m.delta_elo = prev_home_elo - prev_away_elo

        if m.round == next_round:
            continue

        home_score = 0.5

        if m.home_goals > m.away_goals:
            home_score = 1.0
        elif m.home_goals < m.away_goals:
            home_score = 0.0

        away_score = 1.0 - home_score

        new_home_elo = calc_team_elo_update(prev_home_elo,prev_away_elo,home_score)
        new_away_elo = calc_team_elo_update(prev_away_elo,prev_home_elo,away_score)

        elo[home_team.id].append(new_home_elo)
        elo[away_team.id].append(new_away_elo)
        expected_result[home_team.id].append(home_expected_score)
        expected_result[away_team.id].append(away_expected_score)          

    for t in teams:
        n = len(elo[t.id])
        t.history["elo_before_match"] = elo[t.id][:n-1]
        t.history["elo_after_match"] = elo[t.id][1:]
        t.history["expected_result"] = expected_result[t.id]

def add_player_form(p:Player) -> None:
        form = []
        for i in range(len(p.history)):
            form.append(calc_norm_form(p.history["total_points"][:i+1]))
        p.history["form"] = form

def add_squad_adjusted_player_value(players:list[Player], squad:Squad) -> None:

    current_players = [p for p in players if p.id in squad.current_players]

    for p in current_players:
        
        set_value = False

        for r,player_ids in zip(squad.history["round"][::-1][1:],squad.history["player_ids"][::-1][1:]):
            
            if p.id not in player_ids:
                
                #Try to use the value of the player in the round he was first present
                try:
                    i = list(p.history["round"].values).index(r+1)
                except ValueError:
                    #If the round does not exist, try to use the previous round
                    try:
                        i = list(p.history["round"].values).index(r)   
                    except ValueError:
                        print(f"Unable to find round for player {p}:",r,p.history["round"],p.history["value"])
                        sys.exit()

                #The sale value is the average of the buy value and current value, rounded down
                sale_value = floor(0.5*(p.history['value'].values[i] + p.current_value))
                p.squad_adjusted_value = sale_value
                set_value = True
                break
        
        if not set_value:
            print(f"Player {p} has always been in the squad, using first recorded value as buy cost")
            
            sale_value = floor(0.5*(p.history['value'].values[0] + p.current_value))
            p.squad_adjusted_value = sale_value


def add_calculated_attributes(players:list[Player], teams:list[Team], matches:list[Match], squad:Squad, initial_elo:pd.DataFrame) -> None:
   
    for p in players:
        add_previous_team_to_player(p,matches)
        add_rounds_to_player(p,matches)
        add_player_form(p)

    add_result_and_form_to_team(teams,matches)
    add_team_elo(teams,matches,initial_elo)

    for t in teams:
        add_sum_points_to_team(t,players)

    add_squad_adjusted_player_value(players,squad)


eliteserien = True

if eliteserien:
    url_base = "https://fantasy.eliteserien.no/api/"    
    squad_id = 9438 
    directory = "eliteserien//2022//"
else:
    url_base = "https://fantasy.premierleague.com/api/"
    squad_id = 2796953
    directory = "premier_league//2022_2023//"

round = 19
data_dir = directory+f"post_round_{round-1}//"

initial_elo = pd.read_csv(directory+"initial_elo.csv",sep=";")
try:
    players,teams,matches,squad = ut.read_data_from_csv(data_dir,suffix="raw")   
except FileNotFoundError:
    print("Raw data files not found, retreiving data...")
    players,teams,matches,squad = gd.retreive_raw_data(url_base,squad_id)
    ut.save_all_data(data_dir,players,teams,matches,squad,suffix="raw")

#Filter out new players that have been transferred in from outside the league
players = [p for p in players if p.history is not None]

add_calculated_attributes(players,teams,matches,squad,initial_elo)

ut.save_all_data(data_dir,players,teams,matches,squad,suffix="calc")