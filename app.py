import streamlit as st
import folium
from folium import FeatureGroup, LayerControl
from folium.plugins import MiniMap, Fullscreen
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import io

st.set_page_config(
    page_title="Peta Keadilan Spasial PKL Surabaya",
    layout="wide",
    page_icon="🗺️",
)

# =========================================================
# DATA CONTOH (dummy) - dipakai kalau tidak ada file yang diupload
# =========================================================

pasar_list = [
    {"nama": "Pasar Wonokromo", "lat": -7.3130, "lon": 112.7340, "jam": "05.00 - 11.00", "kapasitas": 320},
    {"nama": "Pasar Genteng", "lat": -7.2620, "lon": 112.7390, "jam": "04.30 - 10.00", "kapasitas": 210},
    {"nama": "Pasar Keputran", "lat": -7.2725, "lon": 112.7395, "jam": "05.00 - 12.00", "kapasitas": 150},
    {"nama": "Pasar Pabean", "lat": -7.2320, "lon": 112.7370, "jam": "04.00 - 09.00", "kapasitas": 280},
    {"nama": "Pasar Kapasan", "lat": -7.2360, "lon": 112.7460, "jam": "05.00 - 11.00", "kapasitas": 190},
]

klaster_pkl = [
    {"nama": "Kawasan Wonokromo", "jumlah_pkl": 85, "status": "Terlayani", "coords": [
        [-7.305, 112.728], [-7.305, 112.740], [-7.318, 112.740], [-7.318, 112.728]
    ]},
    {"nama": "Kawasan Genteng", "jumlah_pkl": 62, "status": "Terlayani", "coords": [
        [-7.256, 112.733], [-7.256, 112.745], [-7.267, 112.745], [-7.267, 112.733]
    ]},
    {"nama": "Kawasan Pabean", "jumlah_pkl": 74, "status": "Terlayani", "coords": [
        [-7.226, 112.731], [-7.226, 112.743], [-7.237, 112.743], [-7.237, 112.731]
    ]},
]

blank_spot = [
    {"nama": "Kawasan Rungkut", "jumlah_pkl": 58, "status": "Blank Spot", "coords": [
        [-7.330, 112.760], [-7.330, 112.780], [-7.345, 112.780], [-7.345, 112.760]
    ]},
    {"nama": "Kawasan Benowo", "jumlah_pkl": 41, "status": "Blank Spot", "coords": [
        [-7.220, 112.640], [-7.220, 112.660], [-7.235, 112.660], [-7.235, 112.640]
    ]},
    {"nama": "Kawasan Tenggilis", "jumlah_pkl": 36, "status": "Blank Spot", "coords": [
        [-7.320, 112.770], [-7.320, 112.790], [-7.335, 112.790], [-7.335, 112.770]
    ]},
]

rekomendasi = [
    {"nama": "Pasar Satelit Rungkut", "lat": -7.3375, "lon": 112.7700, "alasan": "Berada di tengah klaster PKL blank spot Rungkut (58 PKL), dekat sentra industri"},
    {"nama": "Pasar Satelit Benowo", "lat": -7.2275, "lon": 112.6500, "alasan": "Berada di tengah klaster PKL blank spot Benowo (41 PKL), akses jalan utama"},
    {"nama": "Pasar Satelit Tenggilis", "lat": -7.3275, "lon": 112.7800, "alasan": "Berada di tengah klaster PKL blank spot Tenggilis (36 PKL), kepadatan PKL tinggi"},
]

total_pkl_blankspot = sum(b["jumlah_pkl"] for b in blank_spot)

# =========================================================
# HELPER - baca file GeoJSON yang diupload user
# =========================================================

def baca_geojson(uploaded_file):
    """Baca file GeoJSON/JSON yang diupload jadi GeoDataFrame. Return None kalau tidak ada file."""
    if uploaded_file is None:
        return None
    try:
        gdf = gpd.read_file(io.BytesIO(uploaded_file.getvalue()))
        return gdf
    except Exception as e:
        st.sidebar.error(f"Gagal membaca file: {e}")
        return None

def popup_dari_properti(row, exclude=("geometry",)):
    """Buat HTML popup otomatis dari semua kolom atribut yang ada di data upload user."""
    items = []
    for col, val in row.items():
        if col in exclude:
            continue
        items.append(f"<b>{col}</b>: {val}")
    return "<br>".join(items) if items else "(tidak ada atribut)"

# =========================================================
# SIDEBAR - Sumber Data (Upload)
# =========================================================

st.sidebar.title("📂 Sumber Data")
st.sidebar.markdown(
    "Kosongkan jika ingin memakai data contoh. "
    "Upload GeoJSON hasil export QGIS Anda "
    "(*Layer > Export > Save Features As > GeoJSON*) untuk memakai data asli."
)

up_pasar = st.sidebar.file_uploader("Pasar Tradisional (titik)", type=["geojson", "json"], key="up_pasar")
up_buffer = st.sidebar.file_uploader("Buffer 3 KM (poligon)", type=["geojson", "json"], key="up_buffer")
up_klaster = st.sidebar.file_uploader("Klaster PKL Terlayani (poligon)", type=["geojson", "json"], key="up_klaster")
up_blank = st.sidebar.file_uploader("Blank Spot (poligon)", type=["geojson", "json"], key="up_blank")
up_rekomendasi = st.sidebar.file_uploader("Rekomendasi Pasar Satelit (titik)", type=["geojson", "json"], key="up_rekomendasi")

st.sidebar.markdown("---")
st.sidebar.title("🗺️ Kontrol Peta")
st.sidebar.markdown("Aktifkan/nonaktifkan layer di bawah ini:")

show_pasar = st.sidebar.checkbox("1. Pasar Tradisional (Aktif Pagi)", value=True)
show_buffer = st.sidebar.checkbox("2. Buffer 3 KM", value=True)
show_klaster = st.sidebar.checkbox("3. Klaster PKL Terlayani", value=True)
show_blank = st.sidebar.checkbox("4. Blank Spot", value=True)
show_rekomendasi = st.sidebar.checkbox("5. Rekomendasi Pasar Satelit", value=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Legenda**
    - 🟢 Pasar Tradisional
    - 🔵 Buffer 3 KM
    - 🟩 Klaster PKL Terlayani
    - 🟥 Blank Spot
    - ⭐ Rekomendasi Pasar Satelit
    """
)

# --- Baca semua file yang diupload (kalau ada) ---
gdf_pasar_upload = baca_geojson(up_pasar)
gdf_buffer_upload = baca_geojson(up_buffer)
gdf_klaster_upload = baca_geojson(up_klaster)
gdf_blank_upload = baca_geojson(up_blank)
gdf_rekomendasi_upload = baca_geojson(up_rekomendasi)

pakai_data_asli = any([
    gdf_pasar_upload is not None, gdf_buffer_upload is not None, gdf_klaster_upload is not None,
    gdf_blank_upload is not None, gdf_rekomendasi_upload is not None
])

# =========================================================
# HALAMAN UTAMA
# =========================================================

st.title("Peta Interaktif Keadilan Spasial Akses Bahan Baku PKL Surabaya")
st.caption("WebGIS sederhana — hasil analisis blank spot & rekomendasi lokasi Pasar Satelit")

if pakai_data_asli:
    st.success("✅ Menggunakan data asli yang Anda upload (layer yang tidak diupload tetap memakai data contoh).")
else:
    st.info("ℹ️ Saat ini menampilkan **data contoh (dummy)**. Upload file GeoJSON di sidebar kiri untuk memakai data asli Anda.")

st.markdown(
    f"""
    **Ringkasan Eksekutif:** Analisis spasial menunjukkan terdapat **{len(blank_spot)} kawasan klaster PKL**
    yang berstatus *blank spot* (total ±{total_pkl_blankspot} lapak PKL) karena berada di luar
    radius 3 km dari pasar tradisional aktif pagi terdekat. Kawasan dengan jumlah PKL terbanyak yang
    tidak terlayani adalah **{max(blank_spot, key=lambda x: x['jumlah_pkl'])['nama']}**.

    Berdasarkan temuan ini, direkomendasikan **{len(rekomendasi)} lokasi Pasar Satelit** baru yang
    diposisikan di tengah masing-masing klaster blank spot untuk memperpendek jarak akses bahan baku
    bagi PKL, sekaligus mendukung pemerataan distribusi pasar di wilayah Surabaya.

    *(Catatan: kalimat ringkasan di atas dihitung dari data contoh. Kalau Anda upload data asli,
    silakan sesuaikan narasinya secara manual di laporan.)*
    """
)

# --- Bangun peta Folium ---
m = folium.Map(location=[-7.2756, 112.7382], zoom_start=12, tiles="CartoDB positron", control_scale=True)
Fullscreen().add_to(m)
MiniMap(toggle_display=True).add_to(m)

# --- Layer 1: Pasar Tradisional ---
if show_pasar:
    fg = FeatureGroup(name="Pasar Tradisional")
    if gdf_pasar_upload is not None:
        for _, row in gdf_pasar_upload.iterrows():
            geom = row.geometry
            if geom is None or geom.geom_type != "Point":
                continue
            popup_html = popup_dari_properti(row)
            folium.CircleMarker(
                location=[geom.y, geom.x], radius=8, color="#0d6efd", weight=2,
                fill=True, fill_color="#28a745", fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(fg)
    else:
        for p in pasar_list:
            popup_html = f"<b>{p['nama']}</b><br>Jam Operasional: {p['jam']}<br>Kapasitas PKL: {p['kapasitas']} lapak"
            folium.CircleMarker(
                location=[p["lat"], p["lon"]], radius=8, color="#0d6efd", weight=2,
                fill=True, fill_color="#28a745", fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=250), tooltip=p["nama"],
            ).add_to(fg)
    fg.add_to(m)

# --- Layer 2: Buffer 3 KM ---
if show_buffer:
    fg = FeatureGroup(name="Buffer 3 KM")
    if gdf_buffer_upload is not None:
        for _, row in gdf_buffer_upload.iterrows():
            if row.geometry is None:
                continue
            popup_html = popup_dari_properti(row)
            folium.GeoJson(
                row.geometry,
                style_function=lambda x: {"color": "#6cb2eb", "weight": 1.5, "fillColor": "#6cb2eb", "fillOpacity": 0.15},
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(fg)
    else:
        for p in pasar_list:
            folium.Circle(
                location=[p["lat"], p["lon"]], radius=3000, color="#6cb2eb", weight=1.5,
                fill=True, fill_color="#6cb2eb", fill_opacity=0.15,
                popup=f"Buffer 3km - {p['nama']}",
            ).add_to(fg)
    fg.add_to(m)

# --- Layer 3: Klaster PKL Terlayani ---
if show_klaster:
    fg = FeatureGroup(name="Klaster PKL Terlayani")
    if gdf_klaster_upload is not None:
        for _, row in gdf_klaster_upload.iterrows():
            if row.geometry is None:
                continue
            popup_html = popup_dari_properti(row)
            folium.GeoJson(
                row.geometry,
                style_function=lambda x: {"color": "#1e7e34", "weight": 2, "fillColor": "#28a745", "fillOpacity": 0.35},
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(fg)
    else:
        for k in klaster_pkl:
            popup_html = (
                f"<b>{k['nama']}</b><br>Jumlah PKL: {k['jumlah_pkl']} lapak<br>Status Akses: {k['status']}"
            )
            folium.Polygon(
                locations=k["coords"], color="#1e7e34", weight=2,
                fill=True, fill_color="#28a745", fill_opacity=0.35,
                popup=folium.Popup(popup_html, max_width=250), tooltip=k["nama"],
            ).add_to(fg)
    fg.add_to(m)

# --- Layer 4: Blank Spot ---
if show_blank:
    fg = FeatureGroup(name="Blank Spot")
    if gdf_blank_upload is not None:
        for _, row in gdf_blank_upload.iterrows():
            if row.geometry is None:
                continue
            popup_html = popup_dari_properti(row)
            folium.GeoJson(
                row.geometry,
                style_function=lambda x: {"color": "#a71d2a", "weight": 2, "fillColor": "#dc3545", "fillOpacity": 0.4},
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(fg)
    else:
        for b in blank_spot:
            popup_html = (
                f"<b>{b['nama']}</b><br>Jumlah PKL: {b['jumlah_pkl']} lapak<br>Status Akses: {b['status']}"
            )
            folium.Polygon(
                locations=b["coords"], color="#a71d2a", weight=2,
                fill=True, fill_color="#dc3545", fill_opacity=0.4,
                popup=folium.Popup(popup_html, max_width=250), tooltip=b["nama"],
            ).add_to(fg)
    fg.add_to(m)

# --- Layer 5: Rekomendasi Pasar Satelit ---
if show_rekomendasi:
    fg = FeatureGroup(name="Rekomendasi Pasar Satelit")
    if gdf_rekomendasi_upload is not None:
        for _, row in gdf_rekomendasi_upload.iterrows():
            geom = row.geometry
            if geom is None or geom.geom_type != "Point":
                continue
            popup_html = popup_dari_properti(row)
            folium.Marker(
                location=[geom.y, geom.x],
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color="orange", icon="star", prefix="fa"),
            ).add_to(fg)
    else:
        for r in rekomendasi:
            popup_html = f"<b>⭐ {r['nama']}</b><br>Alasan: {r['alasan']}"
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=folium.Popup(popup_html, max_width=250), tooltip=r["nama"],
                icon=folium.Icon(color="orange", icon="star", prefix="fa"),
            ).add_to(fg)
    fg.add_to(m)

LayerControl(collapsed=False).add_to(m)

# --- Tampilkan peta di app ---
st_folium(m, width=None, height=600, use_container_width=True)

# --- Tabel data pendukung (hanya ditampilkan kalau pakai data contoh) ---
if gdf_pasar_upload is None:
    st.markdown("### 📋 Data Atribut Pasar Tradisional (contoh)")
    df_pasar = pd.DataFrame(pasar_list).rename(columns={
        "nama": "Nama Pasar", "lat": "Latitude", "lon": "Longitude",
        "jam": "Jam Operasional", "kapasitas": "Kapasitas (lapak)"
    })
    st.dataframe(df_pasar, use_container_width=True, hide_index=True)

if gdf_rekomendasi_upload is None:
    st.markdown("### ⭐ Rekomendasi Lokasi Pasar Satelit (contoh)")
    df_rekomendasi = pd.DataFrame(rekomendasi).rename(columns={
        "nama": "Nama Lokasi", "lat": "Latitude", "lon": "Longitude", "alasan": "Alasan Rekomendasi"
    })
    st.dataframe(df_rekomendasi, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("Dibuat dengan Streamlit + Folium. Upload file GeoJSON di sidebar untuk mengganti data contoh dengan data asli Anda.")
