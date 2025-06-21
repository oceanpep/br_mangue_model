import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import folium
from streamlit_folium import st_folium
import tempfile
import os
import zipfile
from br_mangue_backend import BrMangueModel, load_and_standardize_rasters, load_and_rasterize_vector_solos

# Configuração da página
st.set_page_config(
   page_title="BR MANGUE 2.0 - Simulação Espacial de Manguezais",
   page_icon="🌿",
   layout="wide",
   initial_sidebar_state="expanded"
)

# Título principal
st.title("🌿 BR MANGUE 2.0 - Simulação Espacial de Manguezais")
st.markdown("### Sistema de Modelagem baseado em Autômatos Celulares para Dinâmicas Espaciais de Mangue")

# Sidebar para configurações
st.sidebar.header("⚙️ Configurações da Simulação")

# Upload de arquivos
st.sidebar.subheader("📁 Upload de Dados")
uso_file = st.sidebar.file_uploader("Uso e Ocupação do Solo (Raster - .tif)", type=["tif", "tiff"], key="uso")
alt_file = st.sidebar.file_uploader("Altimetria (Raster - .tif)", type=["tif", "tiff"], key="alt")
solos_file = st.sidebar.file_uploader("Solos (Shapefile - .zip)", type=["zip"], key="solos")

# Parâmetros do Shapefile de Solos
st.sidebar.subheader("⚙️ Configurações do Shapefile de Solos")
soil_attribute_column = st.sidebar.text_input("Nome da Coluna de Atributo do Solo no Shapefile", value="ClasseSolos")

# Parâmetros da simulação
st.sidebar.subheader("🔧 Parâmetros da Simulação")
area_celula = st.sidebar.number_input("Área da Célula (ha)", value=0.09, min_value=0.01, max_value=1.0, step=0.01)
tide_height = st.sidebar.number_input("Altura da Maré (m)", value=6.0, min_value=0.0, max_value=20.0, step=0.1)
sea_level_rise_rate = st.sidebar.number_input("Taxa de Elevação do Nível do Mar (m/ano)", value=0.5, min_value=0.0, max_value=2.0, step=0.01)
final_time = st.sidebar.number_input("Tempo Final (anos)", value=50, min_value=1, max_value=200, step=1)

# Botão RUN
run_simulation = st.sidebar.button("🚀 RUN SIMULATION", type="primary", use_container_width=True)

# Área principal
if not all([uso_file, alt_file, solos_file]):
    st.info("📋 Por favor, faça o upload dos arquivos necessários (Uso e Ocupação, Altimetria e Solos) para iniciar a simulação.")
