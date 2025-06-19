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
from br_mangue_backend import BrMangueModel, load_and_standardize_rasters

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
st.sidebar.subheader("📁 Upload de Dados Raster")
uso_file = st.sidebar.file_uploader("Uso e Ocupação do Solo", type=['tif', 'tiff'], key="uso")
alt_file = st.sidebar.file_uploader("Altimetria", type=['tif', 'tiff'], key="alt")
solos_file = st.sidebar.file_uploader("Solos", type=['tif', 'tiff'], key="solos")

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
   st.info("📋 Por favor, faça o upload dos três arquivos raster (Uso e Ocupação, Altimetria e Solos) para iniciar a simulação.")

   # Mostrar informações sobre o modelo
   col1, col2 = st.columns(2)

   with col1:
       st.subheader("📖 Sobre o Modelo BR MANGUE 2.0")
       st.markdown("""
        Este modelo utiliza a abordagem de Autômatos Celulares,
         Especificamente este modelo emprega a Vizinhança de Moore.

       **Aviso:**
       É importante ressaltar que o Modelo BR-MANGUE encontra-se atualmente em versão beta e em desenvolvimento ativo. 
       Isso significa que novas funcionalidades estão sendo implementadas, 
       otimizações estão sendo realizadas e testes contínuos estão em andamento
       para aprimorar sua precisão e robustez. 

       **Desenvolvedores:**

       Este projeto está sendo desenvolvido por:

Felipe Martins Sousa, Sergio Souza Costa e Denilson da Silva Bezerra


       """)

   with col2:
       st.subheader("📊 Classes de Uso da Terra")
       classes_df = pd.DataFrame({
           'Código': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
           'Classe': [
               'Mangue', 'Vegetação Terrestre', 'Mar', 'Área Antropizada',
               'Solo Descoberto', 'Solo Descoberto Inundado', 'Área Antropizada Inundada',
               'Mangue Migrado', 'Mangue Inundado', 'Vegetação Terrestre Inundada'
           ]
       })
       st.dataframe(classes_df, use_container_width=True)

else:
   if run_simulation:
       # Salvar arquivos temporariamente
       with tempfile.TemporaryDirectory() as temp_dir:
           uso_path = os.path.join(temp_dir, "uso.tif")
           alt_path = os.path.join(temp_dir, "alt.tif")
           solos_path = os.path.join(temp_dir, "solos.tif")

           with open(uso_path, "wb") as f:
               f.write(uso_file.getbuffer())
           with open(alt_path, "wb") as f:
               f.write(alt_file.getbuffer())
           with open(solos_path, "wb") as f:
               f.write(solos_file.getbuffer())

           try:
               # Carregar e padronizar dados
               with st.spinner("📊 Carregando e padronizando dados raster..."):
                   uso_data, alt_data, solos_data, target_resolution = load_and_standardize_rasters(
                       uso_path, alt_path, solos_path
                   )

               st.success(f"✅ Dados carregados com sucesso! Resolução: {target_resolution}")

               # Inicializar modelo
               with st.spinner("🔧 Inicializando modelo BR_MANGUE..."):
                   model = BrMangueModel(
                       uso_data, alt_data, solos_data,
                       area_celula=area_celula,
                       tide_height=tide_height,
                       sea_level_rise_rate=sea_level_rise_rate,
                       final_time=final_time
                   )

               # Executar simulação
               progress_bar = st.progress(0)
               status_text = st.empty()

               with st.spinner("🌊 Executando simulação..."):
                   # Modificar o modelo para atualizar o progresso
                   original_run = model.run_simulation

                   def run_with_progress():
                       results = {'time': [], 'areaVegetacao_USO': [], 'areaVegetacaoInundado_USO': [], 'total_USO': []}

                       for t in range(model.final_time):
                           model.current_time = t + 1

                           # Atualizar progresso
                           progress = (t + 1) / model.final_time
                           progress_bar.progress(progress)
                           status_text.text(f"Iteração {t + 1} de {model.final_time}")

                           # Aplicar lógicas
                           model.cell_space.for_each_cell(lambda r, c, cell: model._apply_flooding_logic(r, c, cell))
                           model.cell_space.for_each_cell(lambda r, c, cell: model._apply_mangrove_dynamics_logic(r, c, cell))
                           model.cell_space.synchronize()

                           # Contagem e armazenamento
                           from br_mangue_backend import contagem
                           contagem(model.model_data, model.cell_space.usos.flatten(), model.area_celula)
                           results['time'].append(model.current_time)
                           results['areaVegetacao_USO'].append(model.model_data.get('areaVegetacao_USO', 0))
                           results['areaVegetacaoInundado_USO'].append(model.model_data.get('areaVegetacaoInundado_USO', 0))
                           results['total_USO'].append(model.model_data.get('total_USO', 0))

                       return results

                   simulation_results = run_with_progress()

               progress_bar.progress(1.0)
               status_text.text("✅ Simulação concluída!")

               # Exibir resultados
               st.success("🎉 Simulação concluída com sucesso!")

               # Criar abas para diferentes visualizações
               tab1, tab2, tab3, tab4 = st.tabs(["📈 Gráficos", "🗺️ Mapas", "📊 Tabela de Resultados", "📋 Resumo"])

               with tab1:
                   st.subheader("📈 Evolução das Áreas ao Longo do Tempo")

                   # Gráfico de linha com Plotly
                   fig = go.Figure()
                   fig.add_trace(go.Scatter(
                       x=simulation_results['time'],
                       y=simulation_results['areaVegetacao_USO'],
                       mode='lines+markers',
                       name='Vegetação Terrestre',
                       line=dict(color='green')
                   ))
                   fig.add_trace(go.Scatter(
                       x=simulation_results['time'],
                       y=simulation_results['areaVegetacaoInundado_USO'],
                       mode='lines+markers',
                       name='Vegetação Inundada',
                       line=dict(color='red')
                   ))

                   fig.update_layout(
                       title="Evolução das Áreas de Vegetação",
                       xaxis_title="Tempo (anos)",
                       yaxis_title="Área (ha)",
                       hovermode='x unified'
                   )

                   st.plotly_chart(fig, use_container_width=True)

               with tab2:
                   st.subheader("🗺️ Estado Final da Simulação")

                   col1, col2 = st.columns(2)

                   with col1:
                       st.write("**Uso da Terra (Estado Final)**")
                       fig_uso, ax_uso = plt.subplots(figsize=(8, 6))
                       im_uso = ax_uso.imshow(model.cell_space.usos, cmap='tab10', interpolation='nearest')
                       ax_uso.set_title("Uso da Terra")
                       plt.colorbar(im_uso, ax=ax_uso)
                       st.pyplot(fig_uso)

                   with col2:
                       st.write("**Altimetria (Estado Final)**")
                       fig_alt, ax_alt = plt.subplots(figsize=(8, 6))
                       im_alt = ax_alt.imshow(model.cell_space.alt, cmap='terrain', interpolation='bilinear')
                       ax_alt.set_title("Altimetria")
                       plt.colorbar(im_alt, ax=ax_alt)
                       st.pyplot(fig_alt)

               with tab3:
                   st.subheader("📊 Tabela de Resultados")

                   # Criar DataFrame com todos os resultados
                   results_df = pd.DataFrame(simulation_results)
                   st.dataframe(results_df, use_container_width=True)

                   # Botão para download
                   csv = results_df.to_csv(index=False)
                   st.download_button(
                       label="📥 Download CSV",
                       data=csv,
                       file_name="br_mangue_results.csv",
                       mime="text/csv"
                   )

               with tab4:
                   st.subheader("📋 Resumo da Simulação")

                   col1, col2, col3 = st.columns(3)

                   with col1:
                       st.metric("Tempo Total", f"{final_time} anos")
                       st.metric("Área da Célula", f"{area_celula} ha")

                   with col2:
                       st.metric("Altura da Maré", f"{tide_height} m")
                       st.metric("Taxa de Elevação", f"{sea_level_rise_rate} m/ano")

                   with col3:
                       st.metric("Dimensões da Grade", f"{model.cell_space.rows} x {model.cell_space.cols}")
                       st.metric("Total de Células", f"{model.cell_space.rows * model.cell_space.cols}")

           except Exception as e:
               st.error(f"❌ Erro durante a simulação: {str(e)}")
               if isinstance(e, ValueError) and "CRS" in str(e):
                   st.error("Por favor, verifique se os arquivos raster fornecidos possuem um Sistema de Coordenadas de Referência (CRS) projetado.")
               st.exception(e)

   else:
       st.info("✅ Arquivos carregados. Configure os parâmetros e clique em 'RUN SIMULATION' para iniciar.")

# Footer
st.markdown("---")
st.markdown("**BR_MANGUE** - Desenvolvido com Python, Streamlit e NumPy | Versão 2.0.1")
