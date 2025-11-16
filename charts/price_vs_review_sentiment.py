import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error
import numpy as np


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_price_sentiment_data(_connection, run_date):
    """Fetch price vs review sentiment data for a specific date."""
    try:
        query = """
        SELECT
            appid,
            MAX(name) as name,
            MAX(price_usd) as price_usd,
            SUM(positive_reviews) as positive_reviews,
            SUM(negative_reviews) as negative_reviews,
            MAX(current_players) as current_players
        FROM games_cleaned
        WHERE run_date = %s
            AND price_usd > 0
        GROUP BY appid
        HAVING (SUM(positive_reviews) + SUM(negative_reviews)) >= 10
        ORDER BY price_usd DESC
        """
        result = pd.read_sql(query, _connection, params=(run_date,))
        return result
    except Error as e:
        st.error(f"Error fetching price sentiment data: {e}")
        return pd.DataFrame()


def show_price_vs_review_sentiment(connection, selected_date):
    """
    Display the Price vs Review Sentiment analysis.
    
    Args:
        connection: MySQL database connection
        selected_date: The run_date to display data for
    """
    
    # Fetch data
    data = fetch_price_sentiment_data(connection, selected_date)
    
    if data.empty:
        st.warning(f"⚠️ No data available for {selected_date}")
        return
    
    # Display date info
    st.markdown(f"**📅 Date:** {selected_date.strftime('%Y-%m-%d')}")
    st.markdown("---")
    
    # Calculate sentiment metrics
    data['total_reviews'] = data['positive_reviews'] + data['negative_reviews']
    data['sentiment_pct'] = (data['positive_reviews'] / data['total_reviews'] * 100).round(1)
    
    # ===== ANALYSIS DESCRIPTION =====
    st.info(
        """
        **What This Analysis Shows:**
        
        This scatter plot reveals the relationship between game pricing and community sentiment:
        - **X-Axis**: Game price in USD
        - **Y-Axis**: Positive review percentage (0-100%)
        - **Bubble Size**: Total number of reviews (larger = more reliable data)
        
        **What is Sentiment %?**
        Sentiment % = (Positive Reviews / Total Reviews) × 100
        
        Higher percentage = more players recommend the game. For example:
        - 90% = 9 out of 10 players recommend (highly positive)
        - 50% = Split opinion (mixed reception)
        - 20% = Most players don't recommend (negative)
        
        **Note**: Larger bubbles (more reviews) are generally more reliable indicators than smaller bubbles.
        
        **Valuable Insights:**
        - **Top-Left**: Bargain games (low price + high sentiment) - great value picks
        - **Top-Right**: Premium games (high price + high sentiment) - quality premium titles
        - **Bottom-Left**: Budget games (low price + low sentiment) - potentially problematic
        - **Bottom-Right**: Overpriced games (high price + low sentiment) - poor value
        
        **Filter**: Only games with ≥10 reviews are shown for data reliability
        """
    )
    
    st.markdown("---")
    
    # ===== SCATTER PLOT SECTION =====
    st.header("💰⭐ Price vs Review Sentiment")
    
    # Create scatter plot
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data['price_usd'],
        y=data['sentiment_pct'],
        mode='markers',
        marker=dict(
            size=data['total_reviews'].apply(lambda x: max(5, min(25, 5 + np.log1p(x)))),  # Logarithmic scale for bubble size
            color=data['sentiment_pct'],
            colorscale='RdYlGn',  # Red (bad) to Yellow (ok) to Green (good)
            showscale=True,
            colorbar=dict(title="Sentiment %"),
            line=dict(width=1, color='white'),
            opacity=0.8
        ),
        text=[
            f"<b>{name}</b><br>" +
            f"Price: ${price:.2f}<br>" +
            f"Sentiment: {sentiment:.1f}%<br>" +
            f"Positive Reviews: {pos:,}<br>" +
            f"Negative Reviews: {neg:,}<br>" +
            f"Total Reviews: {total:,}<br>" +
            f"Current Players: {players:,}"
            for name, price, sentiment, pos, neg, total, players
            in zip(
                data['name'], data['price_usd'], data['sentiment_pct'],
                data['positive_reviews'], data['negative_reviews'],
                data['total_reviews'], data['current_players']
            )
        ],
        hovertemplate='%{text}<extra></extra>',
        name='Games'
    ))
    
    fig.update_layout(
        title="Price vs Review Sentiment Analysis",
        xaxis_title="Price (USD)",
        yaxis_title="Positive Review Percentage (%)",
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
            gridcolor='#f0f0f0',
            range=[0, 105]  # 0-100% with some padding
        ),
        title_font=dict(size=16, color='#000000'),
        margin=dict(b=80, l=80, r=80, t=80)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # ===== STATISTICS SECTION =====
    st.markdown("---")
    st.header("📊 Market Insights")
    st.caption("📌 Showing paid games with ≥10 total reviews.")
    
    # Calculate insights
    avg_sentiment = data['sentiment_pct'].mean()
    avg_price = data['price_usd'].mean()
    
    # Identify bargains (high sentiment + low price)
    bargain_threshold_sentiment = data['sentiment_pct'].quantile(0.75)
    bargain_threshold_price = data['price_usd'].quantile(0.25)
    bargains = data[
        (data['sentiment_pct'] >= bargain_threshold_sentiment) &
        (data['price_usd'] <= bargain_threshold_price)
    ]
    
    # Identify overpriced (low sentiment + high price)
    overpriced_threshold_sentiment = data['sentiment_pct'].quantile(0.25)
    overpriced_threshold_price = data['price_usd'].quantile(0.75)
    overpriced = data[
        (data['sentiment_pct'] <= overpriced_threshold_sentiment) &
        (data['price_usd'] >= overpriced_threshold_price)
    ]
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 Total Games", len(data))
    with col2:
        st.metric("⭐ Avg Sentiment", f"{avg_sentiment:.1f}%")
    with col3:
        st.metric("💰 Avg Price", f"${avg_price:.2f}")
    with col4:
        st.metric("🔥 Total Reviews", f"{data['total_reviews'].sum():,}")
    
    st.markdown("---")
    
    # Bargain games section
    st.subheader("🎁 Bargain Picks")
    st.caption("Games in top 25% sentiment with prices in bottom 25% - exceptional value recommendations")
    if not bargains.empty:
        bargain_display = bargains[['name', 'price_usd', 'sentiment_pct', 'total_reviews']].copy()
        bargain_display = bargain_display.sort_values('sentiment_pct', ascending=False).head(10)
        bargain_display.columns = ['Game Name', 'Price', 'Sentiment %', 'Total Reviews']
        bargain_display['Price'] = bargain_display['Price'].apply(lambda x: f"${x:.2f}")
        bargain_display['Sentiment %'] = bargain_display['Sentiment %'].apply(lambda x: f"{x:.1f}%")
        bargain_display['Total Reviews'] = bargain_display['Total Reviews'].apply(lambda x: f"{int(x):,}")
        st.dataframe(bargain_display, use_container_width=True, hide_index=True)
    else:
        st.info("No bargain picks found in current data.")
    
    st.markdown("---")
    
    # Overpriced games section
    st.subheader("⚠️ Potentially Overpriced")
    st.caption("Games in bottom 25% sentiment with prices in top 25% - may indicate poor value for money")
    if not overpriced.empty:
        overpriced_display = overpriced[['name', 'price_usd', 'sentiment_pct', 'total_reviews']].copy()
        overpriced_display = overpriced_display.sort_values('price_usd', ascending=False).head(10)
        overpriced_display.columns = ['Game Name', 'Price', 'Sentiment %', 'Total Reviews']
        overpriced_display['Price'] = overpriced_display['Price'].apply(lambda x: f"${x:.2f}")
        overpriced_display['Sentiment %'] = overpriced_display['Sentiment %'].apply(lambda x: f"{x:.1f}%")
        overpriced_display['Total Reviews'] = overpriced_display['Total Reviews'].apply(lambda x: f"{int(x):,}")
        st.dataframe(overpriced_display, use_container_width=True, hide_index=True)
    else:
        st.info("No overpriced games found in current data.")
