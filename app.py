import streamlit as st
import anthropic
import requests
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
import random

# Hardcode your API key here
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

st.set_page_config(page_title="Flight Price Monitor", page_icon="✈️", layout="wide")

# Title and description
st.title("✈️ Flight Price Monitor & Travel Agent")
st.markdown("Monitor flight prices, identify peak times, and get personalized travel advice powered by Claude AI")

# Sidebar for inputs
with st.sidebar:
    st.header("Flight Search")
    origin = st.text_input("Origin City", "New York")
    destination = st.text_input("Destination City", "London")
    
    st.header("Weather Settings")
    weather_city = st.text_input("Check Weather For", destination)

# Function to get weather data (OpenWeatherMap free API)
def get_weather(city):
    """Get weather data from OpenWeatherMap free API"""
    try:
        # Using OpenWeatherMap free API
        url = f"https://wttr.in/{city}?format=j1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            return {
                'temp': current['temp_C'],
                'description': current['weatherDesc'][0]['value'],
                'humidity': current['humidity'],
                'wind_speed': current['windspeedKmph']
            }
    except Exception as e:
        st.error(f"Weather API error: {e}")
    return None

# Function to generate mock flight price data
def generate_flight_data(origin, destination, days=30):
    """Generate mock flight price data for demonstration"""
    dates = [(datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    
    # Simulate price patterns with peaks on weekends
    prices = []
    for i, date in enumerate(dates):
        day_of_week = (datetime.now() + timedelta(days=i)).weekday()
        base_price = random.randint(300, 500)
        
        # Higher prices on weekends (Fri, Sat, Sun)
        if day_of_week in [4, 5, 6]:
            base_price += random.randint(100, 200)
        
        prices.append(base_price)
    
    return pd.DataFrame({
        'date': dates,
        'price': prices,
        'day_of_week': [(datetime.now() + timedelta(days=i)).strftime('%A') for i in range(days)]
    })

# Function to call Claude API
def get_travel_advice(origin, destination, flight_data, weather_data):
    """Get travel advice from Claude"""
    
    avg_price = flight_data['price'].mean()
    min_price = flight_data['price'].min()
    max_price = flight_data['price'].max()
    best_day = flight_data.loc[flight_data['price'].idxmin(), 'date']
    
    weather_info = ""
    if weather_data:
        weather_info = f"\n\nCurrent weather in {destination}:\n- Temperature: {weather_data['temp']}°C\n- Conditions: {weather_data['description']}\n- Humidity: {weather_data['humidity']}%\n- Wind Speed: {weather_data['wind_speed']} km/h"
    
    prompt = f"""You are a professional travel agent. Analyze this flight data and provide personalized travel advice.

Flight Route: {origin} to {destination}

Price Analysis:
- Average Price: ${avg_price:.2f}
- Lowest Price: ${min_price:.2f} (on {best_day})
- Highest Price: ${max_price:.2f}
{weather_info}

Please provide:
1. Best time to book based on price patterns
2. Travel tips for this destination
3. Weather considerations
4. Money-saving recommendations

Keep your response conversational and helpful."""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error getting travel advice: {str(e)}"

# Main app layout
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📊 Flight Price Trends")
    
    if st.button("🔍 Search Flights", type="primary"):
        with st.spinner("Analyzing flight prices..."):
            # Generate flight data
            flight_df = generate_flight_data(origin, destination)
            st.session_state['flight_df'] = flight_df
            
            # Create price chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=flight_df['date'],
                y=flight_df['price'],
                mode='lines+markers',
                name='Price',
                line=dict(color='#FF6B6B', width=3),
                marker=dict(size=8)
            ))
            
            fig.update_layout(
                title=f"Flight Prices: {origin} → {destination}",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Peak times analysis
            st.subheader("📈 Peak Times Analysis")
            weekend_avg = flight_df[flight_df['day_of_week'].isin(['Friday', 'Saturday', 'Sunday'])]['price'].mean()
            weekday_avg = flight_df[~flight_df['day_of_week'].isin(['Friday', 'Saturday', 'Sunday'])]['price'].mean()
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Avg Weekend Price", f"${weekend_avg:.2f}")
            col_b.metric("Avg Weekday Price", f"${weekday_avg:.2f}")
            col_c.metric("Best Deal", f"${flight_df['price'].min():.2f}", 
                        delta=f"-${(flight_df['price'].mean() - flight_df['price'].min()):.2f}")

with col2:
    st.header("🌤️ Weather Info")
    weather_data = get_weather(weather_city)
    
    if weather_data:
        st.metric("Temperature", f"{weather_data['temp']}°C")
        st.info(f"**Conditions:** {weather_data['description']}")
        st.text(f"💧 Humidity: {weather_data['humidity']}%")
        st.text(f"💨 Wind: {weather_data['wind_speed']} km/h")
    else:
        st.warning("Weather data unavailable")

# Claude Travel Agent Section
st.header("🤖 AI Travel Agent Advice")

if st.button("💬 Get Personalized Travel Advice"):
    if 'flight_df' in st.session_state:
        with st.spinner("Claude is analyzing your travel options..."):
            advice = get_travel_advice(origin, destination, 
                                      st.session_state['flight_df'], 
                                      weather_data)
            st.markdown(advice)
    else:
        st.warning("Please search for flights first!")

# Footer
st.markdown("---")
st.caption("Powered by Claude AI (Anthropic) • Weather data from wttr.in")
