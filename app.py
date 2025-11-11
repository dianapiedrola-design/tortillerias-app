import streamlit as st
import json
import requests
import folium
from streamlit_folium import st_folium

# =======================
# CONFIGURACIÓN INICIAL
# =======================
TOKEN_DENUE = "8c682e30-15a4-4f80-8b63-3350cc509f1e"

STATE_CODE = {
    "Aguascalientes": "01", "Baja California": "02", "Baja California Sur": "03",
    "Campeche": "04", "Coahuila": "05", "Colima": "06", "Chiapas": "07",
    "Chihuahua": "08", "Ciudad de México": "09", "Durango": "10", 
    "Guanajuato": "11", "Guerrero": "12", "Hidalgo": "13", "Jalisco": "14", 
    "México": "15", "Michoacán": "16", "Morelos": "17", "Nayarit": "18", 
    "Nuevo León": "19", "Oaxaca": "20", "Puebla": "21", "Querétaro": "22", 
    "Quintana Roo": "23", "San Luis Potosí": "24", "Sinaloa": "25", 
    "Sonora": "26", "Tabasco": "27", "Tamaulipas": "28", "Tlaxcala": "29", 
    "Veracruz": "30", "Yucatán": "31", "Zacatecas": "32"
}

# =======================
# FUNCIONES API
# =======================
def build_buscarareaact_url(cve_ent, cve_mun="0", cve_loc="0",
                            nombre="tortillería", pos_ini=1, pos_fin=200, id_estab=0):
    base = "https://www.inegi.org.mx/app/api/denue/v1/consulta/BuscarAreaAct"
    path = f"/{cve_ent}/{cve_mun}/{cve_loc}/0/0/0/0/0/0/{nombre}/{pos_ini}/{pos_fin}/{id_estab}/{TOKEN_DENUE}"
    return base + path


def fetch_json(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()


def parse_denue_item(item):
    """Extrae nombre, dirección, latitud y longitud."""
    name = None
    address = None
    lat = None
    lon = None

    if isinstance(item, dict):
        name = item.get("Nombre") or item.get("Nombre del establecimiento")
        calle = item.get("Calle")
        num_ext = item.get("Número exterior")
        colonia = item.get("Colonia")
        cp = item.get("Código postal")
        loc_mun_ent = item.get("Localidad, municipio y entidad federativa")
        lat_s = item.get("Latitud")
        lon_s = item.get("Longitud")

        address = ", ".join([str(x) for x in [calle, num_ext, colonia, cp, loc_mun_ent] if x])
        try:
            lat = float(lat_s) if lat_s else None
            lon = float(lon_s) if lon_s else None
        except Exception:
            lat = lon = None

    elif isinstance(item, (list, tuple)):
        def get_i(i): return item[i - 1] if len(item) >= i and item[i - 1] else None
        name = get_i(3)
        calle = get_i(8)
        num_ext = get_i(9)
        colonia = get_i(11)
        cp = get_i(12)
        loc_mun_ent = get_i(13)
        lon_s = get_i(18)
        lat_s = get_i(19)
        address = ", ".join([str(x) for x in [calle, num_ext, colonia, cp, loc_mun_ent] if x])
        try:
            lat = float(lat_s) if lat_s else None
            lon = float(lon_s) if lon_s else None
        except Exception:
            lat = lon = None

    return {"name": name, "address": address, "lat": lat, "lon": lon}


@st.cache_data(show_spinner=False)
def paginate_buscarareaact(cve_ent, cve_mun, cve_loc, nombre="tortillería",
                           page_size=200, max_pages=50):
    results = []
    pos_ini = 1
    for _ in range(max_pages):
        pos_fin = pos_ini + page_size - 1
        url = build_buscarareaact_url(cve_ent, cve_mun, cve_loc, nombre, pos_ini, pos_fin)
        data = fetch_json(url)
        if not data:
            break
        for item in data:
            results.append(parse_denue_item(item))
        if len(data) < page_size:
            break
        pos_ini = pos_fin + 1
    return results


def create_map(rows):
    """Crea el mapa con los marcadores."""
    center = (23.6345, -102.5528)
    for r in rows:
        if r.get("lat") and r.get("lon"):
            center = (r["lat"], r["lon"])
            break
    
    fmap = folium.Map(location=center, zoom_start=12)
    
    for r in rows:
        if r["lat"] and r["lon"]:
            folium.Marker(
                [r["lat"], r["lon"]],
                popup=f"<b>{r['name']}</b><br>{r['address']}",
                tooltip=r['name']
            ).add_to(fmap)
    
    return fmap


# =======================
# INTERFAZ STREAMLIT
# =======================
st.set_page_config(
    page_title="🌮 Mapeador de Tortillerías",
    page_icon="🌮",
    layout="wide"
)

st.title("🌮 Mapeador de Tortillerías en México")
st.markdown("### Encuentra tortillerías cerca de ti usando datos del DENUE (INEGI)")

# Sidebar con opciones
with st.sidebar:
    st.header("⚙️ Configuración de búsqueda")
    
    # Selector de estado
    estado_seleccionado = st.selectbox(
        "Selecciona un estado:",
        options=list(STATE_CODE.keys()),
        index=8  # Ciudad de México por defecto
    )
    
    codigo_estado = STATE_CODE[estado_seleccionado]
    
    # Opción de municipio
    buscar_municipio = st.checkbox("Buscar en municipio específico")
    
    if buscar_municipio:
        codigo_municipio = st.text_input(
            "Código del municipio (3 dígitos):",
            value="000",
            max_chars=3,
            help="Ingresa el código de 3 dígitos del municipio"
        ).zfill(3)
    else:
        codigo_municipio = "0"
    
    # Botón de búsqueda
    buscar = st.button("🔍 Buscar Tortillerías", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("**Datos proporcionados por:**")
    st.markdown("DENUE - INEGI")

# Contenido principal
if buscar:
    with st.spinner(f"Buscando tortillerías en {estado_seleccionado}..."):
        try:
            # Buscar tortillerías
            results = paginate_buscarareaact(codigo_estado, codigo_municipio, "0")
            
            if len(results) == 0:
                st.warning("No se encontraron tortillerías en esta ubicación. Intenta con otro estado o municipio.")
            else:
                # Mostrar métricas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Tortillerías encontradas", len(results))
                
                with col2:
                    con_coordenadas = sum(1 for r in results if r['lat'] and r['lon'])
                    st.metric("Con ubicación", con_coordenadas)
                
                with col3:
                    st.metric("Estado", estado_seleccionado)
                
                st.markdown("---")
                
                # Crear dos columnas: mapa y lista
                col_mapa, col_lista = st.columns([2, 1])
                
                with col_mapa:
                    st.subheader("📍 Mapa de ubicaciones")
                    fmap = create_map(results)
                    st_folium(fmap, width=700, height=500)
                
                with col_lista:
                    st.subheader("📋 Lista de tortillerías")
                    
                    # Mostrar resultados en un contenedor con scroll
                    for i, r in enumerate(results, 1):
                        with st.expander(f"{i}. {r['name']}"):
                            st.write(f"**Dirección:** {r['address']}")
                            if r['lat'] and r['lon']:
                                st.write(f"**Coordenadas:** {r['lat']}, {r['lon']}")
                
                # Botón de descarga
                st.markdown("---")
                st.subheader("💾 Descargar datos")
                
                json_str = json.dumps(results, ensure_ascii=False, indent=2)
                st.download_button(
                    label="📥 Descargar JSON",
                    data=json_str,
                    file_name=f"tortillerias_{estado_seleccionado.replace(' ', '_')}.json",
                    mime="application/json"
                )
                
        except Exception as e:
            st.error(f"Error al buscar tortillerías: {str(e)}")
            st.info("Verifica que los códigos sean correctos o intenta de nuevo más tarde.")

else:
    # Mensaje inicial
    st.info("👈 Selecciona un estado en el menú lateral y haz clic en 'Buscar Tortillerías' para comenzar.")
    
    # Información adicional
    with st.expander("ℹ️ ¿Cómo usar esta aplicación?"):
        st.markdown("""
        1. **Selecciona un estado** del menú desplegable
        2. (Opcional) Marca la casilla para buscar en un municipio específico e ingresa su código
        3. Haz clic en **"Buscar Tortillerías"**
        4. Explora el mapa interactivo y la lista de resultados
        5. Descarga los datos en formato JSON si lo necesitas
        
        **Nota:** Los datos provienen del Directorio Estadístico Nacional de Unidades Económicas (DENUE) del INEGI.
        """)
