# -*- coding: utf-8 -*-
"""
TFG – Problema 9.1 (GUI) con customtkinter
Versión FINAL DEFINITIVA (GOD EDITION + DASHBOARD UI) - CORREGIDA Y MEJORADA
(Restaurada funcionalidad completa de la pestaña Interactivo y unificados los cuadros de resumen)

Cambios recientes:
- Unificados los cuadros de texto en "Interactivo":
  - Izquierda: Un solo cuadro para a, b, c.
  - Derecha: Un solo cuadro para d, e.
  Esto elimina el exceso de barras de desplazamiento (sliders).
"""

import numpy as np
import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ----------- Utilidades hidráulicas ----------- #
def hazen_williams_k_per_length(D_m, C):
    """Devuelve k_L tal que hf = k_L * L * Q^1.852 (Q en m³/s, L en m, hf en m)."""
    return 10.67 / (C**1.852 * D_m**4.87)

def choose_CHW_from_eps_over_D(eps_cm, D_m):
    """Asigna C_HW según ε/D (tabla del enunciado)."""
    eps_m = eps_cm / 100.0
    r = eps_m / D_m
    if r <= 1.5e-5:  return 150.0
    if r <= 2.0e-4:  return 140.0
    if r <= 1.0e-3:  return 130.0
    if r <= 4.0e-3:  return 120.0
    if r <= 1.5e-2:  return 110.0
    return 100.0

def interp_xy(x_table, y_table, x):
    if x <= x_table[0]:   return float(y_table[0])
    if x >= x_table[-1]:  return float(y_table[-1])
    for i in range(len(x_table)-1):
        x0, x1 = x_table[i], x_table[i+1]
        if x0 <= x <= x1:
            y0, y1 = y_table[i], y_table[i+1]
            t = (x - x0) / (x1 - x0)
            return float(y0 + t*(y1 - y0))
    return float(y_table[-1])

def bisect_root(f, a, b, tol=1e-8, itmax=200):
    fa, fb = f(a), f(b)
    if fa*fb > 0: return None
    for _ in range(itmax):
        m = 0.5*(a+b); fm = f(m)
        if abs(fm) < tol or (b-a) < tol: return m
        if fa*fm <= 0: b, fb = m, fm
        else: a, fa = m, fm
    return 0.5*(a+b)

# ----------- Curva de la bomba base (Fija a 1490 rpm) ----------- #
Qb_ls = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65], dtype=float)
Hb_m  = np.array([38,38,38,38,38,37,36,34,32,30,26,20,13,0], dtype=float)
eta_p = np.array([ 0,26,45,58,67,74,77,78,77,75,68,80,30,0], dtype=float)

def H_bomba(Ql):
    return interp_xy(Qb_ls, Hb_m, Ql)

def eta_bomba(Ql):
    return interp_xy(Qb_ls, eta_p, Ql)/100.0

# ----------- Válvula de asiento en aspiración ----------- #
# Arrays originales (Parabolic Plug, To Close).
VALVE_OPEN_PCT = np.array([0, 10, 20, 40, 60, 80, 100], dtype=float)
VALVE_PHI_REL  = np.array([0.00, 0.20, 0.30, 0.50, 0.60, 0.80, 1.00], dtype=float)

def phi_from_open(pct_open):
    """Φ = Kv/Kvmax por apertura [%] con interpolación y límites [0,1]."""
    pct = max(0.0, min(100.0, float(pct_open)))
    return float(interp_xy(VALVE_OPEN_PCT, VALVE_PHI_REL, pct))

def hf_valve_from_Kv(Q_lps, s_rel, Kv_max_m3h, pct_open):
    """
    Pérdida en la válvula: hf = 10.197*s*(Q_m3h/Kv)^2
    - 100 % → hf = 0 EXACTO.
    """
    pct_open = round(pct_open)  
    if pct_open >= 100:
        return 0.0
    if pct_open <= 0:
        return 0.0 if Q_lps <= 1e-12 else 1e9

    phi = max(1e-9, phi_from_open(pct_open))
    Kv = phi * max(1e-9, Kv_max_m3h)
    Q_m3h = (Q_lps / 1000.0) * 3600.0
    return 10.197 * s_rel * (Q_m3h / Kv)**2

# ============================ GUI ============================ #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Problema nº1: Bombeo entre depósitos")
        self.geometry("1200x900")
        self.minsize(1100, 800)
        
        # Maximizar ventana
        self.after(0, lambda: self.state('zoomed'))

        # Estado hidráulico
        self.delta_z = 10.0
        self.Q_plot = np.linspace(0, Qb_ls[-1], 400)
        self.k_lps = None
        self.last_Qpf = None; self.last_Hpf = None; self.last_eta = None
        self._update_job = None

        # Fuentes generales
        self.font_h1 = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=14)

        # Pestañas
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_datos = self.tabs.add("Interactivo")
        self.tab_result = self.tabs.add("Resultados")
        self.tab_notas = self.tabs.add("Notas")
        
        # Botón volver al menú (esquina superior izquierda)
        self.back_btn = ctk.CTkButton(self, text="← Volver al Menú", 
                                       command=self._volver_menu,
                                       width=140, height=32,
                                       fg_color="#666666", hover_color="#444444")
        self.back_btn.place(x=10, y=10)

        # --- VARIABLES PARA RESULTADOS (DASHBOARD) ---
        self.res_a_chw = ctk.StringVar(value="-")
        self.res_a_ecuacion = ctk.StringVar(value="Pendiente de cálculo")
        
        self.res_b_apertura = ctk.StringVar(value="- %")
        self.res_b_kvmax = ctk.StringVar(value="-")
        self.res_b_Q = ctk.StringVar(value="--.--")
        self.res_b_H = ctk.StringVar(value="--.--")
        self.res_b_Eta = ctk.StringVar(value="--.-")
        
        self.res_c_Pabs = ctk.StringVar(value="--.--")
        
        self.res_e_dH0 = ctk.StringVar(value="-")
        self.res_e_PB = ctk.StringVar(value="-")
        self.res_status = ctk.StringVar(value="Esperando cálculo...")

        # Construcción de la UI
        self._build_interactivo()
        self._build_resultados()
        self._build_notas()
        
        self._draw_static_ccb()

    # -------------------- helpers UI -------------------- #
    def _flash(self, widget, color=("#FFF4CC", "#3A2F00"), dur_ms=180):
        try:
            orig = widget.cget("fg_color")
            widget.configure(fg_color=color)
            widget.after(dur_ms, lambda: widget.configure(fg_color=orig))
        except Exception:
            pass

    def _set_text(self, tb: ctk.CTkTextbox, content: str):
        old = tb.get("1.0", "end-1c")
        if old == content:
            return
        tb.configure(state="normal")
        tb.delete("1.0", "end")
        tb.insert("end", content)
        tb.configure(state="disabled")
        self._flash(tb)

    # -------------------- TAB: INTERACTIVO -------------------- #
    def _build_interactivo(self):
        root = ctk.CTkFrame(self.tab_datos)
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # Izquierda: controles
        controls = ctk.CTkScrollableFrame(root, width=380)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 10))

        # Vars (inicializadas con valores por defecto)
        self.s_var   = ctk.StringVar(value="1.2")
        self.nu_var  = ctk.StringVar(value="1e-6")
        self.D1_var  = ctk.StringVar(value="200")
        self.L1_var  = ctk.StringVar(value="200")
        self.D2_var  = ctk.StringVar(value="150")
        self.L2_var  = ctk.StringVar(value="500")
        self.eps_var = ctk.StringVar(value="0.01")  # cm
        self.PB_var  = ctk.StringVar(value="")
        
        # Válvula
        self.open_var  = ctk.StringVar(value="100")   # %
        self.kvmax_var = ctk.StringVar(value="300")   # Kv_max fijo y oculto

        ctk.CTkLabel(controls, text="Parámetros", font=self.font_h1).pack(anchor="w", padx=6, pady=(6,2))

        # Helper: slider + entry sincronizados con "Snapping"
        def add_entry_slider(parent, label, var, unit, vmin, vmax, step, fmt):
            row = ctk.CTkFrame(parent); row.pack(fill="x", padx=6, pady=(6,0))
            ctk.CTkLabel(row, text=label, font=self.font_body).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=unit, font=self.font_body).grid(row=0, column=2, sticky="w", padx=(6,0))

            sframe = ctk.CTkFrame(parent); sframe.pack(fill="x", padx=6, pady=(2,8))
            sframe.grid_columnconfigure(0, weight=1)
            
            n_steps = int(round((vmax - vmin) / step))
            
            slider = ctk.CTkSlider(sframe, from_=vmin, to=vmax, number_of_steps=n_steps)
            
            try: init = float(str(var.get()).replace(",", "."))
            except: init = vmin
            slider.set(init)
            slider.grid(row=0, column=0, sticky="ew", padx=(4,6), pady=2)

            ent = ctk.CTkEntry(sframe, textvariable=var, width=80, justify="right")
            ent.grid(row=0, column=1, sticky="e")

            def on_slide(val):
                var.set(fmt.format(val))
                self._schedule_recalc()
            slider.configure(command=on_slide)

            def _snap_to_step(val_in):
                steps_count = round((val_in - vmin) / step)
                snapped = vmin + steps_count * step
                return min(max(snapped, vmin), vmax)

            def on_entry_change(*_):
                txt = str(var.get()).replace(",", ".").strip()
                try: x = float(txt)
                except ValueError: return
                slider.set(min(max(x, vmin), vmax))
                self._schedule_recalc()
            var.trace_add("write", on_entry_change)

            def on_focus_out(_):
                txt = str(var.get()).replace(",", ".").strip()
                try: x = float(txt)
                except ValueError: x = slider.get()
                final_val = _snap_to_step(x)
                var.set(fmt.format(final_val))
                slider.set(final_val)
                self._schedule_recalc()

            ent.bind("<FocusOut>", on_focus_out)
            ent.bind("<Return>", lambda e: on_focus_out(e))
            return ent, slider

        # Sliders
        self.ent_s,  self.sl_s  = add_entry_slider(controls, "s (densidad relativa)", self.s_var, "-", 0.8, 1.4, 0.01, "{:.2f}")
        
        row_nu = ctk.CTkFrame(controls); row_nu.pack(fill="x", padx=6, pady=(6,8))
        ctk.CTkLabel(row_nu, text="ν (m²/s)", font=self.font_body).pack(side="left")
        ctk.CTkEntry(row_nu, textvariable=self.nu_var, width=100, justify="right").pack(side="left", padx=6)
        ctk.CTkLabel(row_nu, text="m²/s", font=self.font_body).pack(side="left")

        # DIAMETROS COMERCIALES
        self.ent_D1, self.sl_D1 = add_entry_slider(controls, "D1 (comercial)", self.D1_var, "mm", 50.0, 400.0, 25.0, "{:.0f}")
        self.ent_L1, self.sl_L1 = add_entry_slider(controls, "L1", self.L1_var, "m", 10.0, 1000.0, 1.0, "{:.0f}")
        
        self.ent_D2, self.sl_D2 = add_entry_slider(controls, "D2 (comercial)", self.D2_var, "mm", 50.0, 400.0, 25.0, "{:.0f}")
        self.ent_L2, self.sl_L2 = add_entry_slider(controls, "L2", self.L2_var, "m", 10.0, 1500.0, 1.0, "{:.0f}")
        
        self.ent_eps,self.sl_eps= add_entry_slider(controls, "ε (cm)", self.eps_var, "cm", 0.001, 0.10, 0.001, "{:.3f}")

        # Válvula
        ctk.CTkLabel(controls, text="Regulación Válvula", font=self.font_h2).pack(anchor="w", padx=6, pady=(8,2))
        self.ent_open, self.sl_open = add_entry_slider(controls, "Apertura válvula", self.open_var, "%", 0.0, 100.0, 1.0, "{:.0f}")

        # Botones Principales
        btns = ctk.CTkFrame(controls); btns.pack(fill="x", padx=6, pady=(8,12))
        self.calc_btn = ctk.CTkButton(btns, text="Calcular a) b) c) e)", command=self.calcular)
        self.calc_btn.pack(fill="x")

        # Presurización
        pres = ctk.CTkFrame(controls); pres.pack(fill="x", padx=6, pady=(4,8))
        ctk.CTkLabel(pres, text="d) PB (kg/cm²) manométrica en B", font=self.font_body).pack(anchor="w")
        pb_row = ctk.CTkFrame(pres); pb_row.pack(fill="x", pady=4)
        ctk.CTkEntry(pb_row, textvariable=self.PB_var, width=120, justify="right").pack(side="left", padx=4)
        self.d_btn = ctk.CTkButton(pb_row, text="Aplicar d) presurización", command=self.aplicar_presion_B, state="disabled")
        self.d_btn.pack(side="left", padx=4)

        # Botón RESET (El GOD)
        reset_btn = ctk.CTkButton(controls, text="Restaurar valores iniciales", fg_color="#555555", hover_color="#333333", command=self.reset_valores)
        reset_btn.pack(fill="x", padx=6, pady=(6,10))

        # Tabla Hmi
        table_frame = ctk.CTkFrame(controls); table_frame.pack(fill="both", expand=False, padx=6, pady=6)
        ctk.CTkLabel(table_frame, text="Tabla Hmi cada 5 l/s", font=self.font_h2).pack(anchor="w", padx=6, pady=6)
        columns = ("Q_lps","Hmi_m")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=8)
        self.tree.heading("Q_lps", text="Q (l/s)"); self.tree.heading("Hmi_m", text="Hmi (m)")
        self.tree.column("Q_lps", width=90, anchor="center")
        self.tree.column("Hmi_m", width=110, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        export_row = ctk.CTkFrame(controls); export_row.pack(fill="x", padx=6, pady=6)
        ctk.CTkButton(export_row, text="Exportar tabla a CSV", command=self.exportar_csv).pack(side="left", padx=4)
        ctk.CTkButton(export_row, text="Guardar gráfica", command=self.guardar_grafica).pack(side="left", padx=4)

        # Derecha: gráfico y resultados (resumidos lado izquierdo)
        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=4)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Gráfico
        plot_frame = ctk.CTkFrame(right)
        plot_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4,2))
        self.fig = plt.Figure(figsize=(6.8, 4.8))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("Hm (mcl)")
        self.ax.set_title("Curvas características y punto de funcionamiento"); self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Resultados pequeños (panel resumen debajo del gráfico en pestaña interactiva)
        # Se unifican los textboxes para evitar múltiples scrollbars.
        res = ctk.CTkFrame(right)
        res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1)
        res.grid_columnconfigure(1, weight=1)

        left_col  = ctk.CTkFrame(res); left_col.grid(row=0, column=0, sticky="nsew", padx=(6,3), pady=6)
        right_col = ctk.CTkFrame(res); right_col.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)

        # Columna Izquierda: Un solo cuadro para a, b, c
        ctk.CTkLabel(left_col, text="Resumen a, b, c", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.txt_res_abc = ctk.CTkTextbox(left_col, font=self.font_body)
        self.txt_res_abc.pack(fill="both", expand=True, padx=8, pady=2)
        
        # Columna Derecha: Un solo cuadro para d, e
        ctk.CTkLabel(right_col, text="Resumen d, e", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.txt_res_de = ctk.CTkTextbox(right_col, font=self.font_body)
        self.txt_res_de.pack(fill="both", expand=True, padx=8, pady=2)
        
        # Inicializar textos
        self._set_text(self.txt_res_abc, "a) Pendiente de cálculo…\n\nb) Pendiente de cálculo…\n\nc) Pendiente de cálculo…\n")
        self._set_text(self.txt_res_de, "d) Introduce PB y pulsa el botón.\n\ne) Pendiente de cálculo.\n")

    # -------------------- TAB: RESULTADOS (DASHBOARD) -------------------- #
    def _build_resultados(self):
        # Frame principal con scroll para resultados
        main_scroll = ctk.CTkScrollableFrame(self.tab_result, fg_color="transparent")
        main_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        # --- ESTILOS ---
        color_card = "#FFFFFF" # Blanco para resaltar sobre el fondo grisáceo
        color_accent = "#3B8ED0" # Azul CustomTkinter
        font_title = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        font_value = ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
        font_label = ctk.CTkFont(family="Segoe UI", size=12)

        # --- HELPER PARA CREAR TARJETAS ---
        def create_card(parent, title, icon=""):
            card = ctk.CTkFrame(parent, fg_color=color_card, corner_radius=15, border_width=1, border_color="#E0E0E0")
            card.pack(fill="x", pady=5, padx=5)
            
            # Header de la tarjeta
            header = ctk.CTkFrame(card, fg_color="transparent", height=30)
            header.pack(fill="x", padx=15, pady=(10, 5))
            
            ctk.CTkLabel(header, text=f"{icon} {title}", font=font_title, text_color="#333").pack(side="left")
            # Línea separadora decorativa azul
            ctk.CTkFrame(card, height=2, fg_color=color_accent).pack(fill="x", padx=15, pady=(0, 10))
            return card

        # --- SECCIÓN B: EL PUNTO DE FUNCIONAMIENTO (Lo más importante arriba) ---
        frm_pf = create_card(main_scroll, "Punto de Funcionamiento", icon="⚙️")
        
        # Grid para métricas grandes (Q, H, Eta, P)
        grid_metrics = ctk.CTkFrame(frm_pf, fg_color="transparent")
        grid_metrics.pack(fill="x", padx=10, pady=10)
        
        # Función para columna de métrica
        def add_metric(parent, label, variable, unit, col):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.grid(row=0, column=col, sticky="ew", padx=10)
            parent.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(f, text=label, font=font_label, text_color="gray").pack(anchor="center")
            ctk.CTkLabel(f, textvariable=variable, font=font_value, text_color=color_accent).pack(anchor="center")
            ctk.CTkLabel(f, text=unit, font=("Segoe UI", 12, "bold"), text_color="gray").pack(anchor="center")

        add_metric(grid_metrics, "CAUDAL (Q)", self.res_b_Q, "l/s", 0)
        add_metric(grid_metrics, "ALTURA (H)", self.res_b_H, "m.c.a.", 1)
        add_metric(grid_metrics, "RENDIMIENTO (η)", self.res_b_Eta, "%", 2)
        add_metric(grid_metrics, "POTENCIA (Pabs)", self.res_c_Pabs, "kW", 3)

        # Info extra de la válvula en el PF
        inf_valv = ctk.CTkFrame(frm_pf, fg_color="#F1F5F9", corner_radius=6)
        inf_valv.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(inf_valv, textvariable=self.res_b_apertura, font=("Segoe UI", 12)).pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(inf_valv, textvariable=self.res_b_kvmax, font=("Segoe UI", 12)).pack(side="right", padx=10, pady=5)

        # --- SECCIÓN A: CARACTERÍSTICA INSTALACIÓN ---
        frm_a = create_card(main_scroll, "Curva Característica (CCI)", icon="📈")
        ctk.CTkLabel(frm_a, text="Ecuación de ajuste:", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20)
        ctk.CTkLabel(frm_a, textvariable=self.res_a_ecuacion, font=("Consolas", 13), text_color="#444", wraplength=700).pack(anchor="w", padx=20, pady=(0,5))
        
        detalles_a = ctk.CTkFrame(frm_a, fg_color="transparent")
        detalles_a.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(detalles_a, textvariable=self.res_a_chw, font=("Segoe UI", 12), justify="left").pack(anchor="w")

        # --- SECCIÓN E: LÍMITE DE PRESURIZACIÓN ---
        frm_e = create_card(main_scroll, "Análisis de Presurización (Depósito B)", icon="🚨")
        
        # Usamos un grid dentro de la tarjeta
        grid_e = ctk.CTkFrame(frm_e, fg_color="transparent")
        grid_e.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(grid_e, text="Presión Límite (Umbral):", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(grid_e, textvariable=self.res_e_PB, font=("Segoe UI", 14), text_color="#D32F2F").grid(row=0, column=1, sticky="w", padx=10)
        
        ctk.CTkLabel(grid_e, text="Altura estática equivalente:", font=("Segoe UI", 12)).grid(row=1, column=0, sticky="w")
        ctk.CTkLabel(grid_e, textvariable=self.res_e_dH0, font=("Segoe UI", 12)).grid(row=1, column=1, sticky="w", padx=10)

        # --- BARRA DE ESTADO INFERIOR ---
        status_bar = ctk.CTkFrame(self.tab_result, fg_color="#333333", height=30, corner_radius=0)
        status_bar.pack(fill="x", side="bottom")
        ctk.CTkLabel(status_bar, textvariable=self.res_status, text_color="white", font=("Segoe UI", 11)).pack(side="left", padx=10)

    # -------------------- TAB: NOTAS -------------------- #
    def _build_notas(self):
        scroll = ctk.CTkScrollableFrame(self.tab_notas, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        def add_note_section(title, lines):
            frame = ctk.CTkFrame(scroll, fg_color="white", corner_radius=10, border_color="#DDD", border_width=1)
            frame.pack(fill="x", pady=8)
            
            # Titulo sección
            ctk.CTkLabel(frame, text=title, font=("Segoe UI", 14, "bold"), text_color="#3B8ED0").pack(anchor="w", padx=15, pady=(10, 5))
            
            # Contenido
            for line in lines:
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", padx=15, pady=2)
                ctk.CTkLabel(row, text="•", font=("Arial", 16, "bold"), text_color="#555", width=20).pack(side="left", anchor="n")
                ctk.CTkLabel(row, text=line, font=("Segoe UI", 13), text_color="#333", justify="left", wraplength=800).pack(side="left", fill="x", expand=True)
            
            # Espacio final
            ctk.CTkFrame(frame, height=5, fg_color="transparent").pack()

        # Sección 1: Modelo Físico
        add_note_section("Modelo Hidráulico", [
            "Bernoulli entre A y B: Hmi = Δz + hf (con Δz = 10 m).",
            "Pérdidas por fricción (Hazen-Williams): hf = Σ 10.67·L·Q^1.852 / (C^1.852·D^4.87).",
            "Coeficiente C_HW asignado dinámicamente según rugosidad relativa ε/D (Tabla del enunciado)."
        ])

        # Sección 2: Equipos
        add_note_section("Bomba y Válvula", [
            "Bomba centrífuga funcionando a velocidad nominal constante (1490 rpm).",
            "Válvula de asiento (Globo, Parabolic Plug) modelada según catálogo Fisher/Emerson.",
            "Valve Sizing: Kv_max fijado internamente en 300 m³/h para garantizar autoridad de control.",
            "Comportamiento límite: A 0% apertura (cerrada), la resistencia es infinita y el caudal es estrictamente nulo."
        ])

        # Sección 3: Cálculos Avanzados
        add_note_section("Análisis de Presión", [
            "Presurización del depósito B: Se modela añadiendo una altura piezométrica equivalente ΔH0 = 10·PB/s.",
            "PB Límite: Es la presión mínima en B necesaria para igualar la altura de la bomba a caudal cero (Shut-off head), impidiendo la circulación."
        ])

    # -------------------- Helpers -------------------- #
    def _schedule_recalc(self):
        if self._update_job is not None:
            try: self.after_cancel(self._update_job)
            except Exception: pass
        self._update_job = self.after(150, self._recalc_from_sliders)

    def _recalc_from_sliders(self):
        self._update_job = None
        try:
            self.calcular()
        except Exception:
            pass

    def _draw_static_ccb(self):
        self.ax.cla(); self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("Hm (mcl)")
        self.ax.set_title("Curvas características y punto de funcionamiento")
        self.ax.plot(Qb_ls, Hb_m, "o-", label="CC bomba (1490 rpm)", linewidth=2, color="tab:green")
        self.ax.legend(); self.canvas.draw_idle()

    def _parse_inputs(self):
        try:
            s   = float(self.s_var.get().replace(",", "."))
            nu  = float(self.nu_var.get().replace(",", "."))  # informativo
            D1m = float(self.D1_var.get().replace(",", "."))/1000.0
            L1  = float(self.L1_var.get().replace(",", "."))
            D2m = float(self.D2_var.get().replace(",", "."))/1000.0
            L2  = float(self.L2_var.get().replace(",", "."))
            eps = float(self.eps_var.get().replace(",", "."))  # cm
            open_pct = float(self.open_var.get().replace(",", "."))
            kvmax = float(self.kvmax_var.get().replace(",", "."))
            if D1m <= 0 or D2m <= 0 or L1 <= 0 or L2 <= 0 or s <= 0 or kvmax <= 0:
                raise ValueError
            open_pct = round(min(max(open_pct, 0.0), 100.0))  # entero 0..100
            return s, nu, D1m, L1, D2m, L2, eps, open_pct, kvmax
        except Exception:
            messagebox.showerror("Error", "Entrada no válida. Revisa las casillas.")
            return None

    def _cci_params(self, D1m, L1, D2m, L2, eps_cm):
        C1 = choose_CHW_from_eps_over_D(eps_cm, D1m)
        C2 = choose_CHW_from_eps_over_D(eps_cm, D2m)
        kL1 = hazen_williams_k_per_length(D1m, C1)
        kL2 = hazen_williams_k_per_length(D2m, C2)
        k_total_lps = (kL1*L1 + kL2*L2) / (1000.0**1.852)
        J1_lps = kL1 / (1000.0**1.852)
        J2_lps = kL2 / (1000.0**1.852)
        return C1, C2, J1_lps, J2_lps, k_total_lps

    def H_inst_lps(self, q_lps, k_lps, s_rel, kvmax_m3h, pct_open, dH0=0.0):
        """CCI total: base + pérdidas tuberías + pérdidas válvula."""
        base = (self.delta_z + dH0) + k_lps*(q_lps**1.852)
        hf_val = hf_valve_from_Kv(q_lps, s_rel, kvmax_m3h, pct_open)
        return base + hf_val

    # -------------------- Acciones principales -------------------- #
    def calcular(self):
        parsed = self._parse_inputs()
        if not parsed: return
        s, nu, D1m, L1, D2m, L2, eps_cm, open_pct, kvmax = parsed

        C1, C2, J1_lps, J2_lps, k_lps = self._cci_params(D1m, L1, D2m, L2, eps_cm)
        self.k_lps = k_lps

        qs = np.arange(0.0, 61.0+1e-9, 5.0)

        def equilibrio(q):
            return H_bomba(q) - self.H_inst_lps(q, k_lps, s, kvmax, open_pct)

        Qmax_busca = 65.0
        Qpf = bisect_root(equilibrio, 0.0, Qmax_busca, tol=1e-8)
        
        # --- ACTUALIZAR DATOS DE DASHBOARD (Pestaña Resultados) ---
        
        # 1. Sección A (CCI) - Se actualiza siempre
        self.res_a_chw.set(f"C_HW1={C1:.0f}, C_HW2={C2:.0f} (según ε/D={eps_cm/100/D1m:.1e})")
        self.res_a_ecuacion.set(f"Hmi(Q) = {self.delta_z:.2f} + {k_lps:.5f}·Q^1.852 + hf_valv(Q)")
        
        # 2. Sección E (PB Límite) - Se actualiza siempre
        Hb0 = H_bomba(0.0)
        dH0_lim_m = max(Hb0 - self.delta_z, 0.0)
        PB_lim_kPa = 9800.0 * s * dH0_lim_m / 1000.0
        PB_lim_kgcm2 = s * dH0_lim_m / 10.0
        self.res_e_dH0.set(f"ΔH0_lím = {dH0_lim_m:.2f} mcl")
        self.res_e_PB.set(f"{PB_lim_kgcm2:.2f} kg/cm² ({PB_lim_kPa:.0f} kPa)")

        # --- CONSTRUCCIÓN DEL TEXTO PARA EL PANEL INTERACTIVO (UNIFICADO) ---
        
        # Parte A (Siempre visible)
        str_a = (
            f"[a] Curva característica de la instalación:\n"
            f"    C_HW1={C1:.0f}, C_HW2={C2:.0f} (según ε/D).\n"
            f"    J1={J1_lps:.6e}·Q^1.852 y J2={J2_lps:.6e}·Q^1.852 (Q en l/s, por m).\n"
            f"    Hmi(Q) = {self.delta_z:.2f} + {k_lps:.6f}·Q^1.852 + hf_válvula(Q)."
        )
        # Parte E (Siempre visible)
        str_e = (
            f"[e] PB_límite en el depósito B (umbral sin circulación):\n"
            f"    PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm² (≈ {PB_lim_kPa:.0f} kPa).\n"
            f"    Aplica cuando B está presurizado."
        )

        if Qpf is None:
            # CASO SIN INTERSECCIÓN (Caudal Nulo)
            self._plot_curvas(k_lps, s, kvmax, open_pct, Qpf=None)
            
            # Dashboard a ceros/alertas
            self.res_b_apertura.set(f"Apertura: {open_pct:.0f}%")
            self.res_b_kvmax.set(f"Kv_max (int.): {kvmax:.0f}")
            self.res_b_Q.set("0.00")
            self.res_b_H.set(f"{Hb0:.2f}") 
            self.res_b_Eta.set("0.0")
            self.res_c_Pabs.set("0.00")
            self.res_status.set("Estado: Válvula cerrada o resistencia infinita. No hay circulación.")
            
            # Textos panel interactivo
            str_b = f"[b] Punto de funcionamiento:\n    Apertura = {open_pct:.0f} %.\n    Q = 0.00 l/s (Cerrado)."
            str_c = f"[c] Potencia absorbida:\n    P_abs = 0.00 kW."
            
            self._set_text(self.txt_res_abc, f"{str_a}\n\n{str_b}\n\n{str_c}")
            self._set_text(self.txt_res_de, f"d) Introduce PB y pulsa el botón.\n\n{str_e}")

            # Tabla
            for row in self.tree.get_children(): self.tree.delete(row)
            for q in qs:
                self.tree.insert("", "end", values=(f"{q:5.0f}", f"{self.H_inst_lps(q, k_lps, s, kvmax, open_pct):6.2f}"))
            
            self.d_btn.configure(state="disabled")
            return

        # CASO NORMAL (Con caudal)
        Hpf = H_bomba(Qpf); etapf = eta_bomba(Qpf)
        gamma = 9800.0 * s
        Pabs_kW = gamma*(Qpf/1000.0)*Hpf/max(etapf,1e-9)/1000.0

        # Dashboard con datos
        self.res_b_apertura.set(f"Apertura: {open_pct:.0f}%")
        self.res_b_kvmax.set(f"Kv_max: {kvmax:.0f}")
        self.res_b_Q.set(f"{Qpf:.2f}")
        self.res_b_H.set(f"{Hpf:.2f}")
        self.res_b_Eta.set(f"{etapf*100:.1f}")
        self.res_c_Pabs.set(f"{Pabs_kW:.2f}")
        self.res_status.set("Cálculo exitoso. Sistema en equilibrio.")
        
        # Textos panel interactivo
        str_b = (
            f"[b] Punto de funcionamiento:\n"
            f"    Apertura = {open_pct:.0f} %.\n"
            f"    Q = {Qpf:.2f} l/s, H = {Hpf:.2f} m, η = {etapf*100:.1f} %."
        )
        str_c = f"[c] Potencia absorbida:\n    P_abs ≈ {Pabs_kW:.2f} kW."

        self._set_text(self.txt_res_abc, f"{str_a}\n\n{str_b}\n\n{str_c}")
        self._set_text(self.txt_res_de, f"d) Introduce PB y pulsa el botón.\n\n{str_e}")

        # Tabla
        for row in self.tree.get_children(): self.tree.delete(row)
        for q in qs:
            self.tree.insert("", "end", values=(f"{q:5.0f}", f"{self.H_inst_lps(q, k_lps, s, kvmax, open_pct):6.2f}"))

        # Gráfica
        self._plot_curvas(k_lps, s, kvmax, open_pct, Qpf=Qpf, Hpf=Hpf)

        self.last_Qpf, self.last_Hpf, self.last_eta = Qpf, Hpf, etapf
        self.d_btn.configure(state="normal")

    def _plot_curvas(self, k_lps, s, kvmax, open_pct, Qpf=None, Hpf=None):
        self.ax.cla(); self.ax.grid(True)
        self.ax.set_xlabel(r"$Q$ (L/s)"); self.ax.set_ylabel(r"$H_m$ (m.c.l.)")
        self.ax.set_title("Curvas características y punto de funcionamiento")

        Q_plot = self.Q_plot
        H_inst_base = [self.H_inst_lps(q, k_lps, s, kvmax, 100.0) for q in Q_plot]
        
        # Curva Bomba Fija
        Qs, Hs = Qb_ls, Hb_m

        if open_pct == 0:
            # 1. Curva Base (discontinua)
            self.ax.plot(Q_plot, H_inst_base, linestyle="--", color="tab:blue", label=r"CCI (válvula abierta 100%)", linewidth=1.5)
            
            # 2. Curva Bomba
            self.ax.plot(Qs, Hs, "o-", color="tab:green", label=r"CC bomba (1490 rpm)", linewidth=2)
            
            # 3. LÍNEA VERTICAL INFINITA (resistencia infinita)
            y_techo = max(Hs) * 1.5 
            self.ax.plot([0, 0], [self.delta_z, y_techo], color="tab:orange", linewidth=3, label=r"CCI con válvula (cerrada 0%)")
            
            # Cartel rojo translúcido
            self.ax.text(
                0.5, 0.5, "CAUDAL NULO!",
                transform=self.ax.transAxes, ha="center", va="center",
                color="red",
                fontsize=22, fontweight="bold",
                bbox=dict(facecolor="red", alpha=0.15, edgecolor="red", boxstyle="round,pad=0.6")
            )
            self.ax.set_ylim(bottom=0, top=max(Hs)*1.2)

        else:
            H_inst = [self.H_inst_lps(q, k_lps, s, kvmax, open_pct) for q in Q_plot]
            self.ax.plot(Q_plot, H_inst_base, linestyle="--", label=r"CCI sin válvula (apertura 100%)", linewidth=1.5)
            self.ax.plot(Q_plot, H_inst, label=rf"CCI con válvula (apertura {open_pct:.0f}%)", linewidth=2)
            self.ax.plot(Qs, Hs, "o-", label=r"CC bomba (1490 rpm)", linewidth=2, color="tab:green")
            if Qpf is not None and Hpf is not None:
                self.ax.plot([Qpf], [Hpf], "s", markersize=8, label=r"Punto de funcionamiento", color="tab:red")

        # Cota piezométrica
        self.ax.axhline(self.delta_z, linestyle=":", linewidth=1, color="gray")
        self.ax.text(Q_plot.max()*0.02, self.delta_z+0.5, "Cota piezométrica", fontsize=9, color="gray")

        self.ax.legend(); self.canvas.draw_idle()

    def aplicar_presion_B(self):
        parsed = self._parse_inputs()
        if not parsed:
            messagebox.showinfo("Primero calcula", "Calcula a) b) c) antes de aplicar d).")
            return
        s, nu, D1m, L1, D2m, L2, eps_cm, open_pct, kvmax = parsed

        if self.k_lps is None:
            messagebox.showinfo("Primero calcula", "Calcula a) b) c) antes de aplicar d).")
            return
        txt = self.PB_var.get().strip()
        if txt == "":
            messagebox.showinfo("Sin PB", "No has introducido PB manométrica.")
            return
        try:
            PB = float(txt.replace(",", "."))
        except Exception:
            messagebox.showerror("Error", "PB no es un número válido.")
            return

        dH0 = 10.0 * PB / s  # mcl

        def H_inst_pres(q): return self.H_inst_lps(q, self.k_lps, s, kvmax, open_pct, dH0=dH0)
        def equilibrio(q):  return H_bomba(q) - H_inst_pres(q)

        Qpf2 = bisect_root(equilibrio, 0.0, 65.0, tol=1e-8)
        
        # Recuperamos PB_lim
        Hb0 = H_bomba(0.0)
        dH0_lim_m = max(Hb0 - self.delta_z, 0.0)
        PB_lim_kPa = 9800.0 * s * dH0_lim_m / 1000.0
        PB_lim_kgcm2 = s * dH0_lim_m / 10.0
        
        # Texto para parte E
        str_e = (
            f"[e] PB_límite en el depósito B (umbral sin circulación):\n"
            f"    PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm² (≈ {PB_lim_kPa:.0f} kPa).\n"
        )

        # Actualizamos el cuadro derecho (d y e)
        if Qpf2 is None:
            str_d = f"[d] Con depósito B presurizado:\n    PB = {PB:.3f} kg/cm² → ΔH0 ≈ {dH0:.2f} mcl.\n    No hay intersección (PB excesiva)."
        else:
            Hpf2 = H_bomba(Qpf2); eta2 = eta_bomba(Qpf2)
            gamma = 9800.0 * s
            Pabs2_kW = gamma*(Qpf2/1000.0)*Hpf2/max(eta2,1e-9)/1000.0
            str_d = (
                f"[d] Con depósito B presurizado:\n"
                f"    PB = {PB:.3f} kg/cm² → ΔH0 ≈ {dH0:.2f} mcl.\n"  # <--- ¡Línea recuperada!
                f"    Q' = {Qpf2:.2f} l/s, H' = {Hpf2:.2f} m\n"
                f"    P'_abs ≈ {Pabs2_kW:.2f} kW"
            )
            
        self._set_text(self.txt_res_de, f"{str_d}\n\n{str_e}")

        # ---- Gráfica con PB ----
        self.ax.cla(); self.ax.grid(True)
        self.ax.set_xlabel(r"$Q$ (L/s)"); self.ax.set_ylabel(r"$H_m$ (m.c.l.)")
        self.ax.set_title("Efecto de presurizar el depósito B")
        Q_plot = self.Q_plot
        base = [self.H_inst_lps(q, self.k_lps, s, kvmax, open_pct) for q in Q_plot]
        shift= [H_inst_pres(q) for q in Q_plot]
        
        self.ax.plot(Q_plot, base,  label="CCI instalación", linewidth=2)
        self.ax.plot(Q_plot, shift, label="CCI con PB", linewidth=2)
        self.ax.plot(Qb_ls, Hb_m, "o-", label="CC bomba (1490 rpm)", linewidth=2, color="tab:green")
        
        if self.last_Qpf is not None:
            self.ax.plot([self.last_Qpf], [self.last_Hpf], "s", markersize=8, label="Punto base")
        if Qpf2 is not None:
            self.ax.plot([Qpf2], [H_bomba(Qpf2)], "D", markersize=8, label="Punto con PB")
        self.ax.legend(); self.canvas.draw_idle()
    
    # -------------------- Utilidades UI -------------------- #
    def reset_valores(self):
        # 1. Variables inputs
        self.s_var.set("1.2")
        self.nu_var.set("1e-6")
        self.D1_var.set("200")
        self.L1_var.set("200")
        self.D2_var.set("150")
        self.L2_var.set("500")
        self.eps_var.set("0.01")
        self.open_var.set("100")
        self.PB_var.set("")
        
        # 2. Reset Dashboard
        self.res_a_chw.set("-")
        self.res_a_ecuacion.set("Pendiente de cálculo")
        self.res_b_apertura.set("- %")
        self.res_b_kvmax.set("-")
        self.res_b_Q.set("--.--")
        self.res_b_H.set("--.--")
        self.res_b_Eta.set("--.-")
        self.res_c_Pabs.set("--.--")
        self.res_e_dH0.set("-")
        self.res_e_PB.set("-")
        self.res_status.set("Valores restaurados. Pulsa Calcular.")
        
        # 3. Reset Textboxes Panel Izquierdo
        self._set_text(self.txt_res_abc, "Pendiente de cálculo…\n")
        self._set_text(self.txt_res_de, "d) Introduce PB y pulsa el botón.\n(e) Disponible tras aplicar d).\n")
        
        for row in self.tree.get_children(): self.tree.delete(row)
        
        self._draw_static_ccb()
        self.k_lps = None
        self.d_btn.configure(state="disabled")

    def exportar_csv(self):
        if self.k_lps is None:
            messagebox.showinfo("Nada que exportar", "Calcula primero.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar tabla como CSV",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="tabla_Hmi.csv",
        )
        if not path: return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write("Q_lps,Hmi_m\n")
                for item in self.tree.get_children():
                    q, h = self.tree.item(item, "values")
                    f.write(f"{q},{h}\n")
            messagebox.showinfo("OK", f"CSV guardado en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

    def guardar_grafica(self):
        path = filedialog.asksaveasfilename(
            title="Guardar gráfica",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")],
            initialfile="curvas_9_1.png",
        )
        if not path: return
        try:
            self.fig.savefig(path, dpi=200, bbox_inches="tight")
            messagebox.showinfo("OK", f"Gráfica guardada en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))
    
    def _volver_menu(self):
        """Cierra esta ventana y abre el menú principal"""
        import subprocess
        import sys
        self.destroy()
        script_path = os.path.join(os.path.dirname(__file__), "menu_principal.py")
        subprocess.Popen([sys.executable, script_path])

def main():
    App().mainloop()

if __name__ == "__main__":
    main()