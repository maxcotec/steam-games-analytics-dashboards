# 🎮 Steam Game Analytics Dashboard

A Streamlit-based interactive dashboard for analyzing Steam gaming data from MySQL database.

Youtube tutorial Link: https://youtu.be/fuqF60beLdk?si=N8f4nlY34WZnqEmd
![youtube video.png](youtube%20video.png)

## ⚠️ Important note
This repository builds the Gold Layer dashboards and visualizations for Steam games analytics. It depends on the data collected by the Airflow dag in this [airflow-steam-ingestion](https://github.com/maxcotec/airflow-steam-ingestion/) project (Brown and Silver stages).  
Make sure you have run the Airflow DAGs extensively for atleast 3 to 4 days, to gather enough historical and current data before running this dashboard, otherwise some charts may not display meaningful insights.

## About the Code (Generated with Cline AI)
This project was generated using [Cline](https://cline.bot/) — an AI coding agent.
The [full prompt](cline_prompt.docx) used for generation is included in this repository. 

Because AI models are non-deterministic, running the same prompt again may produce different code structures, approaches, or implementations. 
Results also vary based on the LLM provider.

For transparency, this project was built using:
```shell
Provider: Cline API
Plan Model: x-ai/grok-code-fast-1
Act Model: anthropic/claude-haiku-4.5
```
Despite variations, the generated code provides a solid blueprint for building the full workflow end-to-end.

## 📋 What This Does

This dashboard visualizes Steam game analytics including:
- Top trending games by player count
- Price vs review sentiment analysis  
- Developer market performance
- Player count trends over time
- Game momentum (playtime deltas)

Data is sourced from the `steam_games` MySQL database and presented through interactive Plotly charts.

## 🚀 Setup

### Prerequisites
- Python 3.10+
- MySQL 8.0+ with `steam_games` database
- pip

### Installation

```bash
# Clone/navigate to project
cd steam-game-analytics-dashboard

# Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify MySQL
mysql -u root -h localhost steam_games -e "SELECT COUNT(*) FROM games_cleaned;"
```

### Running the Dashboard

```bash
streamlit run dashboard.py
```

Opens at `http://localhost:8501`

## 🔧 Configuration

Edit database credentials in `dashboard.py`:

```python
mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='steam_games'
)
```

## 📁 Project Structure

```
steam-game-analytics-dashboard/
├── dashboard.py              # Main Streamlit app
├── charts/
│   ├── fetch_top_trending_games.py
│   ├── price_vs_review_sentiment.py
│   ├── developer_performance.py
│   ├── players_count_trends.py
│   └── players_count_trends_hourly.py
├── db_connection.py          # DB utilities
├── requirements.txt
└── README.md
```

## ➕ Adding a New Chart
### Add via Cline 
Simply ask Cline to read through the repository first (in plan mode), and once it understands everything, 
proceed with following command prompt;
```shell
Add a new chart;
Release Date vs Performance:
This should show if newer/older games perform differently. capture Game age vs player count analysis (new vs established games)
Should combine release_date from `game_catalog` with current players
```
Once it understands your chart idea, switch to ACT mode and let it build!

### Add manually
1. **Create chart file** in `charts/` folder:
   ```python
   # charts/my_chart.py
   import streamlit as st
   import pandas as pd
   
   @st.cache_data(ttl=300)
   def fetch_chart_data(_connection, run_date):
       query = "SELECT ... FROM games_cleaned WHERE run_date = %s"
       return pd.read_sql(query, _connection, params=(run_date,))
   
   def show_my_chart(connection, selected_date):
       data = fetch_chart_data(connection, selected_date)
       st.header("📊 My Chart")
       # Add your chart code here
   ```

2. **Import in dashboard.py**:
   ```python
   from charts.my_chart import show_my_chart
   ```

3. **Add to chart menu**:
   ```python
   chart_options = {
       ...
       "📊 My Chart": "my_chart",
   }
   ```

4. **Add routing**:
   ```python
   elif chart_key == "my_chart":
       show_my_chart(connection, selected_date)
   ```

## 📦 Dependencies

See `requirements.txt`:
- streamlit
- pandas
- plotly
- mysql-connector-python
- numpy

Install: `pip install -r requirements.txt`

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Database connection failed | Verify MySQL running: `mysql -u root -h localhost` |
| No data for selected date | Check `games_cleaned` has records for that date |
| ModuleNotFoundError | Activate venv and run `pip install -r requirements.txt` |
| Charts not loading | Check console for error messages; may need to refresh browser |

## 📖 Database Schema

Complete schema documented in `DATABASE_README.md` and original `airflow-steam-game-analytics` repo.

Main table: `games_cleaned` with columns like:
- `appid`, `name`, `run_date`, `run_hour`
- `current_players`, `price_usd`
- `positive_reviews`, `negative_reviews`
- `median_playtime_2weeks`, `average_playtime_forever`

---

**Built with**: Streamlit | Plotly | Pandas | MySQL  
**Using**: Cline Bot
