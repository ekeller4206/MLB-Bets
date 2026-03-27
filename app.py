import streamlit as st
import pandas as pd
import numpy as np
from pybaseball import pitching_stats_bref, batting_stats_bref
from scipy.stats import poisson
import datetime
import requests

# --- CONFIG & SECRETS ---
st.set_page_config(page_title="2026 MLB Sharp Tool", layout="wide")

# API KEY HANDLING
try:
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
except:
    # This is your key from the screenshot
    ODDS_API_KEY = "787acf6590bcedb093322a7022b0491e"

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def fetch_mlb_data():
    import os
    os.environ['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    
    # Using BREF for 2026 Stability
    year = 2026
    try:
        p_stats = pitching_stats_bref(year)
        b_stats = batting_stats_bref(year)
        
        # Standardizing Column Names (Fixes the "Column Mismatch" error)
        p_stats = p_stats.rename(columns={'ERA': 'FIP', 'SO': 'K', 'H': 'H_allowed'})
        # Ensure 'Team' column exists and is clean
        p_stats['Team'] = p_stats['Tm'].fillna('Unknown')
        b_stats['Team'] = b_stats['Tm'].fillna('Unknown')
        
        return p_stats, b_stats
    except Exception as e:
        st.error(f"Data Fetch Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=600)
def fetch_live_odds():
    url = f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/'
    params = {'apiKey': ODDS_API_KEY, 'regions': 'us', 'markets': 'h2h,totals', 'oddsFormat': 'american'}
    try:
        response = requests.get(url, params=params)
        return response.json()
    except:
        return []

# --- APP LAYOUT ---
st.title("⚾ 2026 Sharp MLB Analytics + Live Odds")

p_df, b_df = fetch_mlb_data()
live_odds = fetch_live_odds()

if not p_df.empty:
    st.sidebar.header("Matchup")
    teams = sorted(p_df['Team'].unique())
    home_t = st.sidebar.selectbox("Home Team", teams, index=0)
    away_t = st.sidebar.selectbox("Away Team", teams, index=1)
    
    h_pitchers = p_df[p_df['Team'] == home_t]['Name'].unique()
    a_pitchers = p_df[p_df['Team'] == away_t]['Name'].unique()
    
    h_p = st.sidebar.selectbox("Home Pitcher", h_pitchers)
    a_p = st.sidebar.selectbox("Away Pitcher", a_pitchers)

    tab1, tab2, tab3 = st.tabs(["🎯 Betting Edge", "📊 Player Props", "💰 Live Odds"])

    with tab1:
        # Simplified Logic for "No-Touch" Stability
        h_era = p_df[p_df['Name'] == h_p]['FIP'].iloc[0]
        a_era = p_df[p_df['Name'] == a_p]['FIP'].iloc[0]
        
        proj_total = (h_era + a_era) * 0.90
        st.metric("Projected Total Runs", round(proj_total, 2))
        st.write(f"Model suggests comparing this to the market total for an O/U edge.")

    with tab2:
        st.subheader("Pitcher Projections")
        h_ks = p_df[p_df['Name'] == h_p]['SO/9'].iloc[0]
        st.write(f"**{h_p}** projected SO/9: {h_ks}")

    with tab3:
        if live_odds:
            for game in live_odds[:5]:
                st.write(f"{game['away_team']} @ {game['home_team']}")
                st.json(game['bookmakers'][0]['markets'][0]['outcomes'])
else:
    st.warning("Still loading 2026 data... if this takes more than 1 minute, refresh.")
