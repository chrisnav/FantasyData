from fileinput import filename
from fantasydata.classes import Player, Match, Squad, Team, PlayerPointPredictor
import fantasydata.utility as ut
import numpy as np
import statsmodels.api as sm

def linear_model_to_csv(directory:str, model:PlayerPointPredictor) -> None:

    if model.opponent_form_coeff == 0.0 and model.team_delta_elo_coeff == 0.0:
        filename = "simple_model.csv"
    else:
        filename = "model.csv"

    with open(directory+filename,"w") as f:
        f.write("constant;player_form;opponent_team_form;team_delta_elo\n")
        f.write(f"{model.const};{model.player_form_coeff};{model.opponent_form_coeff};{model.team_delta_elo_coeff}")

def read_linear_model(directory:str, filename:str) -> PlayerPointPredictor:

    with open(directory+filename,"r") as f:
        lines = [l for l in f]
    
    l = lines[1].strip()
    l = l.split(";")
    const = float(l[0])
    player_form = float(l[1])
    opponent_team_form = float(l[2])
    team_delta_elo = float(l[3])

    return PlayerPointPredictor(const,player_form,opponent_team_form,team_delta_elo)

def estimate_linear_model(players:list[Player], teams:list[Team]) -> tuple[PlayerPointPredictor,PlayerPointPredictor]:
    
    player_points = []
    player_form = []
    team_delta_elo = []
    opponent_form = []

    players = sorted(players,key=lambda p: np.sum(p.history["total_points"].values),reverse=True)
    players = [p for p in players if len(p.history)>=3 and np.mean(p.history["total_points"].values) >= 2]
    print(f"{len(players)} best players used in fit")

    for p in players:

        fixtures = p.history["fixture"].values
        opponent_id = p.history["opponent_team"].values
        team_id = p.history["team_id"].values
        points = p.history["total_points"].values
        form = p.history["form"].values
        minutes = p.history["minutes"].values

        for i in range(3,len(p.history)):
            
            #if the player didn't play the round, we skip it (assume we can know if the player is unavailable)
            if minutes[i] == 0:                
                continue
            
            #Points this round
            player_points.append(points[i])
            #Player form before the round
            player_form.append(form[i-1])

            #The team the player played for
            team = ut.get_team_from_id(teams,team_id[i])            
            #The index of the match in question in the team history df
            j = team.history.index[team.history['match_id']==fixtures[i]].tolist()[0]
            #The team elo before the match
            de = team.history["elo_before_match"].values[j]

            #Opponent team
            opponent = ut.get_team_from_id(teams,opponent_id[i])
            j = opponent.history.index[opponent.history['match_id']==fixtures[i]].tolist()[0]
            #Opponent form and elo before the match
            opponent_form.append(opponent.history["form"].values[j-1])
            de -= opponent.history["elo_before_match"].values[j]
            team_delta_elo.append(de)

    #Y is the actual outcome
    Y = np.array(player_points).reshape(-1, 1) 

    #We use the player form, opponent team form, and team elo difference to predict the player points
    predictors = []
    predictors.append(player_form)
    predictors.append(opponent_form)
    predictors.append(team_delta_elo)
    X = np.array(predictors).T

    #Add constant intercept
    X2 = sm.add_constant(X)
    #Fit linear regression model
    est = sm.OLS(Y, X2)
    est2 = est.fit()
    #Predict given the input 
    Y_pred = est2.predict(X2)

    #Print model summary and rms values
    print(est2.summary())
    rms = np.sqrt(np.mean((Y_pred-Y)**2))
    simple_rms1 = np.sqrt(np.mean((np.array(player_form).reshape(-1, 1)-Y)**2))
    print(rms, simple_rms1)

    coeffs = est2.params
    model = PlayerPointPredictor(coeffs[0],coeffs[1],coeffs[2],coeffs[3])

    from prettyplotting import PrettyPlot as pp
    plot = pp.Plot(title="player form")
    plot.scatter(player_form,Y,col="k")
    plot.scatter(player_form,Y_pred,col="r")
    plot.show()

    plot = pp.Plot(title="opponent form")
    plot.scatter(opponent_form,Y,col="k")
    plot.scatter(opponent_form,Y_pred,col="r")
    plot.show()  

    plot = pp.Plot(title="team elo")
    plot.scatter(team_delta_elo,Y,col="k")
    plot.scatter(team_delta_elo,Y_pred,col="r")
    plot.show()   


    predictors = [player_form]
    X = np.array(predictors).T

    #Add constant intercept
    X2 = sm.add_constant(X)
    #Fit linear regression model
    est = sm.OLS(Y, X2)
    est2 = est.fit()
    #Predict given the input 
    Y_pred = est2.predict(X2)

    #Print model summary and rms values
    print(est2.summary())
    rms = np.sqrt(np.mean((Y_pred-Y)**2))
    simple_rms1 = np.sqrt(np.mean((np.array(player_form).reshape(-1, 1)-Y)**2))
    print(rms, simple_rms1)

    coeffs = est2.params
    simple_model = PlayerPointPredictor(coeffs[0],coeffs[1])

    plot = pp.Plot(title="player form")
    plot.scatter(player_form,Y,col="k")
    plot.scatter(player_form,Y_pred,col="r")
    plot.show()

    return model,simple_model

def predict_player_points(players:list[Player], teams:list[Team], matches:list[Match], model:PlayerPointPredictor, simple_model:PlayerPointPredictor) -> None:
    
    next_round = ut.get_next_round(matches)
    last_round = matches[-1].round

    for p in players:

        if np.mean(p.history["total_points"].values[-4:]) < 2.0:
            p.predicted_points = [p.current_form] * (last_round-next_round+1)
            continue

        if p.chance_of_playing < 0.25:
            p.predicted_points = [0.0] * (last_round-next_round+1)
            continue

        team = ut.get_team_from_id(teams, p.current_team_id)
        round_score = []

        for r in range(next_round,last_round+1):
            round_matches = [m for m in matches if m.round == r and team.id in [m.home_team_id,m.away_team_id]]

            pred_score = 0.0

            for m in round_matches:
                    
                if team.id == m.home_team_id:
                    opponent = ut.get_team_from_id(teams, m.away_team_id)
                else:
                    opponent = ut.get_team_from_id(teams, m.home_team_id)
                  
                if len(p.history) < 3:
                    pred_score += p.chance_of_playing * simple_model.predict(p,team,opponent)    
                else:
                    pred_score += p.chance_of_playing * model.predict(p,team,opponent)    

            round_score.append(pred_score)            

        p.predicted_points = round_score