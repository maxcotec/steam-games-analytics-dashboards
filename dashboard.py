import streamlit as st
import pandas as pd
from mysql.connector import Error
from charts.fetch_top_trending_games import show_top_trending_games
from charts.players_count_trends import show_players_count_trends
from charts.players_count_trends_hourly import show_player_count_trends_hourly
from charts.price_vs_review_sentiment import show_price_vs_review_sentiment
from charts.developer_performance import show_developer_performance
from db_connection import get_db_connection

# Page configuration
st.set_page_config(
    page_title="Steam Game Analytics Dashboard",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ===== QUERY FUNCTIONS =====
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_available_dates(_connection):
    """Get all available run_dates, sorted newest first."""
    try:
        query = "SELECT DISTINCT run_date FROM games_cleaned ORDER BY run_date DESC"
        result = pd.read_sql(query, _connection)
        return result['run_date'].tolist() if not result.empty else []
    except Error as e:
        st.error(f"Error fetching dates: {e}")
        return []


# ===== PAGE LAYOUT =====

# Get database connection
connection = get_db_connection()

if connection is None:
    st.error("❌ Failed to connect to database. Please check MySQL is running.")
    st.stop()

# Fetch available dates
available_dates = fetch_available_dates(connection)

if not available_dates:
    st.error("❌ No data available in database.")
    st.stop()

# Main title
st.title("🎮 Steam Game Analytics Dashboard")
st.markdown("---")

# ===== SIDEBAR NAVIGATION =====
with st.sidebar:
    st.header("📊 Dashboard Charts")
    st.markdown("---")
    
    # Chart selection
    chart_options = {
        "🔥 Top Trending Games": "top_trending_games",
        "📈 Players Count Trends": "players_count_trends",
        "🕐 Hourly Counts Trends": "players_count_trends_hourly",
        "💰⭐ Price vs Review Sentiment": "price_vs_review_sentiment",
        "🏢 Developer Performance": "developer_performance",
        "🏢 Owner vs Active Player Ratio": "owners_vs_active_players_ratio",
        "🏢 Release Date vs Performance": "release_date_vs_performance"
    }
    
    selected_chart = st.radio(
        "Select Chart:",
        options=list(chart_options.keys()),
        index=0
    )
    
    st.markdown("---")
    st.header("⚙️ Settings")
    
    # Date selection
    selected_date = st.selectbox(
        "Select Date:",
        available_dates,
        format_func=lambda x: x.strftime("%Y-%m-%d") if hasattr(x, 'strftime') else str(x)
    )
    
    # Top N games selector (applicable to most charts)
    top_n = st.slider(
        "Number of Games to Display:",
        min_value=5,
        max_value=50,
        value=20,
        step=5
    )

# ===== MAIN CONTENT AREA =====

# Map chart selection to chart function
chart_key = chart_options[selected_chart]

if chart_key == "top_trending_games":
    show_top_trending_games(connection, selected_date, top_n)

elif chart_key == "players_count_trends":
    show_players_count_trends(connection, selected_date)

elif chart_key == "players_count_trends_hourly":
    show_player_count_trends_hourly(connection, selected_date)

elif chart_key == "price_vs_review_sentiment":
    show_price_vs_review_sentiment(connection, selected_date)

elif chart_key == "developer_performance":
    show_developer_performance(connection, selected_date)

elif chart_key == "owners_vs_active_players_ratio":
    st.info("⭐ Analysis coming soon...")
    st.markdown("Coming soon.")

elif chart_key == "release_date_vs_performance":
    st.info("⏱️ Analysis coming soon...")
    st.markdown("Coming soon.")

# ===== FOOTER =====
st.markdown("---")
st.markdown("<p style='text-align: center; color: #666; font-size: 11px;'>Steam Game Analytics Dashboard</p>", unsafe_allow_html=True)
