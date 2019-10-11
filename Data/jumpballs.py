# -*- coding: utf-8 -*-
"""
Created on Thu Feb 14 19:02:23 2019

@author: galar
"""

import pandas as pd
import re
from tqdm import tqdm
tqdm.pandas(desc='mybar')
import sqlite3


def update_jumpballs():
'''
Updates a df containing information for each game's jump balls

Only considers jump balls that happen at the beginning of the game or overtime periods

'''
    
    conn = sqlite3.connect("DB/Player_Info.sqlite")
    
    player_info = pd.read_sql("select * from PlayerInfo", conn)
    
    conn.close()
    
    conn2 = sqlite3.connect("DB/Game_Info.sqlite")
    
    # prior jump ball df
    jumpballs = pd.read_sql("select * from Jumpballs", conn2, index_col='index')
    
    # general info for each game (game_id, home_team_id, away_team_id)
    homeaway = pd.read_sql("select * from HomeAway", conn2, index_col='GAME_ID')
    
    # play by play for each game (to know who won the jump balls)
    playbyplays = pd.read_sql("select * from PlayByPlays", conn2)    
    
    jumps = playbyplays.copy()
    
    indices = homeaway.index.difference(jumpballs.GAME_ID)
    
    jumps = jumps[jumps.GAME_ID.isin(indices)]
    
    # jumpballs have EVENTMSGTYPE 10
    jumps = jumps[jumps.EVENTMSGTYPE == 10]
    
    # Only want jumpballs at the start of game or overtimes
    jumps = jumps[((jumps.PCTIMESTRING == '12:00') & (jumps.PERIOD == 1)) | ((jumps.PCTIMESTRING == '5:00') & (jumps.PERIOD > 4))]
    
    # Look up TEAM_ID's, SEASON_YEAR and GAME_DATE
    jumps['HOME_TEAM_ID'] = jumps.GAME_ID.progress_apply(lambda x: homeaway.loc[x].HOME_TEAM_ID)
    jumps['AWAY_TEAM_ID'] = jumps.GAME_ID.progress_apply(lambda x: homeaway.loc[x].AWAY_TEAM_ID)
    jumps['SEASON_YEAR'] = jumps.GAME_ID.progress_apply(lambda x: '20' + x[3:5] + '-' + str('{0:0>2}'.format(int(x[3:5])+1)))
    jumps['GAME_DATE'] = jumps.GAME_ID.progress_apply(lambda x: homeaway.loc[x].GAME_DATE)
    jumps.GAME_DATE = pd.to_datetime(jumps.GAME_DATE).dt.date
    
    # Most of the time, the jumpball description is under HOME. But sometimes it's under VISITOR so I'll combine them
    jumps['DESCRIPTION'] = jumps.progress_apply(lambda x: x.HOMEDESCRIPTION if x.HOMEDESCRIPTION is not None else x.VISITORDESCRIPTION, axis=1)
    
    # For this purpose, I don't need these columns
    jumps = jumps.drop(['NEUTRALDESCRIPTION', 'EVENTMSGTYPE', 'EVENTMSGACTIONTYPE', 'WCTIMESTRING'], axis=1)
    
    # Need to get the names of the two players who jumped
    # Description is always in the form: "Jump Ball Player1 vs. Player2: Tip to Player3
    new = jumps.DESCRIPTION.str.split('vs. ', expand=True)
    jumps['Jumper1'] = new[0].progress_apply(lambda x: x.replace('Jump Ball ', '').strip())
    jumps['Jumper2'] = new[1].progress_apply(lambda x: x.split(':')[0])
    
    # Identify which player was on the home team and away team
    jumps['HOME_JUMPER'] = jumps.progress_apply(lambda x: x.Jumper1 if x.HOMEDESCRIPTION is not None else x.Jumper2, axis=1)
    jumps['AWAY_JUMPER'] = jumps.progress_apply(lambda x: x.Jumper2 if x.HOMEDESCRIPTION is not None else x.Jumper1, axis=1)
    
    # Don't need these columns anymore
    jumps = jumps.drop(['EVENTNUM','SCORE', 'SCOREMARGIN', 'DESCRIPTION', 'HOMEDESCRIPTION', 'VISITORDESCRIPTION', 'Jumper1', 'Jumper2'], axis=1)
    
    # Determine which team won the tip. The next play should be an action for the team that won the tip
    # If both teams have action, one of them should be steal or block
    def who_won(x):
        nextplay = playbyplays.loc[x.name+1]
        
        if nextplay.HOMEDESCRIPTION is None:
            return x.AWAY_TEAM_ID
        elif nextplay.HOMEDESCRIPTION is not None and re.search('Steal', nextplay.HOMEDESCRIPTION , re.IGNORECASE):
            return x.AWAY_TEAM_ID
        elif nextplay.HOMEDESCRIPTION is not None and re.search('Block', nextplay.HOMEDESCRIPTION , re.IGNORECASE):
            return x.AWAY_TEAM_ID
        else:
            return x.HOME_TEAM_ID
    
    jumps['WON_TIP'] = jumps.progress_apply(lambda x: who_won(x), axis=1)
    
    
    # Get PLAYER_ID from just last name
    def get_home_player_id(game):
        if ' ' in game.HOME_JUMPER: # ex: Hardaway Jr.
            splits = game.HOME_JUMPER.split(' ')
            info = player_info[(player_info.PLAYER_NAME.str.contains(re.sub('[,.]','',splits[0]))) & (player_info.PLAYER_NAME.str.contains(re.sub('[,.]','',splits[1]))) & (player_info.TEAM_ID == game.HOME_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            return info.PLAYER_ID.values[0]
        else: # need to split player name to avoid wrong mappings (ex: Jordan Farmar and DeAndre Jordan)
            info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[1].str.contains(game.HOME_JUMPER)) & (player_info.TEAM_ID == game.HOME_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            if len(info) == 0: # ex: Nene
                info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[0].str.contains(game.HOME_JUMPER)) & (player_info.TEAM_ID == game.HOME_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            if len(info) == 0: # ex: James Michael McAdoo
                info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[2].str.contains(game.HOME_JUMPER)) & (player_info.TEAM_ID == game.HOME_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            return info.PLAYER_ID.values[0]
        
    def get_away_player_id(game):
        if ' ' in game.AWAY_JUMPER:
            splits = game.AWAY_JUMPER.split(' ')
            info = player_info[(player_info.PLAYER_NAME.str.contains(re.sub('[,.]','',splits[0]))) & (player_info.PLAYER_NAME.str.contains(re.sub('[,.]','',splits[1]))) & (player_info.TEAM_ID == game.AWAY_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            return info.PLAYER_ID.values[0]
        else:
            info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[1].str.contains(game.AWAY_JUMPER)) & (player_info.TEAM_ID == game.AWAY_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            if len(info) == 0:
                info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[0].str.contains(game.AWAY_JUMPER)) & (player_info.TEAM_ID == game.AWAY_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            if len(info) == 0:
                info = player_info[(player_info.PLAYER_NAME.str.split(' ', expand=True)[2].str.contains(game.AWAY_JUMPER)) & (player_info.TEAM_ID == game.AWAY_TEAM_ID) & (player_info.SEASON_YEAR == game.SEASON_YEAR)]
            return info.PLAYER_ID.values[0]
    
    
    jumps['HOME_JUMPER_ID'] =  jumps.progress_apply(lambda x: get_home_player_id(x), axis=1)
    jumps['AWAY_JUMPER_ID'] =  jumps.progress_apply(lambda x: get_away_player_id(x), axis=1)
    
    # Determine which player won the tip based on which team won the tip
    jumps['WINNING_JUMP_ID'] = jumps.progress_apply(lambda x: x.HOME_JUMPER_ID if x.WON_TIP == x.HOME_TEAM_ID else x.AWAY_JUMPER_ID, axis=1)
    
    jumpballs = jumpballs.append(jumps)
    
    jumpballs.to_sql("Jumpballs", conn2, if_exists='replace')
    
    conn2.close()
