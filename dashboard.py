import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import math

st.set_page_config(layout="wide", page_title="Farm & Control Plot Similarity")

@st.cache_data
def load_data():
    control_farms_path = 'soil_sampled_152_control_farms.csv'
    farms_centroids_path = '7661_farms_centroids.csv'
    
    df_control = pd.read_csv(control_farms_path)
    df_farms = pd.read_csv(farms_centroids_path)
    
    # Process df_control centroid
    df_control[['control_lat', 'control_lon']] = df_control['centroid'].str.split(',', expand=True).astype(float)
    
    # Merge to get farm coordinates
    df_merged = pd.merge(df_control, df_farms[['farm_id', 'lat', 'lon']], on='farm_id', how='inner')
    
    # Rename farm coordinates for clarity
    df_merged = df_merged.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'})
    
    return df_merged

st.title("Farm and Control Plot Similarity Map")
st.markdown("This dashboard visualizes the connection between farms and their respective control plots. "
            "Lines are colored based on the similarity weight.")

try:
    df = load_data()
    
    if df.empty:
        st.warning("No matching data found between the two datasets.")
    else:
        # Create a colormap for similarity_weight
        min_weight = df['similarity_weight'].min()
        max_weight = df['similarity_weight'].max()
        colormap = cm.LinearColormap(colors=['red', 'yellow', 'green'], vmin=min_weight, vmax=max_weight)
        colormap.caption = 'Similarity Weight'

        # Filter option
        selected_farm = st.sidebar.selectbox(
            "Filter by Farm ID (Optional)", 
            options=["All"] + sorted(df['farm_id'].unique().tolist())
        )

        if selected_farm != "All":
            df_plot = df[df['farm_id'] == selected_farm]
        else:
            df_plot = df

        # Center map
        center_lat = df_plot['farm_lat'].mean()
        center_lon = df_plot['farm_lon'].mean()
        
        if math.isnan(center_lat) or math.isnan(center_lon):
            center_lat, center_lon = 0, 0

        # Create Folium map with Esri World Imagery (Satellite)
        m = folium.Map(
            location=[center_lat, center_lon], 
            zoom_start=12, 
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri',
            name='Esri Satellite'
        )

        # Add colormap to map
        m.add_child(colormap)

        # Plot connections and markers
        for idx, row in df_plot.iterrows():
            f_lat, f_lon = row['farm_lat'], row['farm_lon']
            c_lat, c_lon = row['control_lat'], row['control_lon']
            weight = row['similarity_weight']
            color = colormap(weight)
            
            # Draw line between farm and control
            folium.PolyLine(
                locations=[(f_lat, f_lon), (c_lat, c_lon)],
                color=color,
                weight=3,
                opacity=0.8,
                tooltip=f"Similarity: {weight:.4f}"
            ).add_to(m)
            
            # Farm Marker
            folium.CircleMarker(
                location=(f_lat, f_lon),
                radius=5,
                color='white',
                fill=True,
                fill_color='blue',
                fill_opacity=1,
                tooltip=f"Farm ID: {row['farm_id']}"
            ).add_to(m)
            
            # Control Marker
            folium.CircleMarker(
                location=(c_lat, c_lon),
                radius=5,
                color='white',
                fill=True,
                fill_color='orange',
                fill_opacity=1,
                tooltip=f"Control Plot ID: {row['control_plot_id']}<br>Coords: {c_lat:.5f}, {c_lon:.5f}<br>Similarity: {weight:.4f}"
            ).add_to(m)
            
        # Display map
        st_folium(m, width=1200, height=700, returned_objects=[])

except Exception as e:
    st.error(f"Error loading or processing data: {e}")
