import streamlit as st
from streamlit_lottie import st_lottie
import json
from geopy.geocoders import Nominatim
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import pandas as pd
import plotly.graph_objects as go

# ----------------- Gemini Setup -----------------
genai.configure(api_key="AIzaSyA28UIrLIfgi6fTATjQTZueAKpSe-P2FDo")
model = genai.GenerativeModel("models/gemini-1.5-flash")

# ----------------- Load Local Lottie Animation -----------------
def load_lottie_file(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

hello_animation = load_lottie_file("hello_animation.json")  # 👈 Must be in same folder

# ----------------- Utility Functions -----------------
def get_coordinates(location_name):
    geolocator = Nominatim(user_agent="farm-advisor")
    location = geolocator.geocode(location_name)
    if location:
        return location.latitude, location.longitude
    return None, None

def get_past_weather(lat, lon):
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=9)
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
        f"&timezone=auto"
    )
    r = requests.get(url)
    return r.json().get("daily", {})

def get_future_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
        f"&forecast_days=10&timezone=auto"
    )
    r = requests.get(url)
    return r.json().get("daily", {})

def get_soil_data(lat, lon):
    try:
        # Sample static soil data. Replace with actual API call if available.
        return {
            "phh2o": 6.5,
            "ocd": 25.3,
            "sand": 45,
            "silt": 30,
            "clay": 25,
            "cec": 18.2
        }
    except:
        return None

def safe_avg(values):
    clean = [v for v in values if v is not None]
    return sum(clean) / len(clean) if clean else 0

def safe_sum(values):
    return sum([v for v in values if v is not None])

def get_advice(location, past_weather, future_weather, soil, user_query, language):
    prompt = f"""
You are a smart agriculture advisor helping a farmer in {location}.
Speak in {language}. Respond in a short, simple, farmer-friendly tone.

**Past 10 Days:**
- Rain: {safe_sum(past_weather.get('precipitation_sum', [])):.1f} mm
- Avg Max Temp: {safe_avg(past_weather.get('temperature_2m_max', [])):.1f}°C
- Avg Min Temp: {safe_avg(past_weather.get('temperature_2m_min', [])):.1f}°C

**Next 10 Days (Forecast):**
- Rain: {safe_sum(future_weather.get('precipitation_sum', [])):.1f} mm
- Avg Max Temp: {safe_avg(future_weather.get('temperature_2m_max', [])):.1f}°C
- Avg Min Temp: {safe_avg(future_weather.get('temperature_2m_min', [])):.1f}°C

Soil:
- pH: {soil['phh2o']}
- Organic Carbon: {soil['ocd']}
- Texture: {soil['sand']}% sand, {soil['silt']}% silt, {soil['clay']}% clay

Farmer's Question: '{user_query}'
"""
    response = model.generate_content(prompt)
    return response.text.strip()

# ----------------- Streamlit UI -----------------
# ----------------- Professional Header Layout -----------------
st.markdown("""
    <div style='display: flex; justify-content: center; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;'>
        <div style='flex-grow: 1;'>
            <h1 style='font-size: 2.2rem; font-weight: 700; align-items: center;'>🌾 AI Agent for Smart Agriculture</h1>
            <p style='font-size: 1.2rem; align-items: center;'>👨🏻‍🌾 Get farming advice using AI + weather + soil data.</p>
        </div>
        <div style='width: 150px;'>
""", unsafe_allow_html=True)

# Render the local Lottie animation inside the div
if hello_animation:
    st_lottie(hello_animation, height=250, key="ai-animation")

st.markdown("</div></div><hr>", unsafe_allow_html=True)


# --------- User Input -----------
location = st.text_input("📍 Enter your farm location (village/taluka/district):")

if location:
    with st.spinner("📡 Fetching data..."):
        lat, lon = get_coordinates(location)
        if not lat:
            st.error("❌ Could not find coordinates. Try again.")
        else:
            st.success(f"✅ Coordinates for {location}: ({lat}, {lon})")

            past = get_past_weather(lat, lon)
            future = get_future_weather(lat, lon)
            soil = get_soil_data(lat, lon)

            df_past = pd.DataFrame(past)
            df_future = pd.DataFrame(future)
            df_past["date"] = pd.date_range(end=datetime.today() - timedelta(days=1), periods=10)
            df_future["date"] = pd.date_range(start=datetime.today(), periods=10)

            # --------- Weather Chart ----------
            st.markdown("### 📈 Weather Dashboard (Past & Forecast)")
            fig = go.Figure()

            # Past
            fig.add_trace(go.Scatter(x=df_past["date"], y=df_past["temperature_2m_max"],
                                     mode="lines+markers", name="Past Max Temp"))
            fig.add_trace(go.Scatter(x=df_past["date"], y=df_past["temperature_2m_min"],
                                     mode="lines+markers", name="Past Min Temp"))
            fig.add_trace(go.Bar(x=df_past["date"], y=df_past["precipitation_sum"],
                                 name="Past Rain", marker_color='rgba(0,100,255,0.4)'))

            # Forecast
            fig.add_trace(go.Scatter(x=df_future["date"], y=df_future["temperature_2m_max"],
                                     mode="lines+markers", name="Forecast Max Temp", line=dict(dash='dash')))
            fig.add_trace(go.Scatter(x=df_future["date"], y=df_future["temperature_2m_min"],
                                     mode="lines+markers", name="Forecast Min Temp", line=dict(dash='dash')))
            fig.add_trace(go.Bar(x=df_future["date"], y=df_future["precipitation_sum"],
                                 name="Forecast Rain", marker_color='rgba(0,200,255,0.4)'))

            fig.update_layout(title="🌦️ 10-Day Past & Future Weather Overview",
                              xaxis_title="Date",
                              yaxis_title="Temperature (°C) / Rainfall (mm)",
                              legend_title="Legend",
                              barmode='overlay',
                              template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            # --------- Soil Info ----------
            st.markdown("### 🌱 Soil Summary")
            st.write(f"- pH: **{soil['phh2o']}**")
            st.write(f"- Organic Carbon: **{soil['ocd']}**")
            st.write(f"- Sand/Silt/Clay: **{soil['sand']}% / {soil['silt']}% / {soil['clay']}%**")

            # --------- Ask AI ----------
            query = st.text_input("💬 Ask about crop, irrigation, pests, or fertilizer:")
            language = st.radio("🌐 Select your language:", ["English", "Gujarati", "Hindi"], index=0, horizontal=True)

            if query:
                with st.spinner("🤖 Thinking..."):
                    advice = get_advice(location, past, future, soil, query, language)
                    st.markdown("### 💡 AI Agent Suggestion:")
                    st.success(advice)
