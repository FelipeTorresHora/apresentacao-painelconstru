import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pytz
import warnings
warnings.filterwarnings('ignore')

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Análise de Posts",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para carregar e processar os dados com tratamento robusto
@st.cache_data
def load_data():
    try:
        # Carrega o CSV
        df = pd.read_csv('posts.csv')
        
        # Remove linhas onde timestamp é o cabeçalho repetido
        df = df[df['timestamp'] != 'timestamp']
        
        # Converte colunas numéricas de forma segura
        def safe_numeric_convert(series, column_name):
            try:
                # Remove valores não numéricos e converte
                numeric_series = pd.to_numeric(series, errors='coerce')
                return numeric_series.fillna(0)  # Substitui NaN por 0
            except Exception as e:
                st.warning(f"Problema ao converter coluna {column_name}: {str(e)}")
                return pd.Series([0] * len(series))
        
        # Converte colunas numéricas
        if 'followers_count' in df.columns:
            df['followers_count'] = safe_numeric_convert(df['followers_count'], 'followers_count')
        
        if 'media_count' in df.columns:
            df['media_count'] = safe_numeric_convert(df['media_count'], 'media_count')
        
        # Função para converter timestamps de forma robusta
        def parse_timestamp(ts):
            if pd.isna(ts) or ts == 'timestamp' or ts == '':
                return pd.NaT
            
            # Converte para string se não for
            ts = str(ts)
            
            # Lista de formatos possíveis
            formats = [
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S+0000',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    return pd.to_datetime(ts, format=fmt)
                except:
                    continue
            
            # Se nenhum formato funcionou, tenta conversão automática
            try:
                return pd.to_datetime(ts, infer_datetime_format=True)
            except:
                return pd.NaT
        
        # Aplica a conversão de timestamp
        st.write("Processando timestamps...")
        df['timestamp_parsed'] = df['timestamp'].apply(parse_timestamp)
        
        # Remove linhas com timestamps inválidos
        df_clean = df.dropna(subset=['timestamp_parsed']).copy()
        
        if df_clean.empty:
            st.error("Nenhum timestamp válido encontrado nos dados.")
            return None
        
        # Extrai componentes de data
        df_clean['year'] = df_clean['timestamp_parsed'].dt.year
        df_clean['month'] = df_clean['timestamp_parsed'].dt.month
        df_clean['day'] = df_clean['timestamp_parsed'].dt.day
        df_clean['hour'] = df_clean['timestamp_parsed'].dt.hour
        df_clean['weekday'] = df_clean['timestamp_parsed'].dt.day_name()
        df_clean['date'] = df_clean['timestamp_parsed'].dt.date
        
        # Remove anos inválidos (muito antigos ou futuros)
        current_year = datetime.now().year
        df_clean = df_clean[(df_clean['year'] >= 2010) & (df_clean['year'] <= current_year + 1)]
        
        # Garante que as colunas numéricas são do tipo correto
        numeric_columns = ['followers_count', 'media_count', 'year', 'month', 'day', 'hour']
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
        st.success(f"Dados carregados com sucesso! {len(df_clean)} registros válidos.")
        return df_clean
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {str(e)}")
        return None

# Função principal
def main():
    st.title("📊 Dashboard de Análise de Posts")
    st.markdown("---")
    
    # Carrega os dados
    with st.spinner("Carregando dados..."):
        df = load_data()
    
    if df is None or df.empty:
        st.error("Não foi possível carregar os dados. Verifique se o arquivo 'posts.csv' está no diretório correto.")
        return
    
    # Sidebar com filtros
    st.sidebar.header("🔧 Filtros")
    
    # Filtro de anos
    years_available = sorted([int(y) for y in df['year'].unique() if not pd.isna(y)])
    selected_years = st.sidebar.multiselect(
        "Selecione os anos:",
        years_available,
        default=years_available[-3:] if len(years_available) >= 3 else years_available
    )
    
    # Aplica filtros
    if selected_years:
        df_filtered = df[df['year'].isin(selected_years)]
    else:
        df_filtered = df
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Posts", f"{len(df_filtered):,}")
    
    with col2:
        st.metric("Usuários Únicos", f"{df_filtered['username'].nunique():,}")
    
    with col3:
        if len(df_filtered) > 0:
            years_span = int(df_filtered['year'].max() - df_filtered['year'].min() + 1)
            st.metric("Período (anos)", f"{years_span}")
        else:
            st.metric("Período (anos)", "0")
    
    with col4:
        if len(df_filtered) > 0 and 'followers_count' in df_filtered.columns:
            avg_followers = df_filtered['followers_count'].mean()
            st.metric("Média de Seguidores", f"{avg_followers:,.0f}")
        else:
            st.metric("Média de Seguidores", "N/A")
    
    st.markdown("---")
    
    # Layout em duas colunas
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. Distribuição anual de posts
        st.subheader("📅 Distribuição Anual de Posts")
        yearly_posts = df_filtered.groupby('year').size().reset_index(name='posts')
        yearly_posts['year'] = yearly_posts['year'].astype(int)
        
        fig1 = px.bar(
            yearly_posts, 
            x='year', 
            y='posts',
            title="Posts por Ano",
            color='posts',
            color_continuous_scale='viridis'
        )
        fig1.update_layout(height=400)
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        # 2. Distribuição por hora do dia
        st.subheader("🕐 Distribuição por Hora do Dia")
        hourly_posts = df_filtered.groupby('hour').size().reset_index(name='posts')
        hourly_posts['hour'] = hourly_posts['hour'].astype(int)
        
        fig2 = px.bar(
            hourly_posts, 
            x='hour', 
            y='posts',
            title="Posts por Hora do Dia",
            color='posts',
            color_continuous_scale='plasma'
        )
        fig2.update_layout(height=400)
        st.plotly_chart(fig2, use_container_width=True)
# 3. Heatmap de posts por mês/ano COM MARCADORES DA PANDEMIA
    st.subheader("🔥 Heatmap de Posts por Mês/Ano")
    
    try:
        # Cria pivot table para o heatmap
        heatmap_data = df_filtered.groupby(['year', 'month']).size().reset_index(name='posts')
        heatmap_data['year'] = heatmap_data['year'].astype(int)
        heatmap_data['month'] = heatmap_data['month'].astype(int)
        heatmap_data['posts'] = heatmap_data['posts'].astype(int)
        
        if not heatmap_data.empty:
            heatmap_pivot = heatmap_data.pivot(index='month', columns='year', values='posts').fillna(0)
            
            # Nomes dos meses
            month_names = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                           'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
            
            # Cria o heatmap
            fig3 = go.Figure()
            
            # Adiciona o heatmap
            fig3.add_trace(go.Heatmap(
                z=heatmap_pivot.values,
                x=heatmap_pivot.columns,
                y=[month_names[i-1] for i in heatmap_pivot.index],
                colorscale='YlOrRd',
                hoverongaps=False,
                name="Posts"
            ))
            
            # Verifica se 2020 está nos dados para adicionar os marcadores
            if 2020 in heatmap_pivot.columns:
                # Adiciona linha vertical (ano 2020)
                fig3.add_vline(
                    x=2020, 
                    line_dash="dash", 
                    line_color="red", 
                    line_width=3,
                    annotation_text="Início da Pandemia",
                    annotation_position="top"
                )
                
                # Encontra a posição do mês de março se existir
                if 3 in heatmap_pivot.index:  # Março é o mês 3
                    month_position = list(heatmap_pivot.index).index(3)
                    
                    # Adiciona linha horizontal (março)
                    fig3.add_hline(
                        y=month_position, 
                        line_dash="dash", 
                        line_color="red", 
                        line_width=3
                    )
                    
                    # Adiciona anotação específica no ponto de interseção
                    fig3.add_annotation(
                        x=2020,
                        y=month_position,
                        text="🦠 Março/2020<br>Início da Pandemia",
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor="red",
                        ax=50,
                        ay=-50,
                        bgcolor="rgba(255,255,255,0.8)",
                        bordercolor="red",
                        borderwidth=2,
                        font=dict(size=12, color="red")
                    )
            
            fig3.update_layout(
                title="Heatmap de Posts por Mês/Ano - Marcador da Pandemia",
                xaxis_title="Ano",
                yaxis_title="Mês",
                height=500,
                showlegend=False
            )
            st.plotly_chart(fig3, use_container_width=True)
            
            # Adiciona informação sobre o marcador
            st.info("🦠 **Marcador da Pandemia**: As linhas vermelhas tracejadas indicam março de 2020, marco do início da pandemia de COVID-19.")
            
        else:
            st.info("Não há dados suficientes para gerar o heatmap.")
    except Exception as e:
        st.error(f"Erro ao gerar heatmap: {str(e)}")
                
    df['date'] = pd.to_datetime(df['date'])
    # Criação da coluna ano_mes e agrupamento
    df['ano_mes'] = df['date'].dt.to_period('M')
    posts_por_mes = df.groupby('ano_mes').size().reset_index(name='posts')
    posts_por_mes['data'] = posts_por_mes['ano_mes'].dt.to_timestamp()

    # Cálculo da média móvel (3 meses)
    if len(posts_por_mes) > 3:
        posts_por_mes['media_movel'] = posts_por_mes['posts'].rolling(window=3, center=True).mean()
    else:
        posts_por_mes['media_movel'] = None

    # Período da pandemia
    PANDEMIA_INICIO = datetime(2020, 3, 1,tzinfo=pytz.UTC)
    PANDEMIA_FIM = datetime(2021, 12, 31,tzinfo=pytz.UTC)

    # Criar gráfico
    fig = go.Figure()

    # Linha principal
    fig.add_trace(go.Scatter(
        x=posts_por_mes['data'], 
        y=posts_por_mes['posts'],
        mode='lines+markers',
        name='Posts',
        line=dict(color='#2c3e50', width=2.5),
        marker=dict(size=5),
    ))

    # Linha média móvel
    if posts_por_mes['media_movel'].notna().sum() > 0:
        fig.add_trace(go.Scatter(
            x=posts_por_mes['data'], 
            y=posts_por_mes['media_movel'],
            mode='lines',
            name='Média Móvel (3 meses)',
            line=dict(color='orange', width=2, dash='dash'),
        ))

    # Área da pandemia (usando shape)
    fig.add_vrect(
        x0=PANDEMIA_INICIO, x1=PANDEMIA_FIM,
        fillcolor="red", opacity=0.2,
        layer="below", line_width=0,
        annotation_text="Período Pandemia", annotation_position="top left"
    )

    # Layout clean
    fig.update_layout(
        title='📅 Evolução Mensal de Posts',
        xaxis_title='Período',
        yaxis_title='Número de Posts',
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor='white',
        height=450,
        legend=dict(font=dict(size=12))
    )

    fig.update_xaxes(showgrid=False, tickformat="%m/%Y")
    fig.update_yaxes(showgrid=True, gridcolor="lightgray", zeroline=False)

    # Mostrar no Streamlit
    st.subheader("📈 Evolução Mensal de Posts")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Análises Adicionais")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Garantir timestamp no formato datetime com timezone compatível
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True, errors='coerce')

        # Classificar período
        df['periodo'] = df['timestamp'].apply(
            lambda x: 'Pré-Pandemia' if x < PANDEMIA_INICIO else 'Pós-Pandemia'
        )

        # Criar coluna ano_mes
        df['ano_mes'] = df['timestamp'].dt.to_period('M')

        # Separar períodos
        pre_pandemia = df[df['periodo'] == 'Pré-Pandemia']
        pos_pandemia = df[df['periodo'] == 'Pós-Pandemia']

        # Tamanhos para gráfico de pizza
        sizes = [len(pre_pandemia), len(pos_pandemia)]

        if sum(sizes) > 0:
            fig_pizza = px.pie(
                names=['Pré-Pandemia', 'Pós-Pandemia'],
                values=sizes,
                color_discrete_sequence=['#3498db', '#2ecc71'],
                title='Distribuição de Posts por Período'
            )

            fig_pizza.update_traces(
                textinfo='percent+label',
                pull=[0.05, 0.05],
                hole=0.3
            )

            fig_pizza.update_layout(
                showlegend=True,
                height=400
            )

            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.info("Não há dados suficientes para exibir o gráfico.")



    with col2:
        # Distribuição por dia da semana
        st.write("**Posts por Dia da Semana**")
        try:
            weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            weekday_posts = df_filtered['weekday'].value_counts().reindex(weekday_order, fill_value=0)
            
            fig6 = px.bar(
                x=['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'],
                y=weekday_posts.values,
                title="Posts por Dia da Semana"
            )
            fig6.update_layout(height=400)
            st.plotly_chart(fig6, use_container_width=True)
        except Exception as e:
            st.error(f"Erro ao gerar gráfico por dia da semana: {str(e)}")
if __name__ == "__main__":
    main()