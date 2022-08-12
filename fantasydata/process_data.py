from classes import Player, Match, Squad, Team
import utility as ut
import get_data as gd
import numpy as np

def add_previous_team_to_player(p:Player, matches:list[Match]) -> None:
    
    #The previous match ids that the player participated in
    matches_played = p.history["fixture"].values
    
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
    
    rounds = []
    for m_id in matches_played:
        m = ut.get_match_from_id(matches,m_id)
        rounds.append(m.round)

    p.history["round"] = rounds
   

#url_base = "https://fantasy.eliteserien.no/api/"    
#players,teams,matches,squad = gd.retreive_raw_data(url_base)
#gd.save_all_data(players,teams,matches,squad)

players,teams,matches,squad = gd.read_data_from_csv()

for p in players:
    add_previous_team_to_player(p,matches)
    add_rounds_to_player(p,matches)








