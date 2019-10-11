# -*- coding: utf-8 -*-
"""
Created on Sun Feb 17 14:50:56 2019

@author: galar
"""

import pandas as pd
import sqlite3
from tqdm import tqdm

from nba_py import player

season = '2018-19'

def update_player_info(season):
'''
Updates the database table containing player information from two sources:
    1. stats.nba.com
    2. basketball-reference
These two sources are needed since the player information from stats.nba.com only shows players on the team
they are most recently on. bball-ref contains a record for each team a player has played for.

The parameter is season, which should be whatever the current season is
'''
        
    conn = sqlite3.connect("DB/PLayer_Info.sqlite")
    
    # read in player list from stats.nba.com
    players = pd.read_sql("select * from NBA", conn)
    
    # read in player list from basketball-reference
    bball_ref = pd.read_sql("select * from BbRef", conn)
    
    # read in previous player info df
    player_info = pd.read_sql("select * from PlayerInfo", conn)
    
    players_update = pd.DataFrame()
    
    # grab the player list for season from stats.nba.com
    player_list = player.PlayerList(season=season, only_current=0).info()
    player_list['SEASON_YEAR'] = season
    players_update = players_update.append(player_list)
    
    # don't need these columns
    players_update = players_update.drop(['ROSTERSTATUS', 'DISPLAY_LAST_COMMA_FIRST', 'PLAYERCODE', 'GAMES_PLAYED_FLAG'], axis=1)
    
    # only keep the new players
    common = players.merge(players_update, on=['PERSON_ID','SEASON_YEAR', 'TEAM_ABBREVIATION'], suffixes=('','_x'))
    common = common[common.columns.drop(list(common.filter(regex='_x')))]
    
    diffs =  players_update[(~players_update.PERSON_ID.isin(common.PERSON_ID))]
    diffs = diffs[diffs.TEAM_CODE > '']
    
    players = players.append(diffs, sort=False)
    
    # save the new player list
    players.to_sql("NBA", conn, if_exists='replace', index=False)
    
    
    # filter on only players from 2006 and later
    players_post_06 = players[players.TO_YEAR > '2005']
    
    # some names aren't the same between the two sources. this is a manual fix
    name_change = pd.read_csv("Data/PlayerInfo/bbref_namefix.csv", index_col=0)
    
    def namechange(player):
        try:
            return name_change.loc[player].stats_nba
        except:
            return player
    
    tqdm.pandas(desc='mybar')
    
    bball_ref.PLAYER_NAME = bball_ref.PLAYER_NAME.progress_apply(lambda x: namechange(x))
    
    # map the player ID
    bball_ref['PLAYER_ID'] = bball_ref.PLAYER_NAME.progress_apply(lambda x: players_post_06[players_post_06.DISPLAY_FIRST_LAST == x].PERSON_ID.values[0])
    
    # this player changed his name between seasons so he was causing lookup errors. manual fix
    indices = bball_ref[(bball_ref.PLAYER_NAME == 'Jeff Ayres') & (bball_ref.SEASON_YEAR < '2013-14')].index
    bball_ref.loc[indices, 'PLAYER_NAME'] = 'Jeff Pendergraph'
    
    # mapping for team ID's
    bball_to_teamID = pd.read_csv('Data/PlayerInfo/bball_teamID.csv', index_col=0)
    
    # add team IDs
    bball_ref['TEAM_ID'] = bball_ref.TEAM_ABBV.progress_apply(lambda x: bball_to_teamID.loc[x].values[0])
    
    # only keep the new player info
    common = player_info.merge(bball_ref, on=['PLAYER_ID','SEASON_YEAR', 'TEAM_ID'], suffixes=('','_x'))
    common = common[common.columns.drop(list(common.filter(regex='_x')))]
    
    diffs =  bball_ref.loc[~bball_ref.index.isin(common.index)]
    
    # save the new player info df
    player_info = player_info.append(diffs, sort=False)
    
    player_info.to_sql("PlayerInfo", conn, if_exists='replace', index=False)
    conn.close()
