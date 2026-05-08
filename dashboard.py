import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import branca.colormap as cm
import math
import os

# 1. Page Configuration
st.set_page_config(layout="wide", page_title="Farm & Control Plot Similarity")

# 2. Data Loading with Caching
@st.cache_data
def load_data():
    control_farms_path = 'soil_sampled_152_control_farms.csv'
    farms_centroids_path = '7661_farms_centroids.csv'
    
    # Check for files (crucial for Streamlit Cloud deployment)
    if not os.path.exists(control_farms_path) or not os.path.exists(farms_centroids_path):
        st.error("CSV files not found in the root directory. Please check your GitHub repository.")
        return pd.DataFrame()

    df_control = pd.read_csv(control_farms_path)
    df_farms = pd.read_csv(farms_centroids_path)
    
    # Process df_control centroid string into lat/lon floats
    # Assuming format "lat, lon"
    df_control[['control_lat', 'control_lon']] = df_control['centroid'].str.split(',', expand=True).astype(float)
    
    # Merge to get farm coordinates from the second CSV
    df_merged = pd.merge(
        df_control, 
        df_farms[['farm_id', 'lat', 'lon']], 
        on='farm_id', 
        how='inner'
    )
    
    return df_merged.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'})

def main():
    st.title("Farm and Control Plot Similarity Map")
    st.markdown("Visualizing the relationship between Farm locations (Blue) and their high-similarity Control Plots (Orange).")

    df = load_data()
    if df.empty:
        st.stop()

    # --- Sidebar Filtering ---
    with st.sidebar:
        st.header("Map Settings")
        selected_farm = st.selectbox(
            "Select Farm ID to Filter", 
            options=["All"] + sorted(df['farm_id'].unique().tolist())
        )
        st.info("Labels appear automatically on the map. Blue dots = Farms, Orange dots = Control Plots.")

    # Filtered Data
    df_plot = df if selected_farm == "All" else df[df['farm_id'] == selected_farm]

    # --- Map Center Calculation ---
    center_lat = df_plot['farm_lat'].mean()
    center_lon = df_plot['farm_lon'].mean()
    if math.isnan(center_lat):
        center_lat, center_lon = 0, 0

    # --- Colormap Logic ---
    min_w, max_w = df['similarity_weight'].min(), df['similarity_weight'].max()
    if min_w == max_w: 
        max_w += 0.001 
    
    colormap = cm.LinearColormap(
        colors=['red', 'yellow', 'green'], 
        vmin=min_w, vmax=max_w,
        caption='Similarity Weight'
    )

    # --- Create Folium Map ---
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=14 if selected_farm != "All" else 12, 
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri Satellite'
    )

    # --- Plot Connections and Markers with Static Labels ---
    for _, row in df_plot.iterrows():
        f_coords = (row['farm_lat'], row['farm_lon'])
        c_coords = (row['control_lat'], row['control_lon'])
        weight = row['similarity_weight']
        
        # 1. Similarity Line
        folium.PolyLine(
            locations=[f_coords, c_coords],
            color=colormap(weight),
            weight=4, opacity=0.8,
            tooltip=f"Similarity: {weight:.4f}"
        ).add_to(m)
        
        # 2. Farm Marker & Label
        folium.CircleMarker(
            location=f_coords, radius=6, color='white', weight=2,
            fill=True, fill_color='blue', fill_opacity=1
        ).add_to(m)
        
        folium.Marker(
            location=f_coords,
            icon=folium.DivIcon(
                icon_size=(150,36),
                icon_anchor=(75, 40), # Positioned slightly above the dot
                html=f"""<div style="font-size: 10pt; color: white; background-color: rgba(0,0,50,0.6); 
                         padding: 2px 5px; border-radius: 3px; text-align: center; font-weight: bold;
                         border: 1px solid white; display: inline-block;">F: {row['farm_id']}</div>"""
            )
        ).add_to(m)
        
        # 3. Control Marker & Label
        folium.CircleMarker(
            location=c_coords, radius=5, color='white', weight=1,
            fill=True, fill_color='orange', fill_opacity=1
        ).add_to(m)
        
        folium.Marker(
            location=c_coords,
            icon=folium.DivIcon(
                icon_size=(150,36),
                icon_anchor=(0, 0), # Positioned to the side/below the dot
                html=f"""<div style="font-size: 9pt; color: white; background-color: rgba(50,25,0,0.6); 
                         padding: 1px 4px; border-radius: 3px; text-align: center;
                         border: 1px solid orange; display: inline-block;">C: {row['control_plot_id']}</div>"""
            )
        ).add_to(m)

    # Add Colormap legend
    m.add_child(colormap)
    
    # Display Map
    st_folium(m, width=1200, height=700, use_container_width=True, returned_objects=[])

    # --- Data Table Section ---
    st.divider()
    if selected_farm == "All":
        st.subheader("Comparison Summary (Top 50 Results)")
        display_df = df_plot.head(50)
    else:
        st.subheader(f"Detailed Data for Farm: {selected_farm}")
        display_df = df_plot

    # Selection of clean columns for the user
    final_table = display_df[[
        'farm_id', 'control_plot_id', 'similarity_weight', 
        'farm_lat', 'farm_lon', 'control_lat', 'control_lon'
    ]].sort_values(by='similarity_weight', ascending=False)

    st.dataframe(final_table, use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
