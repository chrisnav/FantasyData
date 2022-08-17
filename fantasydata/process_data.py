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

def calc_team_form(past_scores:list[float]) -> float:

    N = len(past_scores)
    form = 0.0
    for i,perf in enumerate(past_scores):
        form += perf / 2**(N-i-1)

    max_form = 2.0 - 1.0/2**(N-1)
    
    return form/max_form

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

            f = calc_team_form(results)
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



def add_team_elo(teams:list[Team], matches:list[Match]) -> None:

    elo = {t.id:[1000.0] for t in teams}
    expected_result = {t.id:[] for t in teams}

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

def add_player_form_score(p:Player, teams:list[Team], matches:list[Match]):

    t = ut.get_team_from_id(teams,p.current_team_id)

    team_form_score = -1.59 + 3.19*t.current_form

    upcoming_matches = [m for m in matches if not m.finished and t.id in [m.home_team_id,m.away_team_id]]
    remaining_rounds = set(m.round for m in upcoming_matches)

    predicted_points = []
    for next_round in remaining_rounds:

        round_matches = [m for m in upcoming_matches if m.round==next_round]

        round_points = 0.0
        for m in round_matches:

            if t.id == m.home_team_id:
                opponent = ut.get_team_from_id(teams,m.away_team_id)
            else:
                opponent = ut.get_team_from_id(teams,m.home_team_id)

            ex_score = calc_expected_elo_score(t.current_elo,opponent.current_elo)
            team_point_boost = ex_score - 0.5

            round_points += 0.9*p.current_form + 0.05*team_form_score + 0.05*team_point_boost

        predicted_points.append(round_points)

    p.predicted_points = predicted_points


def add_calculated_attributes(players:list[Player], teams:list[Team], matches:list[Match], squad:Squad, save:bool = False):
   
    for p in players:
        add_previous_team_to_player(p,matches)
        add_rounds_to_player(p,matches)

    add_result_and_form_to_team(teams,matches)
    add_team_elo(teams,matches)

    for t in teams:
        add_sum_points_to_team(t,players)

    for p in players:
        add_player_form_score(p,teams,matches)

    if save:
        gd.save_all_data(players,teams,matches,squad,suffix="calc")

#url_base = "https://fantasy.eliteserien.no/api/"    
#squad_id = 9438 
url_base = "https://fantasy.premierleague.com/api/"
squad_id = 2796953

#players,teams,matches,squad = gd.retreive_raw_data(url_base,squad_id)
#gd.save_all_data(players,teams,matches,squad,suffix="raw")

players,teams,matches,squad = gd.read_data_from_csv(suffix="calc")   


#players = [p for p in players if p.history is not None]

#add_calculated_attributes(players,teams,matches,squad)
#gd.save_all_data(players,teams,matches,squad,suffix="calc")

#players = sorted(players,key=lambda x: x.current_form/x.current_value,reverse=True)
#players = sorted(players,key=lambda x: x.calc_norm_form()/x.current_value,reverse=True)

#players = sorted(players,key=lambda x: x.calc_norm_form()/x.current_value,reverse=True)
#
#i = 0
#for p in players:
#    if i == 5:
#        break
#    if len(p.history) < 3:
#        continue
#    print(p,p.calc_norm_form(),p.current_value)#,p.calc_norm_form()/p.current_value)
#    i += 1

next_round = [m for m in matches if m.round == ut.get_next_round(matches)]
next_round = sorted(next_round,key=lambda m: abs(m.delta_elo), reverse=True)
for m in next_round:
    print(m,m.delta_elo,m.delta_form)

#next_round = sorted(next_round,key=lambda m: abs(m.delta_form), reverse=True)
#for m in next_round:
#    print(m,m.delta_elo,m.delta_form)    

#print(matches[1])