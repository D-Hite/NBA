# -*- coding: utf-8 -*-
"""
Created on Thu Sep 30 14:01:07 2021

@author: Dylan
"""

import pandas as pd
from datetime import datetime

TEAMS = ['ATL', 'BKN', 'BOS', 'CHA', 'CHI', 'CLE', 'DAL', 'DEN', 'DET', 'GSW', 'HOU', 'IND', 'LAC', 'LAL', 'MEM',
             'MIA', 'MIL', 'MIN', 'NOP', 'NYK', 'OKC', 'ORL', 'PHI', 'PHX', 'POR', 'SAC', 'SAS', 'TOR', 'UTA', 'WAS']

def team_filter(df, team):
    return df[df['TEAM_ABBREVIATION'] == team]


class ModelStats():

    def __init__(self):
        self.data_d = {}
        self.seasons = set()
        self.files = set()
        self.neglected = {}
        self.sgids = {}
        
    def load_season(self, season, file):
        if (file[:4] == 'home') or (file[:4] == 'away'):
            df = pd.read_csv(f'DATA/avgsV1/{file}{season}.csv')
            df.sort_values('GAME_ID', inplace=True, kind='mergesort')
            self.data_d[file+season] = df
            self.neglected[season] = set()
            self.seasons.add(season)
            self.files.add(file)
        else:
            df = pd.read_csv(f'DATA/avgsV2/{file}{season}.csv')
            df.sort_values('GAME_ID', inplace=True, kind='mergesort')
            self.data_d[file+season] = df
            self.neglected[season] = set()
            self.seasons.add(season)
            self.files.add(file)
    
    def apply_rs_filters(self, x=10):
        """
        
        big diff between getting rid of GIDs and indeces bc we need same NEXT_GID
        
        """
        for s in self.seasons:
            self.skip_x(s, x)
            self.os_filter(s, 'avgs', False, s[:4])
            self.lg_filter(s, 'avgs')
            for f in self.files:
                self.neg_filter(s, f)
                if ((f[:4]!='home') and (f[:4]!='away')):
                    self.double_filter(s, f)
        self.apply_sgid()


    def apply_sgid(self):
        for s in self.seasons:
            self.ms_sgid(s, self.files)
            for f in self.files:
                tfil = []
                for i in self.data_d[f+s]['NEXT_GAME_ID']:
                    tfil.append(i in self.sgids[s])
                self.data_d[f+s] = self.data_d[f+s][tfil]

    def ms_sgid(self, season, files):
        """
        model stats season gid filter
        get all game id's that are in the same season / same datasets in the season
        """
        nglist = []
        for i in files:
            nglist.append(self.data_d[i+season]['NEXT_GAME_ID'].tolist())
        result = set(nglist[0])
        for s in nglist[1:]:
            result.intersection_update(s)
        if 0 in result:
            result.remove(0)
        self.sgids[season] = result


                
    def double_filter(self, s, f):
        """
        adds GID to neglected when there is not two rows for the NEXT_GAME_ID
        """
        df = self.data_d[f+s]
        x=df['NEXT_GAME_ID'].value_counts()==2
        newlis=[]
        for ngid in df['NEXT_GAME_ID']:
            newlis.append(x[ngid])
        self.data_d[f+s] = df[newlis]
        
        
        
    # NEGLECTED STUFF, USES NEGLECTED TO REMOVE UNWANTED GID's
                
        
    def skip_x(self, s, x):
        """
        uses stat bucket to get list of GAME_ID's that does not contain the first 10 games a team has played
        """
        df1 = self.data_d['avgs'+s].sort_values('GAME_ID')
        df1.sort_values('TEAM_ABBREVIATION', inplace=True, kind='mergesort')
        first = df1['TEAM_ABBREVIATION'].tolist()[0]
        count=0
        for ta, gid in zip(df1['TEAM_ABBREVIATION'], df1['GAME_ID']):
            if ta != first:
                first = ta
                count = 0
                self.neglected[s].add(int(gid))
                continue
            if count <= x:
                count+=1
                self.neglected[s].add(int(gid))
            else:
                count+=1

                
    def date_filter(self, s, f, sd=datetime(1969, 1, 1), ed=datetime(2050, 1, 1)):
        """
        NOT PERFECT, SEPERATES BASED ON FIRST INSTANCE THAT GAME DATE PAST SD OR ED
        SOME GAMES SLIP THROUGH IF GID IS NOT PERFECTLY SORTED BY DATE
        """
        
        # FIND STARTING GID AND ENDIND GID (GAME_ID)
        df1 = self.data_d[f+s].sort_values('GAME_DATE')
        si = None
        ei = None
        for i, x in zip(df1['GAME_ID'], df1['GAME_DATE']):
            if datetime.strptime(x, "%Y-%m-%d") > sd:
                si = i
                break
            for j, y in zip(df1['GAME_ID'], df1['GAME_DATE']):
                if datetime.strptime(y, "%Y-%m-%d") > ed:
                    ei = j
                    break
                    
        # ADD GIDS TO NEGLECTED DEPENDING ON IF START AND END INDEX FOUND
        if si==None:
            if ei==None:
                return
            else:
                for ind in df1['GAME_ID']:
                    if ind > ei:
                        self.neglected[s].add(ind)
                return
        if ei==None:
            for ind in df1['GAME_ID']:
                if ind < si:
                    self.neglected[s].add(ind)
        else:
            for ind in df1['GAME_ID']:
                if ind < si:
                    self.neglected[s].add(ind)
                if ind > ei:
                    self.neglected[s].add(ind)
                    
                    
    def os_filter(self, s, f, os, year):
        df = self.data_d[f+s]
        if os:
            for ind, sid in zip(df['GAME_ID'], df.SEASON_ID):
                if sid == int('2'+'2015'):
                    self.neglected[s].add(ind)
        else:
            for ind, sid in zip(df['GAME_ID'], df.SEASON_ID):
                if sid == int('4'+'2015'):
                    self.neglected[s].add(ind)

                    
    def ha_filter(self, s, f, ha):
        df = self.data_d[f+s]
        if ha == 'h':
            tarr = []
            for i in df['MATCHUP'].values:
                tarr.append('@' not in str(i))
            self.data_d[f+s] = self.data_d[f+s][tarr]
            return
        else:
            tarr = []
            for i in df['MATCHUP'].values:
                tarr.append('@' in str(i))
            self.data_d[f+s] = self.data_d[f+s][tarr]
        
        
    def lg_filter(self, s, f):
        df = self.data_d[f+s]
        for ind, ngid in zip(df['GAME_ID'], df['NEXT_GAME_ID']):
            if ngid == 0:
                self.neglected[s].add(ind)
            if str(ngid)[0]=='4':
                self.neglected[s].add(ind)
                
                
    # APPLICATIONS OF FILTERS ON NEGLECTED OR A CHOSEN GIDLIST
    
    def neg_filter(self, s, f):
        df = self.data_d[f+s]
        flist = []
        for i in df['GAME_ID'].tolist():
            flist.append(i not in self.neglected[s])
        self.data_d[f+s] = df[flist]
        
        
class Model():
    
    def __init__(self):
        
        # calc function numbers
        self.cf_numbers = {}
        # Prediction numbers
        self.end_d = {}
        # To check whether season has been done
        self.outcheck = {}
        # everything except predictions for results
        self.outcomes = {}
        
        # results and model accuracy
        self.results = {}
        self.acc = {}
        
        
    def run_model(self, ms, seasons, files, calc_func, calc_cols, end_calc_func, file_weights, column_weights):
        # FIRST, RESET PREV RUN MODEL DATA
        for s in seasons:
            self.outcheck[s] = False
            for f in files:
                if (f[:4]=='home'):
                    self.ha_files_np(ms, s, f, calc_func, calc_cols, column_weights, file_weights)
                elif (f[:4]=='away'):
                    continue
                else:
                    self.norm_files_np(ms, s, f, calc_func, calc_cols, column_weights, file_weights)
        self.apply_end(seasons, end_calc_func, file_weights.keys())
        self.format_results(seasons)
                
    def norm_files_np(self, ms, s, f, calc_func, calc_cols, column_weights, file_weights):
        out_d = {}
        df = ms.data_d[f+s].sort_values('NEXT_MATCHUP')
        df.sort_values('NEXT_GAME_ID', inplace=True, kind='mergesort')
        ndata = df[calc_cols].to_numpy()
        hngid = df['NEXT_GAME_ID'].tolist()
        
        outcome_d = {}
        pm = df['NEXT_PLUS_MINUS'].tolist()
        spread = df['NEXT_SPREAD'].tolist()
        ou = df['NEXT_O/U'].tolist()
        matchups = df['NEXT_MATCHUP'].tolist()
        for j in range(int(len(hngid))-1):
            if matchups[j][4] == '@':
                adjust = 1
            else:
                adjust = 0
            # J+1 SO THAT IT IS HOME PLUS MINUS, HOME SPREAD
            outcome_d[hngid[j+adjust]] = [hngid[j+adjust], matchups[j+adjust], pm[j+adjust], spread[j+adjust], ou[j+adjust]]
            j+=1
            
        if not self.outcheck[s]:
            self.outcheck[s] = True
            self.outcomes[s] = outcome_d 
        assert(len(ndata)%2 == 0)
        for i in range(int(len(ndata)-1)):
            if matchups[j][4] == '@':
                out_d[hngid[i]] = file_weights[f] * calc_func(ndata[i+1], ndata[i], column_weights)
            else:
                out_d[hngid[i]] = file_weights[f] * calc_func(ndata[i], ndata[i+1], column_weights)
            i+=1
        self.cf_numbers[f+s] = out_d
            
    def ha_files_np(self, ms, s, f, calcfunc, calccols, colweights, fweights):
        fs = f[4:]+s
        out_d = {}
        dfh = ms.data_d['home'+fs].sort_values('NEXT_GAME_ID')
        dfa = ms.data_d['away'+fs].sort_values('NEXT_GAME_ID')
        hnp = dfh[calccols].to_numpy()
        anp = dfa[calccols].to_numpy()
        assert(len(hnp)==len(anp))
        assert(dfh['NEXT_GAME_ID'].tolist()==dfa['NEXT_GAME_ID'].tolist())
        hngid = dfh['NEXT_GAME_ID'].tolist()
        for i in range(len(hnp)):
            out_d[hngid[i]] = fweights['ha'+f[4:]] * calcfunc(hnp[i], anp[i], colweights)
        self.cf_numbers['ha'+f[4:]+s] = out_d
            
    def apply_end(self, seasons, ecfunc, fkeys):
        for s in seasons:
            out_d = {}
            for i in list(self.cf_numbers['avgs'+s]):
                out_d[i] = ecfunc(self.get_edata(s, i, fkeys))
            self.end_d[s] = out_d
        
    def get_edata(self, s, i, filekeys):
        relist = []
        for key in filekeys:
            relist.append(self.cf_numbers[key+s][i])
        return relist
    
    def format_results(self, seasons):
        for s in seasons:
            df1 = pd.DataFrame(self.outcomes[s].values(), columns = ['GAME_ID', 'MATCHUP', 'PLUS_MINUS', 'SPREAD', 'O/U'])
            df1['PREDICTION'] = self.end_d[s].values()
            
            winners = df1['PLUS_MINUS'] + df1['SPREAD']
#             df1['PM+SPREAD'] = winners
            
            nelist = []
            for i in winners:
                if i>0:
                    nelist.append('h')
                elif i<0:
                    nelist.append('a')
                else:
                    nelist.append('p')
            df1['WINNING_BET'] = nelist
                    
            ourbets = df1['SPREAD'] + df1['PREDICTION']
            nelist2 = []
            for j in ourbets:
                if j>0:
                    nelist2.append('h')
                else:
                    nelist2.append('a')
            df1['OUR_BET'] = nelist2
            
            nelist3 = list(df1['WINNING_BET'] == df1['OUR_BET'])
            for p in range(len(nelist)):
                if nelist[p] == 'p':
                    nelist3[p] = 1
                elif (nelist3[p]):
                    nelist3[p] = 2
                else:
                    nelist3[p] = 0
            df1['HIT'] = nelist3
            
            self.acc[s] = {df1['HIT'].value_counts()[2] / (df1['HIT'].value_counts()[0] + df1['HIT'].value_counts()[2])}
            self.results[s] = df1