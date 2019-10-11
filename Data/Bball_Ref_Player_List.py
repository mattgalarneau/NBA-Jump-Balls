# -*- coding: utf-8 -*-
"""
Created on Tue Jan  8 15:47:47 2019

@author: galar
"""

#%%
import pandas as pd
from bs4 import BeautifulSoup
import requests
import sqlite3
import time


def updaet_bball_ref(year='2019'):
'''
Updates the database table containing player information from basketball-reference

Only paramter is the year which is used to pull player lists up to that season

'''
    conn = sqlite3.connect("DB/Player_Info.sqlite")
    
    # prior player list from basketball-reference
    bball_ref = pd.read_sql("select * from BbRef", conn)
    
    update_df = pd.DataFrame(columns=['SEASON_YEAR', 'TEAM_ABBV', 'PLAYER_NAME'])
    
    # team abbreviations on basketball-reference's website
    teams = ['ATL', 'BOS', 'NJN', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW',
             'HOU', 'IND', 'LAC', 'LAL', 'MEM', 'MIA', 'MIL', 'MIN', 'NOH', 'NYK', 
             'OKC', 'ORL', 'PHI', 'PHO', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']
        
    for team in teams:
        print(team)
        offset = 0
        i=0
        while True:
            # url to grab each team's players from 2006-07 to 2018-19
            url = 'https://www.basketball-reference.com/play-index/psl_finder.cgi?request=1&match=single&type=totals&per_minute_base=36&per_poss_base=100&lg_id=NBA&is_playoffs=N&year_min='+year+'&year_max='+year+'&franch_id=' + team + '&season_start=1&season_end=-1&age_min=0&age_max=99&shoot_hand=&height_min=0&height_max=99&birth_country_is=Y&birth_country=&birth_state=&college_id=&draft_year=&is_active=&debut_yr_nba_start=&debut_yr_nba_end=&is_hof=&is_as=&as_comp=gt&as_val=0&award=&pos_is_g=Y&pos_is_gf=Y&pos_is_f=Y&pos_is_fg=Y&pos_is_fc=Y&pos_is_c=Y&pos_is_cf=Y&qual=&c1stat=&c1comp=&c1val=&c2stat=&c2comp=&c2val=&c3stat=&c3comp=&c3val=&c4stat=&c4comp=&c4val=&c5stat=&c5comp=&c6mult=&c6stat=&order_by=player&order_by_asc=Y&offset=' + str(offset)
        
            raw_data = requests.get(url)
            soup_big = BeautifulSoup(raw_data.text, 'html.parser')
            soup = soup_big.find_all('tr')
            
            if len(soup) == 0:
                break
            
            for s in soup[2:]:
                contents = s.contents
                if len(contents) == 32:
                    i+=1
                    season = contents[1].contents[0]
                    team_id = contents[3].contents[0].contents[0]
                    player = contents[5].contents[0].contents[0]
                    d = {'SEASON_YEAR': season, 'TEAM_ABBV': team_id, 'PLAYER_NAME': player}
                    update_df = update_df.append(pd.DataFrame(d, index=[0]))
                            
            offset += 100
            print(i,' players processed')
            
        time.sleep(3)
    
    # only keep the new players
    common = bball_ref.merge(update_df,on=['PLAYER_NAME','SEASON_YEAR','TEAM_ABBV'])
    
    diffs =  pd.concat([common,update_df], sort=False).drop_duplicates(keep=False)
    
    bball_ref = bball_ref.append(diffs, sort=False)
    
    bball_ref = bball_ref.reset_index(drop=True)
    
    # save out new player list
    bball_ref.to_sql("BbRef", conn, if_exists='replace', index=False)
    
    conn.close()