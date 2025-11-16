import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_developer_performance_data(_connection, run_date):
    """Fetch developer performance metrics for a specific date."""
    try:
        query = """
        SELECT
            CASE 
                WHEN gc.appid = 1938090 THEN 'Infinity Ward'
                ELSE gc.developer
            END as developer,
            SUM(g.current_players) as total_players,
            COUNT(DISTINCT gc.appid) as game_count,
            ROUND(AVG(gc.price), 2) as avg_price,
            COUNT(DISTINCT gc.appid) as unique_games,
            ROUND(SUM(g.positive_reviews) / (SUM(g.positive_reviews) + SUM(g.negative_reviews)) * 100, 1) as avg_sentiment
        FROM game_catalog gc
        LEFT JOIN games_cleaned g ON gc.appid = g.appid AND g.run_date = %s
        WHERE gc.developer IS NOT NULL AND gc.developer != ''
        GROUP BY CASE 
                    WHEN gc.appid = 1938090 THEN 'Infinity Ward'
                    ELSE gc.developer
                 END
        HAVING SUM(g.current_players) > 0
        ORDER BY total_players DESC
        LIMIT 20
        """
        result = pd.read_sql(query, _connection, params=(run_date,))
        return result
    except Error as e:
        st.error(f"Error fetching developer performance data: {e}")
        return pd.DataFrame()


def show_developer_performance(connection, selected_date):
    """
    Display the Developer Performance analysis.
    
    Args:
        connection: MySQL database connection
        selected_date: The run_date to display data for
    """
    
    # Fetch data
    data = fetch_developer_performance_data(connection, selected_date)
    
    if data.empty:
        st.warning(f"⚠️ No data available for {selected_date}")
        return
    
    # Display date info
    st.markdown(f"**📅 Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Calculate market metrics
    total_market_players = data['total_players'].sum()
    data['market_share'] = (data['total_players'] / total_market_players * 100).round(1)
    
    # Fill None values in avg_price to prevent color mapping errors
    data['avg_price'] = data['avg_price'].fillna(0)
    
    # ===== ANALYSIS DESCRIPTION =====
    st.info(
        """
        **What This Analysis Shows:**
        
        This chart reveals which game developers dominate the Steam marketplace by player engagement:
        - **Bar Length**: Total player count across all games by each developer
        - **Game Count**: Number of games published by each developer
        - **Market Share %**: Percentage of total players this developer captures
        - **Avg Price**: Average price of games from this developer
        - **Sentiment**: Average positive review percentage
        
        **Key Questions Answered:**
        - Which developers have the most engaged player bases?
        - Do premium or budget developers lead the market?
        - How many games does it take for a developer to dominate?
        - Which developers maintain high review sentiment?
        
        **Filter**: Only showing developers with active games (≥1 player)
        """
    )
    
    st.markdown("---")
    
    # ===== BAR CHART SECTION =====
    st.header("🏢 Developer Performance Ranking")
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=data['developer'],
        x=data['total_players'] / 1000,  # Convert to thousands
        orientation='h',
        marker=dict(
            color=data['avg_price'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Avg Price ($)"),
            line=dict(width=1, color='white')
        ),
        text=[f"{int(p/1000):,}K ({s:.1f}%)" for p, s in zip(data['total_players'], data['market_share'])],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>' +
                     'Total Players: %{x:,.0f}K<br>' +
                     'Market Share: <extra></extra>',
        name='Players'
    ))
    
    fig.update_layout(
        title="Top Developers by Total Player Count",
        xaxis_title="Total Players (Thousands)",
        yaxis_title="Developer",
        height=600,
        template='plotly_white',
        hovermode='closest',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(size=12, family="Arial, sans-serif", color='#000000'),
        xaxis=dict(
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000'),
            gridcolor='#f0f0f0'
        ),
        yaxis=dict(
            tickfont=dict(size=11, color='#000000'),
            title_font=dict(size=12, color='#000000'),
            autorange='reversed'
        ),
        title_font=dict(size=16, color='#000000'),
        margin=dict(b=80, l=200, r=100, t=80)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ===== STATISTICS SECTION =====
    st.markdown("---")
    st.header("📊 Market Insights")
    st.caption(f"📌 Analyzing {len(data)} developers with games on Steam")
    
    # Calculate insights
    top_3_share = data['market_share'].head(3).sum()
    avg_games_per_dev = data['game_count'].mean()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏢 Total Developers", len(data))
    with col2:
        st.metric("🎮 Market Leader", data.iloc[0]['developer'] if not data.empty else "N/A")
    with col3:
        st.metric("👑 Top 3 Control", f"{top_3_share:.1f}%")
    with col4:
        st.metric("📈 Avg Games/Dev", f"{avg_games_per_dev:.1f}")
    
    st.markdown("---")
    
    # Market leaders section
    st.subheader("👑 Market Leaders (Top 5)")
    st.caption("Developers with the largest player bases and market dominance")
    
    leaders = data.head(5)[['developer', 'total_players', 'game_count', 'avg_price', 'market_share', 'avg_sentiment']].copy()
    leaders.columns = ['Developer', 'Total Players', 'Games', 'Avg Price', 'Market Share %', 'Avg Sentiment %']
    leaders['Total Players'] = leaders['Total Players'].apply(lambda x: f"{int(x/1000):,}K")
    leaders['Avg Price'] = leaders['Avg Price'].apply(lambda x: f"${x:.2f}")
    leaders['Market Share %'] = leaders['Market Share %'].apply(lambda x: f"{x:.1f}%")
    leaders['Avg Sentiment %'] = leaders['Avg Sentiment %'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    
    st.dataframe(leaders, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Detailed comparison table
    st.subheader("📋 Detailed Developer Comparison")
    st.caption("Full metrics for all analyzed developers - sorted by player count")
    
    comparison = data[['developer', 'total_players', 'game_count', 'avg_price', 'market_share', 'avg_sentiment']].copy()
    comparison.columns = ['Developer', 'Total Players', 'Games Published', 'Avg Price', 'Market Share %', 'Avg Sentiment %']
    comparison['Total Players'] = comparison['Total Players'].apply(lambda x: f"{int(x/1000):,}K")
    comparison['Avg Price'] = comparison['Avg Price'].apply(lambda x: f"${x:.2f}")
    comparison['Market Share %'] = comparison['Market Share %'].apply(lambda x: f"{x:.1f}%")
    comparison['Avg Sentiment %'] = comparison['Avg Sentiment %'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
    
    st.dataframe(comparison, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Market concentration analysis
    st.subheader("📈 Market Concentration Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        concentration_data = data.head(10)[['developer', 'market_share']].copy()
        fig_pie = go.Figure(data=[go.Pie(
            labels=concentration_data['developer'],
            values=concentration_data['market_share'],
            hole=0.3,
            hovertemplate='<b>%{label}</b><br>Market Share: %{value:.1f}%<extra></extra>'
        )])
        fig_pie.update_layout(
            title="Top 10 Developers Market Share",
            height=500,
            template='plotly_white'
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Cumulative market share
        cumulative_share = data['market_share'].cumsum().head(10)
        fig_cumsum = go.Figure()
        fig_cumsum.add_trace(go.Scatter(
            y=data['developer'].head(10),
            x=cumulative_share,
            mode='lines+markers',
            fill='tozeroy',
            name='Cumulative Share',
            marker=dict(size=8, color='#636EFA'),
            line=dict(width=2)
        ))
        fig_cumsum.update_layout(
            title="Cumulative Market Share Concentration",
            xaxis_title="Cumulative Market Share %",
            yaxis_title="Developer",
            height=500,
            template='plotly_white',
            hovermode='closest',
            yaxis=dict(autorange='reversed')
        )
        st.plotly_chart(fig_cumsum, use_container_width=True)
