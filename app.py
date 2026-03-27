import streamlit as st
import pandas as pd
import numpy as np
from pybaseball import pitching_stats_bref, batting_stats_bref
import datetime
import requests

# --- CONFIG ---
st.set_page_config(page_title="2026 Sharp MLB Tool", layout="wide")
ODDS_API_KEY = "787acf6590bcedb093322a7022b0491e"

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_mlb_data():
    import os
    os.environ['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    try:
        # Fetching 2026 Season Stats
        p = pitching_stats_bref(2026)
        b = batting_stats_bref(2026)
        
        # Clean up column names for the model
        p['Team'] = p['Tm']
        b['Team'] = b['Tm']
        
        # Calculate SO/9 manually to avoid KeyError
        p['SO9_Calc'] = (p['SO'] / p['IP']) * 9
        
        return p, b
    except Exception as e:
        st.error(f"Waiting for 2026 Stats to populate... {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_live_odds():
    url = f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/'
    params = {'apiKey': ODDS_API_KEY, 'regions': 'us', 'markets': 'h2h,totals', 'oddsFormat': 'american'}
    try:
        return requests.get(url, params=params).json()
    except:
        return []

# --- UI ---
st.title("⚾ 2026 Sharp MLB Analytics")

p_df, b_df = fetch_mlb_data()
odds_data = fetch_live_odds()

if not p_df.empty:
    st.sidebar.header("Matchup")
    team_list = sorted(p_df['Team'].unique())
    home_t = st.sidebar.selectbox("Home Team", team_list, index=0)
    away_t = st.sidebar.selectbox("Away Team", team_list, index=1)
    
    h_pitcher = st.sidebar.selectbox("Home Pitcher", p_df[p_df['Team'] == home_t]['Name'])
    a_pitcher = st.sidebar.selectbox("Away Pitcher", p_df[p_df['Team'] == away_t]['Name'])

    t1, t2, t3 = st.tabs(["🎯 Betting Edge", "📊 Player Props", "💰 Live Odds"])

    with t1:
        # Basic ERA-based Total Projection
        h_era = p_df[p_df['Name'] == h_pitcher]['ERA'].iloc[0]
        a_era = p_df[p_df['Name'] == a_pitcher]['ERA'].iloc[0]
        proj_total = (h_era + a_era) * 0.92
        st.metric("Projected Total Runs", round(proj_total, 2))
        st.caption("Lower is better for the Under. Higher is better for the Over.")

    with t2:
        st.subheader("Pitcher Strikeout Projection")
        k9 = p_df[p_df['Name'] == h_pitcher]['SO9_Calc'].iloc[0]
        st.write(f"**{h_pitcher}** is averaging **{round(k9, 2)}** strikeouts per 9 innings this season.")
        st.info("Compare this to the Sportsbook 'K' line. If this is 2+ points higher than the line, consider the OVER.")

    with t3:
        if odds_data:
            for game in odds_data[:8]:
                st.write(f"**{game['away_team']} @ {game['home_team']}**")
                st.json(game['bookmakers'][0]['markets'][0]['outcomes'])
else:
    st.info("App is ready. Please select your teams in the sidebar once 2026 data loads.")
