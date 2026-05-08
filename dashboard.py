import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import math
import os

# Set page config at the very top
st.set_page_config(layout="wide", page_title="Farm & Control Plot Similarity")

@st.cache_data
def load_data():
    # Use relative paths for Streamlit Cloud
    control_farms_path = 'soil_sampled_152_control_farms.csv'
    farms_centroids_path = '7661_farms_centroids.csv'
    
    # Check if files exist to provide better error messages in Cloud
    if not os.path.exists(control_farms_path) or not os.path.exists(farms_centroids_path):
        st.error("Data files not found. Please ensure CSV files are in the root directory.")
        return pd.DataFrame()

    df_control = pd.read_csv(control_farms_path)
    df_farms = pd.read_csv(farms_centroids_path)
    
    # Process df_control centroid: split 'lat, lon' string into floats
    df_control[['control_lat', 'control_lon']] = df_control['centroid'].str.split(',', expand=True).astype(float)
    
    # Merge to get farm coordinates
    df_merged = pd.merge(
        df_control, 
        df_farms[['farm_id', 'lat', 'lon']], 
        on='farm_id', 
        how='inner'
    )
    
    return df_merged.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'})

def main():
    st.title("Farm and Control Plot Similarity Map")
    st.markdown("Visualizing connections between farms (blue) and control plots (orange).")

    df = load_data()
    
    if df.empty:
        st.stop()

    # Sidebar Filter
    with st.sidebar:
        st.header("Settings")
        selected_farm = st.selectbox(
            "Filter by Farm ID", 
            options=["All"] + sorted(df['farm_id'].unique().tolist())
        )

    df_plot = df if selected_farm == "All" else df[df['farm_id'] == selected_farm]

    # Map Setup
    center_lat = df_plot['farm_lat'].mean()
    center_lon = df_plot['farm_lon'].mean()
    
    if math.isnan(center_lat):
        center_lat, center_lon = 0, 0

    # Color Mapping
    min_w, max_w = df['similarity_weight'].min(), df['similarity_weight'].max()
    # Handle case where all weights are the same to avoid colormap errors
    if min_w == max_w:
        max_w += 0.001 
        
    colormap = cm.LinearColormap(
        colors=['red', 'yellow', 'green'], 
        vmin=min_w, 
        vmax=max_w,
        caption='Similarity Weight'
    )

    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12, 
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri'
    )

    # Plotting
    for _, row in df_plot.iterrows():
        f_coords = (row['farm_lat'], row['farm_lon'])
        c_coords = (row['control_lat'], row['control_lon'])
        
        # Connection Line
        folium.PolyLine(
            locations=[f_coords, c_coords],
            color=colormap(row['similarity_weight']),
            weight=3,
            opacity=0.7,
            tooltip=f"Weight: {row['similarity_weight']:.4f}"
        ).add_to(m)
        
        # Farm Marker (Blue)
        folium.CircleMarker(
            location=f_coords, radius=4, color='white', weight=1,
            fill=True, fill_color='blue', fill_opacity=1,
            tooltip=f"Farm: {row['farm_id']}"
        ).add_to(m)
        
        # Control Marker (Orange)
        folium.CircleMarker(
            location=c_coords, radius=4, color='white', weight=1,
            fill=True, fill_color='orange', fill_opacity=1,
            tooltip=f"Control: {row['control_plot_id']}"
        ).add_to(m)

    m.add_child(colormap)
    
    # Render Map
    st_folium(m, width=1000, height=600, returned_objects=[], use_container_width=True)

if __name__ == "__main__":
    main()