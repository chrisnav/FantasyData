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
    
    #The two first matches played
    m0 = ut.get_match_from_id(matches,matches_played[0])
    m1 = ut.get_match_from_id(matches,matches_played[1])

    #One of the teams should appear in both the first and second match
    if m0.home_team_id in [m1.home_team_id, m1.away_team_id]:
        team = m0.home_team_id
    elif m0.away_team_id in [m1.home_team_id, m1.away_team_id]:
        team = m0.away_team_id
    else:
        print("Unable to match first team, using initial home team")
        team = m0.home_team_id
    
    prev_teams = [team, team]
    n_matches = len(matches_played)

    for i in range(2,n_matches):

        m = ut.get_match_from_id(matches,matches_played[i])

        home = m.home_team_id
        away = m.away_team_id

        #The team the player played for in the previous match is also found in this match
        if team in [home,away]:
            prev_teams.append(team)
        #The player must have changed teams this round!
        elif i != n_matches-1:
            
            #Look at the teams that played in the next match
            m_next = ut.get_match_from_id(matches,matches_played[i+1])

            if m.home_team_id in [m_next.home_team_id, m_next.away_team_id]:
                team = m.home_team_id
            elif m.away_team_id in [m_next.home_team_id, m_next.away_team_id]:
                team = m.away_team_id
            else:
                raise RuntimeError("Unable to match first team")     

            prev_teams.append(team)
        #The player changed team in the last round played, check that the current_team_id played in the match
        elif p.current_team_id in [home,away]:
            team = p.current_team_id
            prev_teams.append(team)
        else:
            raise RuntimeError(f"Unable to find previous team: {team}\n {m}")
    
    #Add the list of previous team ids to the player history
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
   
def add_result_and_form_to_team(t:Team, matches:list[Match]) -> None:

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

        form.append(calc_team_form(results))

    
    if t.history is None:
        t.history = pd.DataFrame()
    
    t.history["rounds"] = rounds
    t.history["match_id"] = match_id
    t.history["results"] = results
    t.history["form"] = form

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

    for m in matches:
        
        if not m.finished:
            continue

        home_team = ut.get_team_from_id(teams, m.home_team_id)
        away_team = ut.get_team_from_id(teams, m.away_team_id)

        home_score = 0.5

        if m.home_goals > m.away_goals:
            home_score = 1.0
        elif m.home_goals < m.away_goals:
            home_score = 0.0

        away_score = 1.0 - home_score

        home_expected_score = calc_expected_elo_score(elo[home_team.id][-1],elo[away_team.id][-1])
        away_expected_score = 1.0 - home_expected_score

        expected_result[home_team.id].append(home_expected_score)
        expected_result[away_team.id].append(away_expected_score)
    
        new_home_elo = calc_team_elo_update(elo[home_team.id][-1],elo[away_team.id][-1],home_score)
        new_away_elo = calc_team_elo_update(elo[away_team.id][-1],elo[home_team.id][-1],away_score)

        elo[home_team.id].append(new_home_elo)
        elo[away_team.id].append(new_away_elo)

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

#url_base = "https://fantasy.eliteserien.no/api/"    
#squad_id = 9438 
url_base = "https://fantasy.premierleague.com/api/"
squad_id = 2796953

#players,teams,matches,squad = gd.retreive_raw_data(url_base,squad_id)
#gd.save_all_data(players,teams,matches,squad)

players,teams,matches,squad = gd.read_data_from_csv()
 
for p in players:
    add_previous_team_to_player(p,matches)
    add_rounds_to_player(p,matches)

for t in teams:
    add_result_and_form_to_team(t,matches)

add_team_elo(teams,matches)

for t in teams:
    add_sum_points_to_team(t,players)

for p in players:
    add_player_form_score(p,teams,matches)


gd.save_all_data(players,teams,matches,squad,suffix="calc")