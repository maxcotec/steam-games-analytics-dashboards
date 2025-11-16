import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_top_20_games(_connection, run_date):
    """Get top 20 games by total aggregated players for a specific date (skip hourly records)."""
    try:
        query = """
        SELECT 
            pa.appid,
            gc.name,
            ROUND(SUM(pa.current_players) / 1000) as total_players_k
        FROM player_count pa
        LEFT JOIN games_cleaned gc ON pa.appid = gc.appid
        WHERE pa.run_date = %s
        GROUP BY pa.appid, gc.name
        ORDER BY total_players_k DESC
        LIMIT 20
        """
        result = pd.read_sql(query, _connection, params=(run_date,))
        return result
    except Error as e:
        st.error(f"Error fetching top 20 games: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_player_count_trends(_connection, appids):
    """
    Fetch total aggregated player counts for selected games by date.
    Sums all hourly records per date and calculates growth metrics.
    """
    if not appids:
        return pd.DataFrame()
    
    try:
        # Convert list to comma-separated string for SQL IN clause
        appids_str = ','.join(map(str, appids))
        
        query = f"""
        WITH daily_totals AS (
            SELECT
                appid,
                run_date,
                ROUND(SUM(current_players) / 1000) AS players_k
            FROM player_count
            WHERE appid IN ({appids_str})
            GROUP BY appid, run_date
        )
        SELECT
            appid,
            run_date,
            players_k,
            LAG(players_k) OVER (PARTITION BY appid ORDER BY run_date) AS prev_players_k,
            players_k - LAG(players_k) OVER (PARTITION BY appid ORDER BY run_date) AS player_diff_k,
            ROUND(
                (players_k - LAG(players_k) OVER (PARTITION BY appid ORDER BY run_date)) * 100.0 /
                NULLIF(LAG(players_k) OVER (PARTITION BY appid ORDER BY run_date), 0),
                2
            ) AS pct_change
        FROM daily_totals
        ORDER BY appid, run_date
        """
        
        result = pd.read_sql(query, _connection)
        return result
    except Error as e:
        st.error(f"Error fetching player count trends: {e}")
        return pd.DataFrame()


def show_players_count_trends(connection, selected_date):
    """
    Display the Players Count Trends dashboard.
    
    Args:
        connection: MySQL database connection
        selected_date: The run_date to use for fetching top 20 games
    """
    
    # Fetch top 20 games for the selected date
    top_20_games = fetch_top_20_games(connection, selected_date)
    
    if top_20_games.empty:
        st.warning(f"⚠️ No data available for {selected_date}")
        return
    
    # Create game name -> appid mapping
    game_options = {row['name']: row['appid'] for _, row in top_20_games.iterrows()}
    game_names = sorted(list(game_options.keys()))
    
    # Display date info
    st.markdown(f"**📅 Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Multi-select for game filtering
    st.subheader("📊 Select Games to Display")
    selected_games = st.multiselect(
        "Choose games to display player counts for:",
        options=game_names,
        default=game_names,  # Default: all games selected
        key="players_count_games"
    )
    
    if not selected_games:
        st.info("Please select at least one game to display trends.")
        return
    
    # Convert selected game names back to appids
    selected_appids = [game_options[game] for game in selected_games]
    
    # Fetch trend data for selected games
    trend_data = fetch_player_count_trends(connection, selected_appids)
    
    if trend_data.empty:
        st.warning("No trend data available for selected games.")
        return
    
    # Add game names to the dataframe for display
    appid_to_name = {v: k for k, v in game_options.items()}
    trend_data['game_name'] = trend_data['appid'].map(appid_to_name)
    
    # ===== CHART SECTION =====
    st.markdown("---")
    st.header("📈 Players Count Trends")
    
    # Create line chart
    fig = go.Figure()
    
    # Add trace for each selected game
    for appid in selected_appids:
        game_data = trend_data[trend_data['appid'] == appid].sort_values('run_date')
        game_name = appid_to_name[appid]
        
        fig.add_trace(go.Scatter(
            x=game_data['run_date'],
            y=game_data['players_k'],
            mode='lines+markers',
            name=game_name,
            hovertemplate=(
                '<b>' + game_name + '</b><br>' +
                'Date: %{x}<br>' +
                'Total Players (K): %{y:,}K<br>' +
                'Previous (K): ' + game_data['prev_players_k'].astype(str).str.replace('.0', '').replace('nan', 'N/A') + '<br>' +
                'Change (K): ' + game_data['player_diff_k'].astype(str).str.replace('.0', '') + '<br>' +
                '% Change: ' + game_data['pct_change'].astype(str) + '%<extra></extra>'
            ),
            line=dict(width=2),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=f"Players Count Trends - {len(selected_games)} Game(s)",
        xaxis_title="Date",
        yaxis_title="Total Players (Thousands)",
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
    st.header("📊 Players Count Data Table")
    
    # Prepare table for display
    display_table = trend_data[['game_name', 'run_date', 'players_k', 'prev_players_k', 'player_diff_k', 'pct_change']].copy()
    display_table.columns = ['Game Name', 'Date', 'Total Players (K)', 'Previous (K)', 'Change (K)', '% Change']
    
    # Sort by game name and date
    display_table = display_table.sort_values(['Game Name', 'Date'], ascending=[True, False])
    
    # Format columns for better readability
    display_table['Total Players (K)'] = display_table['Total Players (K)'].apply(
        lambda x: f"{int(x):,}K" if pd.notna(x) else "N/A"
    )
    display_table['Previous (K)'] = display_table['Previous (K)'].apply(
        lambda x: f"{int(x):,}K" if pd.notna(x) else "N/A"
    )
    display_table['Change (K)'] = display_table['Change (K)'].apply(
        lambda x: f"{int(x):+,}K" if pd.notna(x) else "N/A"
    )
    display_table['% Change'] = display_table['% Change'].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
    )
    
    st.dataframe(display_table, use_container_width=True, hide_index=True)
