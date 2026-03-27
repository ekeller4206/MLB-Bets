import streamlit as st
import pandas as pd
import numpy as np
from pybaseball import pitching_stats, batting_stats
from scipy.stats import poisson
import datetime
import requests

# --- CONFIG & SECRETS ---
st.set_page_config(page_title="2026 MLB Sharp Tool", layout="wide")

# To keep your API key safe, use Streamlit Secrets (Settings > Secrets)
# For local testing, you can replace this with your actual string: "your_key_here"
try:
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
except:
    ODDS_API_KEY = "787acf6590bcedb093322a7022b0491e"

# --- DATA ENGINE (STATS) ---
@st.cache_data(ttl=3600)
def fetch_mlb_data():
    # THE FIX: This makes FanGraphs think your app is a real Chrome browser
    import os
    os.environ['USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    
    current_year = 2026
    
    # Adding 'qual' limits the search to players with enough playing time
    # This makes the data transfer much smaller and faster
    p_season = pitching_stats(current_year, qual=10) 
    b_season = batting_stats(current_year, qual=10)
    
    # Recency Window (Last 14 Days)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    
    # We use the date strings here
    p_l14 = pitching_stats(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    b_l14 = batting_stats(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    return p_season, b_season, p_l14, b_l14
    
    return p_season, b_season, p_l14, b_l14

# --- DATA ENGINE (LIVE ODDS) ---
@st.cache_data(ttl=600)
def fetch_live_odds():
    url = f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/'
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'oddsFormat': 'american',
    }
    try:
        response = requests.get(url, params=params)
        return response.json()
    except:
        return []

# --- MATH HELPER FUNCTIONS ---
def get_weighted_metric(name, season_df, l14_df, metric):
    s_val = season_df[season_df['Name'] == name][metric].values
    l_val = l14_df[l14_df['Name'] == name][metric].values
    s_val = s_val[0] if len(s_val) > 0 else 0
    l_val = l_val[0] if len(l_val) > 0 else s_val
    return (s_val * 0.4) + (l_val * 0.6)

def log5_win_prob(p_win_a, p_win_b):
    num = p_win_a - (p_win_a * p_win_b)
    den = p_win_a + p_win_b - (2 * p_win_a * p_win_b)
    return num / den if den != 0 else 0.5

# --- MAIN APP UI ---
st.title("⚾ 2026 Sharp MLB Analytics + Live Odds")

try:
    # Load Data
    p_s, b_s, p_l, b_l = fetch_mlb_data()
    live_odds_data = fetch_live_odds()

    # Sidebar: Manual Selection (Override)
    st.sidebar.header("Manual Matchup Override")
    home_team = st.sidebar.selectbox("Home Team", sorted(p_s['Team'].unique()))
    away_team = st.sidebar.selectbox("Away Team", sorted(p_s['Team'].unique()))
    
    home_pitcher = st.sidebar.selectbox("Home Starter", p_s[p_s['Team'] == home_team]['Name'])
    away_pitcher = st.sidebar.selectbox("Away Starter", p_s[p_s['Team'] == away_team]['Name'])
    
    abs_toggle = st.sidebar.toggle("ABS System (+5% K Rate)", value=True)

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Betting Edge", "📊 Player Props", "💰 Live Market Lines"])

    with tab1:
        st.subheader("Statistical Projections")
        # Logic for Win Prob
        h_fip = get_weighted_metric(home_pitcher, p_s, p_l, 'FIP')
        a_fip = get_weighted_metric(away_pitcher, p_s, p_l, 'FIP')
        
        # Simplified win prob (Relative to league average 4.20 FIP)
        h_exp = 0.5 + ((4.20 - h_fip) * 0.1)
        a_exp = 0.5 + ((4.20 - a_fip) * 0.1)
        win_prob = log5_win_prob(h_exp, a_exp)
        
        col1, col2 = st.columns(2)
        col1.metric(f"{home_team} Win Prob", f"{win_prob:.1%}")
        col2.metric("Projected Total", round((h_fip + a_fip) * 0.95, 2))

    with tab2:
        st.subheader("Player Prop Projections")
        # Strikeout logic
        h_k_rate = get_weighted_metric(home_pitcher, p_s, p_l, 'K%')
        if abs_toggle: h_k_rate *= 1.05
        
        st.write(f"**{home_pitcher} Projected Ks:** {round(h_k_rate * 25, 1)}")
        st.caption("Calculation based on 60/40 recency weighting and ABS impact.")

    with tab3:
        st.subheader("Live Odds from Sportsbooks")
        if not live_odds_data:
            st.warning("No live odds found. Check your API key or wait for market opening.")
        else:
            for game in live_odds_data:
                h = game['home_team']
                a = game['away_team']
                st.write(f"**{a} @ {h}**")
                for book in game['bookmakers'][:3]: # Show top 3 books
                    st.json(book['markets'][0]['outcomes'])

except Exception as e:
    st.error(f"Error loading data: {e}")
