# -*- coding: utf-8 -*-
"""
Created on Tue Feb 19 15:38:58 2019

@author: galar
"""
#%% Setup

import pandas as pd
import numpy as np
from scipy import stats
from tqdm import tqdm
tqdm.pandas(desc='mybar')
import sqlite3

import Elo_Rating as elo

conn = sqlite3.connect("DB/Player_Info.sqlite")

player_info = pd.read_sql("select * from PlayerInfo", conn)

conn.close()

conn2 = sqlite3.connect("DB/Game_Info.sqlite")

playbyplays = pd.read_sql("select * from PlayByPlays", conn2)
jumps = pd.read_sql("select * from Jumpballs", conn2, index_col="index")
  
conn2.close()

jumps.GAME_DATE = pd.to_datetime(jumps.GAME_DATE).dt.date

#%% ELO Rating System

# instance of the Elo rating system. Uses a k-factor of 40 and 15 game for the provisional period
i = elo.Implementation(k=40, k_prov=40, prov_games=15)

def update_elo(game):
    '''
    For a given game, get the winning/losing jump ball player's id and name and update the Elo system
    
    '''
    winner_id = game.WINNING_JUMP_ID
    loser_id = game.HOME_JUMPER_ID if game.HOME_JUMPER_ID != game.WINNING_JUMP_ID else game.AWAY_JUMPER_ID

    winner_name = player_info[player_info.PLAYER_ID == winner_id].PLAYER_NAME.values[-1]
    loser_name = player_info[player_info.PLAYER_ID == loser_id].PLAYER_NAME.values[-1]
    
    winner_info = [winner_id, winner_name]
    loser_info = [loser_id, loser_name]
    
    if not i.getPlayer(winner_info):
        i.addPlayer(winner_info)
        
    if not i.getPlayer(loser_info):
        i.addPlayer(loser_info)
        
    i.recordMatch(winner_info, loser_info, winner=winner_info)
    

jumps.progress_apply(lambda x: update_elo(x), axis=1)

# put the results of the Elo system into a data frame
player_df = pd.DataFrame()

player_df['Player_ID'] = [player.name[0] for player in i.players]
player_df['Player_Name'] = [player.name[1] for player in i.players]
player_df['Rating'] = [player.rating for player in i.players]
player_df['Game_Count'] = [player.game_count for player in i.players]
player_df['Games_Won'] = player_df.Player_ID.progress_apply(lambda x: jumps[(jumps.WINNING_JUMP_ID==x)].shape[0])
player_df['Win%'] = player_df.Games_Won / player_df.Game_Count


player_df.to_csv('jumpballs.csv')

def player_compare(player1, player2):
    '''
    This function compares any two players and returns the percentage chance 
    that player1 should win a match.
    
    Can take player1 as a string (name) or int (player_id)
    
    '''
    if isinstance(player1, str):
        player1_id = player_info[player_info.PLAYER_NAME==player1].PLAYER_ID.values[-1]
        player1_info = [player1_id, player1]
    else:
        player1_name =  player_info[player_info.PLAYER_ID==player1].PLAYER_NAME.values[-1]
        player1_info = [player1_name, player1]
        
    if isinstance(player2, str):
        player2_id = player_info[player_info.PLAYER_NAME==player2].PLAYER_ID.values[-1]
        player2_info = [player2_id, player2]
    else:
        player2_name =  player_info[player_info.PLAYER_ID==player2].PLAYER_NAME.values[-1]
        player2_info = [player2_name, player2]
        
    return i.getPlayer(player1_info).compareRating(i.getPlayer(player2_info))

#%% Team Scoring
    
'''
Want to explore how often a team scores given they have the ball first.

The way this is done is finding all instances where a team has won the jump ball and
calculate how often they scored first. This is done for each team in each season.

A chi-square test of homogeneity is performed to determine if there is any difference between
teams.

Probably not the most sophisticated way to do it. Further updates can be made to do a better
estimation of how likely a team is able to score first when they get the ball first

'''

# now only looking at the very opening tip of each regular season game
jumpballs = jumps.copy()
jumpballs.GAME_ID = jumpballs.GAME_ID.progress_apply(lambda x: '{0:0>10}'.format(x))
jumpballs = jumpballs[(jumpballs.PCTIMESTRING == '12:00') & (jumpballs.PERIOD == 1) & (jumpballs.GAME_ID.str.startswith('002'))]

# determine who scored first. would be indicated using the SCOREMARGIN field
# SCOREMARGIN is always from perspective of home team
def scored_first(game):
    scores = playbyplays.iloc[game.name:game.name+100].SCOREMARGIN
    scores = scores.dropna()
    first_score = int(scores.values[0])
    return game.HOME_TEAM_ID if first_score > 0 else game.AWAY_TEAM_ID


jumpballs['SCORED_FIRST'] = jumpballs.progress_apply(lambda x: scored_first(x), axis=1)

# check if the team who won the tip scored first
jumpballs['WINNER_SCORED_FIRST'] = jumpballs.progress_apply(lambda x: 1 if x.WON_TIP == x.SCORED_FIRST else 0, axis=1)
print('The winner of the jumpball scores first {:.2%} of the time'.format(jumpballs.WINNER_SCORED_FIRST.sum()/jumpballs.shape[0]))

def homog_test(season='All', sig=0.05):
    counts = jumpballs.copy()
    if season != 'All':
        counts = counts[counts.SEASON_YEAR == season]
    counts_scores= counts.copy()
    counts = pd.DataFrame(counts.groupby(['WON_TIP']).count().mean(axis=1))
    counts_scores = pd.DataFrame(counts_scores.groupby(['WON_TIP']).sum()['WINNER_SCORED_FIRST'])
    counts_scores['No'] = counts[0] - counts_scores.WINNER_SCORED_FIRST
    
    chi2, p, dof, expected = stats.chi2_contingency(counts_scores.values)
    
    if p > sig:
        print('Fail to reject null. All proportions the same. p-value of {:.2%}'.format(p))
    else:
        print('Reject null. Some proportions different. p-value of {:.2%}'.format(p))    


homog_test()

def team_score_formula(player1, player2):
    ''' 
    The above statistical test showed that teams score first about 60% of the time
    when they win the tip.
    
    This is a very rough calculation of a team's chance to score first before the tip.
    
    '''
    p = player_compare(player1, player2)
    return p * 0.6 + (1-p) * 0.4