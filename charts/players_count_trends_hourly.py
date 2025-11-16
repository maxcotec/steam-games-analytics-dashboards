import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_all_games(_connection, run_date):
    """Get all unique games for a specific date."""
    try:
        query = """
        SELECT DISTINCT 
            appid,
            MAX(name) as name
        FROM games_cleaned
        WHERE run_date = %s
        GROUP BY appid
        ORDER BY appid
        """
        result = pd.read_sql(query, _connection, params=(run_date,))
        return result
    except Error as e:
        st.error(f"Error fetching games: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_player_count_trends_hourly(_connection, appids):
    """
    Fetch hourly player count trends with growth metrics for selected games.
    Includes run_hour for intra-day analysis.
    """
    if not appids:
        return pd.DataFrame()
    
    try:
        # Convert list to comma-separated string for SQL IN clause
        appids_str = ','.join(map(str, appids))
        
        query = f"""
        SELECT
            appid,
            run_date,
            run_hour,
            current_players,
            LAG(current_players) OVER (PARTITION BY appid ORDER BY run_date, run_hour) AS prev_players,
            current_players - LAG(current_players) OVER (PARTITION BY appid ORDER BY run_date, run_hour) AS player_diff,
            ROUND(
                (current_players - LAG(current_players) OVER (PARTITION BY appid ORDER BY run_date, run_hour)) * 100.0 /
                NULLIF(LAG(current_players) OVER (PARTITION BY appid ORDER BY run_date, run_hour), 0),
                2
            ) AS pct_change
        FROM player_count
        WHERE appid IN ({appids_str})
        ORDER BY appid, run_date, run_hour
        """
        
        result = pd.read_sql(query, _connection)
        return result
    except Error as e:
        st.error(f"Error fetching hourly player count trends: {e}")
        return pd.DataFrame()


def show_player_count_trends_hourly(connection, selected_date):
    """
    Display the Hourly Player count Trends dashboard.
    
    Args:
        connection: MySQL database connection
        selected_date: The run_date to use for fetching top 20 games
    """
    
    # Fetch all games for the selected date
    all_games = fetch_all_games(connection, selected_date)
    
    if all_games.empty:
        st.warning(f"⚠️ No data available for {selected_date}")
        return
    
    # Create game name -> appid mapping
    game_options = {row['name']: row['appid'] for _, row in all_games.iterrows()}
    game_names = sorted(list(game_options.keys()))
    
    # Display date info
    st.markdown(f"**📅 Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Multi-select for game filtering
    st.subheader("📊 Select Games to Display")
    default_games = game_names[:10] if len(game_names) >= 10 else game_names[:5]
    selected_games = st.multiselect(
        f"Choose games to display hourly trends for ({len(game_names)} available games):",
        options=game_names,
        default=default_games,
        key="player_count_hourly_games"
    )
    
    if not selected_games:
        st.info("Please select at least one game to display hourly trends.")
        return
    
    # Convert selected game names back to appids
    selected_appids = [game_options[game] for game in selected_games]
    
    # Fetch trend data for selected games
    trend_data = fetch_player_count_trends_hourly(connection, selected_appids)
    
    if trend_data.empty:
        st.warning("No trend data available for selected games.")
        return
    
    # Add game names to the dataframe for display
    appid_to_name = {v: k for k, v in game_options.items()}
    trend_data['game_name'] = trend_data['appid'].map(appid_to_name)
    
    # Create datetime column combining run_date and run_hour
    trend_data['datetime'] = pd.to_datetime(trend_data['run_date'].astype(str) + ' ' + trend_data['run_hour'].astype(str).str.zfill(2) + ':00:00')
    
    # ===== CHART SECTION =====
    st.markdown("---")
    st.header("📈 Hourly Players Count Trends")
    
    # Create line chart
    fig = go.Figure()
    
    # Add trace for each selected game
    for appid in selected_appids:
        game_data = trend_data[trend_data['appid'] == appid].sort_values('datetime')
        game_name = appid_to_name[appid]
        
        fig.add_trace(go.Scatter(
            x=game_data['datetime'],
            y=game_data['current_players'],
            mode='lines+markers',
            name=game_name,
            hovertemplate=(
                '<b>' + game_name + '</b><br>' +
                'Date: %{x|%Y-%m-%d %H:%M}<br>' +
                'Players: %{y:,}<br>' +
                'Previous: ' + game_data['prev_players'].astype(str).str.replace('.0', '').replace('nan', 'N/A') + '<br>' +
                'Change: ' + game_data['player_diff'].astype(str).str.replace('.0', '') + '<br>' +
                '% Change: ' + game_data['pct_change'].astype(str) + '%<extra></extra>'
            ),
            line=dict(width=2),
            marker=dict(size=5)
        ))
    
    fig.update_layout(
        title=f"Hourly Players Count Trends - {len(selected_games)} Game(s)",
        xaxis_title="DateTime (Hour)",
        yaxis_title="Current Players",
        height=500,
        template="plotly_white",
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12, family="Arial, sans-serif", color='#000000'),
        xaxis=dict(
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000')
        ),
        yaxis=dict(
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000')
        ),
        title_font=dict(size=16, color='#000000'),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="black",
            borderwidth=1
        ),
        margin=dict(b=80, l=80, r=80, t=80)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ===== DATA TABLE SECTION =====
    st.markdown("---")
    st.header("📊 Hourly Counts Data Table")
    
    # Prepare table for display
    display_table = trend_data[['game_name', 'run_date', 'run_hour', 'current_players', 'prev_players', 'player_diff', 'pct_change']].copy()
    display_table.columns = ['Game Name', 'Date', 'Hour', 'Current Players', 'Previous Players', 'Difference', '% Change']
    
    # Sort by game name, date, and hour
    display_table = display_table.sort_values(['Game Name', 'Date', 'Hour'], ascending=[True, False, False])
    
    # Format columns for better readability
    display_table['Hour'] = display_table['Hour'].apply(lambda x: f"{int(x):02d}:00")
    display_table['Current Players'] = display_table['Current Players'].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
    )
    display_table['Previous Players'] = display_table['Previous Players'].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "N/A"
    )
    display_table['Difference'] = display_table['Difference'].apply(
        lambda x: f"{int(x):+,}" if pd.notna(x) else "N/A"
    )
    display_table['% Change'] = display_table['% Change'].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
    )
    
    st.dataframe(display_table, use_container_width=True, hide_index=True)
