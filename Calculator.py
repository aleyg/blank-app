import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# --- Título y descripción ---
st.title("Calculadora de Tiempo de Exposición (CTE)")
st.write("Proyecto de Astronomía Observacional: óptica / infrarroja cercana.")

# --- Sidebar: parámetros de entrada ---
st.sidebar.header("Parámetros de entrada")

modo = st.sidebar.selectbox("Modo", ["Óptico", "Infrarrojo cercano"])
filtro = st.sidebar.selectbox(
    "Filtro",
    ["g", "r", "i"] if modo == "Óptico" else ["J", "H", "Ks"]
)

apertura_m = st.sidebar.selectbox("Apertura del telescopio (m)", [2.0, 3.5, 6.5, 8.0])

mag_obj = st.sidebar.number_input("Magnitud AB del objeto", value=20.0)
sn_objetivo = st.sidebar.number_input("S/N objetivo", value=10.0, min_value=1.0)

t_exp = st.sidebar.slider("Tiempo de exposición (s)", min_value=10, max_value=3600, value=300, step=10)
n_exp = st.sidebar.number_input("Número de exposiciones", value=1, min_value=1)

# Aquí definirás en otro archivo o más abajo tus funciones físicas:
# sn = sn_for_texp(mag_obj, t_exp, n_exp, modo, filtro, apertura_m, otros_parámetros)
# t_req = texp_for_sn(mag_obj, sn_objetivo, n_exp, modo, filtro, apertura_m, otros_parámetros)

# De momento, placeholder: pon algo simple para probar la interfaz
sn = np.sqrt(t_exp)  # BORRAR y sustituir por fórmula real

st.subheader("Resultados")
st.write(f"S/N estimado para t_exp = {t_exp} s: **{sn:.2f}**")

# --- Gráfica S/N vs tiempo de exposición ---
st.subheader("S/N vs tiempo de exposición")

t_grid = np.linspace(10, 3600, 50)
sn_grid = np.sqrt(t_grid)  # aquí luego usarás tu función sn_for_texp

fig, ax = plt.subplots()
ax.plot(t_grid, sn_grid, label="S/N(t)")
ax.axvline(t_exp, color="r", linestyle="--", label="t_exp actual")
ax.set_xlabel("Tiempo de exposición [s]")
ax.set_ylabel("S/N")
ax.legend()
st.pyplot(fig)
