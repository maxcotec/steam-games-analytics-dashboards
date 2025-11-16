import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_top_trending_games_data(_connection, run_date, limit=20):
    """Fetch top trending games for a specific date."""
    try:
        query = """
        SELECT
            appid,
            name,
            ROUND(AVG(current_players) / 1000) AS avg_players_k,
            ROUND(AVG(positive_reviews) / 1000) AS avg_positive_reviews_k,
            ROUND(AVG(negative_reviews) / 1000) AS avg_negative_reviews_k,
            MAX(price_usd) AS max_price_usd
        FROM games_cleaned
        WHERE run_date = %s
        GROUP BY appid, name
        ORDER BY avg_players_k DESC
        LIMIT %s;
        """
        result = pd.read_sql(query, _connection, params=(run_date, limit))
        return result
    except Error as e:
        st.error(f"Error fetching trending games: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_top_100_hourly(_connection, run_date, run_hour):
    """Fetch top 100 games for a specific hour."""
    try:
        query = """
        SELECT DISTINCT appid, name
        FROM trending_games
        WHERE run_date = %s AND run_hour = %s
        LIMIT 100
        """
        result = pd.read_sql(query, _connection, params=(run_date, run_hour))
        return set(result['appid'].tolist()) if not result.empty else set()
    except Error as e:
        st.error(f"Error fetching top 100 hourly games: {e}")
        return set()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_top_100_movement_data(_connection, run_date, run_hour):
    """Fetch movement analysis for top 100 games between current and previous hour."""
    try:
        # Get current hour's top 100
        current_query = """
        SELECT appid, name
        FROM trending_games
        WHERE run_date = %s AND run_hour = %s
        LIMIT 100
        """
        current_result = pd.read_sql(current_query, _connection, params=(run_date, run_hour))
        current_appids = set(current_result['appid'].tolist()) if not current_result.empty else set()
        
        # Get previous hour's top 100
        prev_hour = run_hour - 1
        prev_date = run_date
        
        if prev_hour < 0:
            # If hour is 0, get previous day's hour 23
            prev_hour = 23
            prev_date = (datetime.strptime(str(run_date), '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        prev_query = """
        SELECT appid, name
        FROM trending_games
        WHERE run_date = %s AND run_hour = %s
        LIMIT 100
        """
        prev_result = pd.read_sql(prev_query, _connection, params=(prev_date, prev_hour))
        prev_appids = set(prev_result['appid'].tolist()) if not prev_result.empty else set()
        
        # Categorize movements
        rising = current_appids - prev_appids  # New entries
        holding = current_appids & prev_appids  # Stayers
        falling = prev_appids - current_appids  # Removals
        
        return {
            'rising': rising,
            'holding': holding,
            'falling': falling,
            'current_df': current_result,
            'prev_df': prev_result
        }
    except Error as e:
        st.error(f"Error fetching movement data: {e}")
        return {'rising': set(), 'holding': set(), 'falling': set(), 'current_df': pd.DataFrame(), 'prev_df': pd.DataFrame()}


def show_top_trending_games(connection, selected_date, top_n=20):
    """
    Display the Top Trending Games dashboard.
    
    Args:
        connection: MySQL database connection
        selected_date: The run_date to display data for
        top_n: Number of games to display (5-50)
    """
    _TOTAL_GAMES_TO_DISPLAY = 30
    _RISING_THRESHOLD = 200
    _FALLING_THRESHOLD = -200

    # Fetch data
    games_data = fetch_top_trending_games_data(connection, selected_date, top_n)
    
    if games_data.empty:
        st.warning(f"⚠️ No data available for {selected_date}")
        return
    
    # Display date info
    st.markdown(f"**📅 Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # ===== CHART SECTION =====
    st.header("🔥 Top Trending Games")
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=games_data['name'],
            y=games_data['avg_players_k'],
            marker=dict(
                color=games_data['avg_players_k'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Avg Players (K)")
            ),
            text=games_data['avg_players_k'].apply(lambda x: f"{int(x):,}K"),
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>Avg Players: %{y:,}K<extra></extra>',
            marker_line_width=0
        )
    ])
    
    fig.update_layout(
        title=f"Top {top_n} Games by Average Players",
        xaxis_title="Game Name",
        yaxis_title="Average Players (Thousands)",
        height=500,
        template="plotly_white",
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12, family="Arial, sans-serif", color='#000000'),
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000')
        ),
        yaxis=dict(
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000')
        ),
        title_font=dict(size=16, color='#000000'),
        margin=dict(b=120, l=80, r=80, t=80)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ===== GAME MOMENTUM ANALYSIS (Playtime Delta - Two Time Windows) =====
    st.markdown("---")
    st.header("📊 Game Momentum Analysis (Morning vs Afternoon)")
    
    # Description of the analysis
    st.info(
        """
        **What This Analysis Captures:**
        
        This analysis compares median playtime changes between two time periods in a single day:
        - **Morning Window (1:00 AM - 12:00 PM)**: Early activity period
        - **Afternoon Window (1:00 PM - 11:00 PM)**: Peak activity period
        
        **Classification Thresholds:**
        - 🚀 **Rising**: Games gaining playtime momentum (+200 or more minutes change)
        - 📉 **Falling**: Games losing playtime momentum (-200 or more minutes change)
        - ⚖️ **Stable**: Games with consistent playtime (-200 to +200 minutes range)
        
        **Key Insights**: Games with large positive deltas are gaining player engagement throughout the day, 
        while negative deltas indicate declining interest. This helps identify emerging hits and fading titles.
        """
    )
    
    st.markdown("---")
    
    # Fixed time windows
    morning_start = 1
    morning_end = 12
    afternoon_start = 13
    afternoon_end = 23
    
    # Fetch momentum data
    momentum_query = """
    WITH morning AS (
        SELECT appid, AVG(median_playtime_2weeks) as avg_morning, MAX(name) as name
        FROM games_cleaned
        WHERE run_date = %s AND run_hour BETWEEN %s AND %s
        GROUP BY appid
    ),
    afternoon AS (
        SELECT appid, AVG(median_playtime_2weeks) as avg_afternoon
        FROM games_cleaned
        WHERE run_date = %s AND run_hour BETWEEN %s AND %s
        GROUP BY appid
    )
    SELECT
        m.appid,
        m.name,
        m.avg_morning,
        COALESCE(a.avg_afternoon, 0) as avg_afternoon,
        (a.avg_afternoon - m.avg_morning) as delta
    FROM morning m
    LEFT JOIN afternoon a ON m.appid = a.appid
    ORDER BY delta DESC
    """
    
    try:
        # # Debug: Print rendered query
        # rendered_query = momentum_query % (
        #     str(selected_date), morning_start, morning_end,
        #     str(selected_date), afternoon_start, afternoon_end
        # )
        # with st.expander("📝 Debug: SQL Query"):
        #     st.code(rendered_query, language="sql")
        
        momentum_df = pd.read_sql(
            momentum_query,
            connection,
            params=(selected_date, morning_start, morning_end, selected_date, afternoon_start, afternoon_end)
        )
        
        if momentum_df.empty:
            st.warning("No momentum data available.")
        else:
            # Fill NaN values with 0 to avoid comparison errors
            momentum_df['delta'] = momentum_df['delta'].fillna(0)
            
            # Classify games by momentum
            momentum_df['status'] = momentum_df['delta'].apply(
                lambda x: '🚀 Rising' if pd.notna(x) and x > _RISING_THRESHOLD else '📉 Falling' if pd.notna(x) and x < _FALLING_THRESHOLD else '⚖️ Stable'
            )
            
            # Get counts
            rising = len(momentum_df[momentum_df['status'] == '🚀 Rising'])
            falling = len(momentum_df[momentum_df['status'] == '📉 Falling'])
            stable = len(momentum_df[momentum_df['status'] == '⚖️ Stable'])
            
            # Display summary metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🚀 Rising Games", rising)
            with col2:
                st.metric("⚖️ Stable Games", stable)
            with col3:
                st.metric("📉 Falling Games", falling)
            
            st.markdown("---")
            
            # Create tabs for different views
            tab1, tab2, tab3 = st.tabs(["🚀 Rising", "⚖️ Stable", "📉 Falling"])
            
            with tab1:
                rising_games = momentum_df[momentum_df['status'] == '🚀 Rising'].head(_TOTAL_GAMES_TO_DISPLAY)
                if not rising_games.empty:
                    rising_display = rising_games[['name', 'avg_morning', 'avg_afternoon', 'delta']].copy()
                    rising_display.columns = ['Game Name', 'Morning (1-12h)', 'Afternoon (13-23h)', 'Delta']
                    rising_display['Morning (1-12h)'] = rising_display['Morning (1-12h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    rising_display['Afternoon (13-23h)'] = rising_display['Afternoon (13-23h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    rising_display['Delta'] = rising_display['Delta'].apply(lambda x: f"+{int(x):,}" if pd.notna(x) else "N/A")
                    st.dataframe(rising_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No rising games in this period.")
            
            with tab2:
                stable_games = momentum_df[momentum_df['status'] == '⚖️ Stable'].head(_TOTAL_GAMES_TO_DISPLAY)
                if not stable_games.empty:
                    stable_display = stable_games[['name', 'avg_morning', 'avg_afternoon', 'delta']].copy()
                    stable_display.columns = ['Game Name', 'Morning (1-12h)', 'Afternoon (13-23h)', 'Delta']
                    stable_display['Morning (1-12h)'] = stable_display['Morning (1-12h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    stable_display['Afternoon (13-23h)'] = stable_display['Afternoon (13-23h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    stable_display['Delta'] = stable_display['Delta'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    st.dataframe(stable_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No stable games in this period.")
            
            with tab3:
                falling_games = momentum_df[momentum_df['status'] == '📉 Falling'].head(_TOTAL_GAMES_TO_DISPLAY)
                if not falling_games.empty:
                    falling_display = falling_games[['name', 'avg_morning', 'avg_afternoon', 'delta']].copy()
                    falling_display.columns = ['Game Name', 'Morning (1-12h)', 'Afternoon (13-23h)', 'Delta']
                    falling_display['Morning (1-12h)'] = falling_display['Morning (1-12h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    falling_display['Afternoon (13-23h)'] = falling_display['Afternoon (13-23h)'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    falling_display['Delta'] = falling_display['Delta'].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "N/A")
                    st.dataframe(falling_display, use_container_width=True, hide_index=True)
                else:
                    st.info("No falling games in this period.")
    except Exception as e:
        st.error(f"Error calculating momentum: {e}")
