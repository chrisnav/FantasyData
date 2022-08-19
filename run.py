from fantasydata import utility as ut
from fantasydata import get_data as gd
from fantasydata import process_data as pr
from fantasydata import predict as pred

import pandas as pd

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

pr.add_calculated_attributes(players,teams,matches,squad,initial_elo)
ut.save_all_data(data_dir,players,teams,matches,squad,suffix="calc")

try:
    model = pred.read_linear_model(directory,"model.csv")
    simple_model = pred.read_linear_model(directory,"simlpe_model.csv")
except FileNotFoundError:
    model, simple_model = pred.estimate_linear_model(players,teams)
    pred.linear_model_to_csv(directory,model)
    pred.linear_model_to_csv(directory,simple_model)


pred.predict_player_points(players,teams,matches,model,simple_model)

my_players = [p for p in players if p.id in squad.current_players]
for p in my_players:
    print(p,p.current_value,p.squad_adjusted_value,p.predicted_points)