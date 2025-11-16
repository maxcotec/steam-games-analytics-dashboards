import mysql.connector
from mysql.connector import Error
import pandas as pd
import streamlit as st

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'steam_games'
}

@st.cache_resource
def get_db_connection():
    """Create and return a MySQL database connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

def fetch_games_cleaned(connection, run_date=None):
    """Fetch data from games_cleaned table."""
    try:
        query = "SELECT * FROM games_cleaned"
        if run_date:
            query += f" WHERE run_date = '{run_date}'"
        query += " ORDER BY current_players DESC"

        df = pd.read_sql(query, connection)
        return df
    except Error as e:
        st.error(f"Error fetching games_cleaned data: {e}")
        return pd.DataFrame()

def fetch_latest_run_date(connection):
    """Get the latest run_date from the database."""
    try:
        query = "SELECT DISTINCT run_date FROM games_cleaned ORDER BY run_date DESC LIMIT 1"
        result = pd.read_sql(query, connection)
        if not result.empty:
            return result.iloc[0]['run_date']
        return None
    except Error as e:
        st.error(f"Error fetching latest run_date: {e}")
        return None

def fetch_available_dates(connection):
    """Get all available run_dates for filtering."""
    try:
        query = "SELECT DISTINCT run_date FROM games_cleaned ORDER BY run_date DESC"
        result = pd.read_sql(query, connection)
        return result['run_date'].tolist() if not result.empty else []
    except Error as e:
        st.error(f"Error fetching available dates: {e}")
        return []

def fetch_player_count_trend(connection, appid, days=30):
    """Fetch player activity trend for a specific game."""
    try:
        query = f"""
        SELECT run_date, current_players, appid 
        FROM games_cleaned 
        WHERE appid = {appid} 
        AND run_date >= DATE_SUB(CURDATE(), INTERVAL {days} DAY)
        ORDER BY run_date ASC
        """
        df = pd.read_sql(query, connection)
        return df
    except Error as e:
        st.error(f"Error fetching player activity trend: {e}")
        return pd.DataFrame()

def fetch_game_details(connection, appid):
    """Fetch detailed information for a specific game."""
    try:
        query = f"""
        SELECT * FROM games_cleaned 
        WHERE appid = {appid} 
        ORDER BY run_date DESC 
        LIMIT 1
        """
        df = pd.read_sql(query, connection)
        return df
    except Error as e:
        st.error(f"Error fetching game details: {e}")
        return pd.DataFrame()

def get_summary_stats(connection, run_date=None):
    """Get summary statistics for the dashboard."""
    try:
        if run_date:
            where_clause = f"WHERE run_date = '{run_date}'"
        else:
            where_clause = ""

        query = f"""
        SELECT 
            COUNT(DISTINCT appid) as total_games,
            SUM(current_players) as total_current_players,
            AVG(price_usd) as avg_price,
            MAX(current_players) as max_current_players,
            SUM(positive_reviews) as total_positive_reviews,
            SUM(negative_reviews) as total_negative_reviews
        FROM games_cleaned
        {where_clause}
        """

        result = pd.read_sql(query, connection)
        return result.iloc[0].to_dict() if not result.empty else {}
    except Error as e:
        st.error(f"Error fetching summary stats: {e}")
        return {}
