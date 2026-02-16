# -*- coding: utf-8 -*-
"""
TFG – Problema 9.2: Fuente de chorro vertical
Interfaz gráfica para el diseño de una fuente con bomba centrífuga.
Incluye selección de rodete, cálculo de pérdidas y visualización
del chorro en tiempo real.
"""

import numpy as np
import customtkinter as ctk
from tkinter import messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ---------------- Utilidades hidráulicas ---------------- #
def hazen_williams_k_per_length(D_m: float, C: float) -> float:
    """hf = k_L * L * Q^1.852  (Q en m3/s, L en m, hf en m)"""
    return 10.67 / (C**1.852 * D_m**4.87)

def choose_CHW_from_eps_over_D(eps_cm: float, D_m: float) -> float:
    eps_m = eps_cm / 100.0
    r = eps_m / D_m
    if r <= 1.5e-5: return 150.0
    if r <= 2.0e-4: return 140.0
    if r <= 1.0e-3: return 130.0
    if r <= 4.0e-3: return 120.0
    if r <= 1.5e-2: return 110.0
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

# ----------- Curva base de bomba (IBS 9.2 ~ rodete 256 mm) ----------- #
Qb_base_ls = np.array([40, 50, 60, 70, 80, 90], dtype=float)  # l/s
Hb_base_m  = np.array([22, 22, 22, 21.8, 21.0, 19.7], dtype=float)  # m
eta_base   = np.array([0.72, 0.76, 0.79, 0.78, 0.76, 0.72], dtype=float)  # fracción
D_BASE_MM  = 256.0

RODETES_MM = [225.0, 235.0, 245.0, 256.0, 266.0]

def gen_curve_for_diameter(D_mm: float):
    r = D_mm / D_BASE_MM
    Q_ls = Qb_base_ls * r
    H_m  = Hb_base_m * (r**2)
    eta  = eta_base.copy()
    return Q_ls, H_m, eta

# ============================ GUI ============================ #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Problema nº2: Fuente de Chorro")
        self.geometry("1280x900")
        self.minsize(1120, 800)
        
        # Maximizar ventana
        self.after(0, lambda: self.state('zoomed'))

        self.Q_plot = np.linspace(0.0, 100.0, 400)  # l/s
        self._update_job = None

        # Estado de bomba activa
        self.active_D = 256.0
        self.pump_curves = {D: gen_curve_for_diameter(D) for D in RODETES_MM}

        # Fuentes
        self.font_h1 = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=14)
        
        # Variables para Dashboard (Resultados)
        self.res_Q = ctk.StringVar(value="-")
        self.res_H = ctk.StringVar(value="-")
        self.res_Eta = ctk.StringVar(value="-")
        self.res_Pot = ctk.StringVar(value="-")
        self.res_hChorro = ctk.StringVar(value="-")  # NUEVO: altura del chorro
        self.res_Coste = ctk.StringVar(value="-")
        self.res_Coste_Hora = ctk.StringVar(value="-")
        self.res_Bomba = ctk.StringVar(value="-")
        self.res_DeltaH = ctk.StringVar(value="-")

        # Pestañas
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_inter = self.tabs.add("Interactivo")
        self.tab_res   = self.tabs.add("Resultados")
        self.tab_notas = self.tabs.add("Notas")
        
        # Botón volver al menú
        self.back_btn = ctk.CTkButton(self, text="← Volver al Menú", 
                                       command=self._volver_menu,
                                       width=140, height=32,
                                       fg_color="#666666", hover_color="#444444")
        self.back_btn.place(x=10, y=10)

        self._build_interactivo()
        self._build_resultados_dashboard()
        self._build_notas()

        self._draw_static()

    # ---------------- pequeños helpers UI ---------------- #
    def _flash(self, widget, color=("#FFF4CC", "#3A2F00"), dur_ms=150):
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

    def _schedule_recalc(self):
        if self._update_job is not None:
            try: self.after_cancel(self._update_job)
            except Exception: pass
        self._update_job = self.after(150, self.calcular)

    # -------------------- TAB: INTERACTIVO -------------------- #
    def _build_interactivo(self):
        root = ctk.CTkFrame(self.tab_inter)
        root.pack(fill="both", expand=True, padx=8, pady=8)
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # Columna izquierda con dos filas: controles scroll + botones fijos
        leftcol = ctk.CTkFrame(root)
        leftcol.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        leftcol.grid_rowconfigure(0, weight=1)  # scrollable ocupa todo
        leftcol.grid_rowconfigure(1, weight=0)  # botones fijos abajo
        leftcol.grid_columnconfigure(0, weight=1)

        # Controles scrollables
        controls = ctk.CTkFrame(leftcol, width=440)
        controls.grid(row=0, column=0, sticky="nsew")

        # Variables por defecto
        # Geometricas (FIJAS)
        self.geo_vals = dict(z="3.00", Dp="175", Le="75", eps="0.015", Dc="80", kc="0.8", s="1.0")
        
        # Variables operativas (SLIDERS)
        self.defaults = dict(h8="8.0", hobj="8.0", precio="0.11")
        self.h8_var     = ctk.StringVar(value=self.defaults["h8"])
        self.hobj_var   = ctk.StringVar(value=self.defaults["hobj"])
        self.precio_var = ctk.StringVar(value=self.defaults["precio"])

        # 1. SECCIÓN DATOS FIJOS (Solo Lectura)
        ctk.CTkLabel(controls, text="Datos del Enunciado (Fijos)", font=self.font_h1).pack(anchor="w", padx=8, pady=(8, 6))
        
        fixed_frame = ctk.CTkFrame(controls, fg_color="#F8F8F8", corner_radius=6)
        fixed_frame.pack(fill="x", padx=8, pady=(0, 10))
        
        # Grid para datos fijos
        for i, (lbl, val, unit) in enumerate([
            ("Cota z (A)", self.geo_vals["z"], "m"),
            ("Dens. rel. s", self.geo_vals["s"], "-"),
            ("D tubería",  self.geo_vals["Dp"], "mm"),
            ("L equiv.",   self.geo_vals["Le"], "m"),
            ("Rugosidad ε",self.geo_vals["eps"], "cm"),
            ("D boquilla", self.geo_vals["Dc"], "mm"),
            ("k boquilla", self.geo_vals["kc"], "-")
        ]):
            r, c = divmod(i, 2)
            f = ctk.CTkFrame(fixed_frame, fg_color="transparent")
            f.grid(row=r, column=c, sticky="ew", padx=10, pady=5)
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont(size=12, weight="bold"), text_color="gray").pack(anchor="w")
            ctk.CTkLabel(f, text=f"{val} {unit}", font=ctk.CTkFont(size=14), text_color="#333").pack(anchor="w")
        
        fixed_frame.grid_columnconfigure((0,1), weight=1)

        # 2. SECCIÓN VARIABLES (Sliders)
        ctk.CTkLabel(controls, text="Variables de Diseño", font=self.font_h1).pack(anchor="w", padx=8, pady=(8, 6))

        def add_entry_slider(parent, label, var, unit, vmin, vmax, step, fmt):
            row = ctk.CTkFrame(parent); row.pack(fill="x", padx=6, pady=(6,0))
            ctk.CTkLabel(row, text=label, font=self.font_body).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=unit,  font=self.font_body).grid(row=0, column=2, sticky="w", padx=(6,0))

            sframe = ctk.CTkFrame(parent); sframe.pack(fill="x", padx=6, pady=(2,10))
            sframe.grid_columnconfigure(0, weight=1)

            slider = ctk.CTkSlider(
                sframe, from_=vmin, to=vmax,
                number_of_steps=max(1, int(round((vmax-vmin)/step)))
            )
            try: init = float(str(var.get()).replace(",", "."))
            except: init = vmin
            slider.set(min(max(init, vmin), vmax))
            slider.grid(row=0, column=0, sticky="ew", padx=(4,6), pady=2)

            ent = ctk.CTkEntry(sframe, textvariable=var, width=80, justify="right")
            ent.grid(row=0, column=1, sticky="e")

            def on_slide(val):
                var.set(fmt.format(val)); self._schedule_recalc()
            slider.configure(command=on_slide)

            def on_entry_change(*_):
                try: 
                    x = float(str(var.get()).replace(",", "."))
                    slider.set(min(max(x, vmin), vmax))
                    self._schedule_recalc()
                except: pass
            var.trace_add("write", on_entry_change)
            
            return slider

        # Sliders solicitados (sin densidad, ahora es fija)
        self.slider_h8 = add_entry_slider(controls, "h mínima (b)",      self.h8_var, "m",     5.00, 10.0, 0.10, "{:.2f}")
        self.slider_hobj = add_entry_slider(controls, "h objetivo (d)",    self.hobj_var,"m",    5.00, 10.0, 0.10, "{:.2f}")
        self.slider_precio = add_entry_slider(controls, "Precio energía",    self.precio_var,"€/kWh", 0.00, 0.50, 0.01, "{:.2f}")

        # Sincronizar h_objetivo con h_minima
        def sync_hobj_to_h8(*args):
            """Cuando cambia h_objetivo, actualizar h_minima (valor Y slider)"""
            try:
                hobj_val = float(self.hobj_var.get().replace(",", "."))
                self.h8_var.set(f"{hobj_val:.2f}")
                self.slider_h8.set(hobj_val)  # Mover también el slider de h_minima
            except:
                pass
        
        self.hobj_var.trace_add("write", sync_hobj_to_h8)

        # Barra de bombas (debajo de sliders)
        self.pump_bar = ctk.CTkFrame(controls); self.pump_bar.pack(fill="x", padx=6, pady=(8,4))
        ctk.CTkLabel(self.pump_bar, text="Bombas disponibles:", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.pump_labels = {}
        row_pump = ctk.CTkFrame(self.pump_bar); row_pump.pack(fill="x")
        for D in RODETES_MM:
            lbl = ctk.CTkLabel(row_pump, text=f"{int(D)}", corner_radius=6, width=40, font=ctk.CTkFont(size=11))
            lbl.pack(side="left", padx=2, pady=2)
            self.pump_labels[D] = lbl

        # Botonera fija (no scroll)
        btnrow = ctk.CTkFrame(leftcol)
        btnrow.grid(row=1, column=0, sticky="ew", pady=(8,0))
        btnrow.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btnrow, text="Calcular", command=self.calcular).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btnrow, text="Reiniciar valores", command=self.reiniciar_valores).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btnrow, text="Guardar gráfica", command=self.guardar_grafica).grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        # Lado derecho: gráfica + resultados
        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=4)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Gráfica: dos subplots, curvas y chorro
        g = ctk.CTkFrame(right); g.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4,2))
        self.fig = plt.Figure(figsize=(7.2, 4.9))
        gs = self.fig.add_gridspec(1, 2, width_ratios=[2.0, 1.0])
        self.ax  = self.fig.add_subplot(gs[0, 0])    # Q-H
        self.ax_jet = self.fig.add_subplot(gs[0, 1]) # chorro
        self.canvas = FigureCanvasTkAgg(self.fig, master=g)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Badge dinámico
        self.badge_artist = None

        # Resultados organizados (A,B | C | D)
        res = ctk.CTkFrame(right); res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1); res.grid_columnconfigure(1, weight=1); res.grid_columnconfigure(2, weight=1)
        
        # Columna Izquierda (A y B)
        c_left = ctk.CTkFrame(res, fg_color="transparent"); c_left.grid(row=0, column=0, sticky="nsew", padx=4)
        ctk.CTkLabel(c_left, text="A) Instalación y B) Selección", font=self.font_h2).pack(anchor="w", pady=2)
        self.txt_ab = ctk.CTkTextbox(c_left, font=self.font_body, activate_scrollbars=False)
        self.txt_ab.pack(fill="both", expand=True, pady=2)
        
        # Columna Central (C)
        c_mid = ctk.CTkFrame(res, fg_color="transparent"); c_mid.grid(row=0, column=1, sticky="nsew", padx=4)
        ctk.CTkLabel(c_mid, text="C) Punto de Funcionamiento", font=self.font_h2).pack(anchor="w", pady=2)
        self.txt_c = ctk.CTkTextbox(c_mid, font=self.font_body, activate_scrollbars=False)
        self.txt_c.pack(fill="both", expand=True, pady=2)
        
        # Columna Derecha (D)
        c_right = ctk.CTkFrame(res, fg_color="transparent"); c_right.grid(row=0, column=2, sticky="nsew", padx=4)
        ctk.CTkLabel(c_right, text="D) Regulación", font=self.font_h2).pack(anchor="w", pady=2)
        self.txt_d = ctk.CTkTextbox(c_right, font=self.font_body, activate_scrollbars=False)
        self.txt_d.pack(fill="both", expand=True, pady=2)

        # Inicializar textos
        for tb in (self.txt_ab, self.txt_c, self.txt_d):
            tb.insert("end", "Calculando...\n"); tb.configure(state="disabled")

    # -------------------- TAB: RESULTADOS (DASHBOARD) -------------------- #
    def _build_resultados_dashboard(self):
        self.dash = ctk.CTkScrollableFrame(self.tab_res, fg_color="#F5F5F5")
        self.dash.pack(fill="both", expand=True, padx=10, pady=10)

        # KPI Helper con fondos de color
        def create_kpi(parent, label, variable, unit, col, colspan=1, color="#1F6AA5", bg_color="#FFFFFF", icon=""):
            f = ctk.CTkFrame(parent, fg_color=bg_color, corner_radius=12, border_width=2, border_color="#E0E0E0")
            f.grid(row=0, column=col, columnspan=colspan, sticky="ew", padx=8, pady=8)
            for i in range(colspan):
                parent.grid_columnconfigure(col+i, weight=1)
            
            # Icono y label
            header = ctk.CTkFrame(f, fg_color="transparent")
            header.pack(pady=(12,0))
            if icon:
                ctk.CTkLabel(header, text=icon, font=ctk.CTkFont(size=16)).pack(side="left", padx=(0,4))
            ctk.CTkLabel(header, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#666").pack(side="left")
            
            # Valor principal
            ctk.CTkLabel(f, textvariable=variable, font=ctk.CTkFont(size=32, weight="bold"), text_color=color).pack(pady=(2,2))
            
            # Unidad
            ctk.CTkLabel(f, text=unit, font=ctk.CTkFont(size=13), text_color="#999").pack(pady=(0,12))
            
            return f

        # Tarjeta 1: Punto de Funcionamiento (Púrpura)
        card1 = ctk.CTkFrame(self.dash, fg_color="transparent")
        card1.pack(fill="x", pady=(0,15))
        
        header1 = ctk.CTkFrame(card1, fg_color="#9B59B6", corner_radius=8, height=50)
        header1.pack(fill="x", pady=(0,10))
        header1.pack_propagate(False)
        ctk.CTkLabel(header1, text="⚙️  PUNTO DE FUNCIONAMIENTO", font=self.font_h1, text_color="white").pack(pady=12)
        
        grid1 = ctk.CTkFrame(card1, fg_color="transparent")
        grid1.pack(fill="x")
        create_kpi(grid1, "CAUDAL", self.res_Q, "l/s", 0, color="#9B59B6", bg_color="#E8D5F0", icon="💧")
        create_kpi(grid1, "ALTURA", self.res_H, "m", 1, color="#9B59B6", bg_color="#E8D5F0", icon="📏")
        create_kpi(grid1, "RENDIMIENTO", self.res_Eta, "%", 2, color="#9B59B6", bg_color="#E8D5F0", icon="⚡")
        create_kpi(grid1, "ALTURA CHORRO", self.res_hChorro, "m", 3, color="#9B59B6", bg_color="#E8D5F0", icon="⛲")
        
        # Tarjeta 2: Energía y Costes (Naranja)
        card2 = ctk.CTkFrame(self.dash, fg_color="transparent")
        card2.pack(fill="x", pady=(0,15))
        
        header2 = ctk.CTkFrame(card2, fg_color="#FF9800", corner_radius=8, height=50)
        header2.pack(fill="x", pady=(0,10))
        header2.pack_propagate(False)
        ctk.CTkLabel(header2, text="💰  ENERGÍA Y COSTES", font=self.font_h1, text_color="white").pack(pady=12)
        
        grid2 = ctk.CTkFrame(card2, fg_color="transparent")
        grid2.pack(fill="x")
        create_kpi(grid2, "POTENCIA", self.res_Pot, "kW", 0, color="#FF9800", bg_color="#FFE0B2", icon="⚡")
        create_kpi(grid2, "COSTE/VOLUMEN", self.res_Coste, "€/m³", 1, color="#FF9800", bg_color="#FFE0B2", icon="💵")
        create_kpi(grid2, "COSTE/HORA", self.res_Coste_Hora, "€/h", 2, color="#FF9800", bg_color="#FFE0B2", icon="🕐")
        
        # Tarjeta 3: Equipamiento (Azul)
        card3 = ctk.CTkFrame(self.dash, fg_color="transparent")
        card3.pack(fill="x", pady=(0,15))
        
        header3 = ctk.CTkFrame(card3, fg_color="#2196F3", corner_radius=8, height=50)
        header3.pack(fill="x", pady=(0,10))
        header3.pack_propagate(False)
        ctk.CTkLabel(header3, text="🔧  EQUIPAMIENTO Y REGULACIÓN", font=self.font_h1, text_color="white").pack(pady=12)
        
        grid3 = ctk.CTkFrame(card3, fg_color="transparent")
        grid3.pack(fill="x")
        
        # KPI de bombas con selector visual
        f_bomba = ctk.CTkFrame(grid3, fg_color="#BBDEFB", corner_radius=12, border_width=2, border_color="#E0E0E0")
        f_bomba.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        grid3.grid_columnconfigure(0, weight=1)
        
        header_bomba = ctk.CTkFrame(f_bomba, fg_color="transparent")
        header_bomba.pack(pady=(12,0))
        ctk.CTkLabel(header_bomba, text="🔄", font=ctk.CTkFont(size=16)).pack(side="left", padx=(0,4))
        ctk.CTkLabel(header_bomba, text="BOMBA SELECCIONADA", font=ctk.CTkFont(size=11, weight="bold"), text_color="#666").pack(side="left")
        
        # Contenedor de bombas
        self.pump_display_frame = ctk.CTkFrame(f_bomba, fg_color="transparent")
        self.pump_display_frame.pack(pady=(8,12))
        
        # Crear labels para cada bomba (se actualizarán en calcular)
        self.pump_display_labels = {}
        for D in RODETES_MM:
            lbl = ctk.CTkLabel(self.pump_display_frame, text=f"{int(D)}", 
                              font=ctk.CTkFont(size=16), text_color="#999")
            lbl.pack(side="left", padx=4)
            self.pump_display_labels[D] = lbl
        
        # ΔH con color dinámico (se actualizará en calcular)
        self.kpi_deltah = create_kpi(grid3, "REGULACIÓN VÁLVULA (ΔH)", self.res_DeltaH, "m", 1, colspan=2, color="#4CAF50", bg_color="#C8E6C9", icon="🎚️")



    # -------------------- TAB: NOTAS -------------------- #
    def _build_notas(self):
        main = ctk.CTkScrollableFrame(self.tab_notas, fg_color="#F5F5F5")
        main.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Título principal
        title_frame = ctk.CTkFrame(main, fg_color="#3F51B5", corner_radius=10, height=60)
        title_frame.pack(fill="x", pady=(0,20))
        title_frame.pack_propagate(False)
        ctk.CTkLabel(title_frame, text="📚  NOTAS TÉCNICAS - PROBLEMA 9.2", 
                    font=ctk.CTkFont(size=22, weight="bold"), text_color="white").pack(pady=15)
        
        # Sección 1: Ecuación de la Instalación
        card1 = ctk.CTkFrame(main, fg_color="white", corner_radius=12, border_width=2, border_color="#E0E0E0")
        card1.pack(fill="x", pady=(0,15))
        
        header1 = ctk.CTkFrame(card1, fg_color="#E3F2FD", corner_radius=8)
        header1.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header1, text="🔵  CURVA CARACTERÍSTICA DE LA INSTALACIÓN (CCI)", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#1976D2").pack(pady=8, padx=10)
        
        content1 = ctk.CTkLabel(card1, 
                               text="La altura manométrica de la instalación se calcula como:\n\n"
                                    "   H_mi(Q) = z + (1 + k_c)·(V_c²/2g) + hf_tubería(Q)\n\n"
                                    "Donde:\n"
                                    "  • z: Cota geométrica (altura estática)\n"
                                    "  • V_c²/2g: Altura de velocidad en la boquilla = k_v2g·Q²\n"
                                    "  • hf_tubería: Pérdidas por fricción (Hazen-Williams)",
                               font=ctk.CTkFont(family="Consolas", size=13), 
                               text_color="#333", justify="left")
        content1.pack(fill="x", padx=15, pady=(0,15), anchor="w")
        
        # Sección 2: Pérdidas en tubería
        card2 = ctk.CTkFrame(main, fg_color="white", corner_radius=12, border_width=2, border_color="#E0E0E0")
        card2.pack(fill="x", pady=(0,15))
        
        header2 = ctk.CTkFrame(card2, fg_color="#FFF3E0", corner_radius=8)
        header2.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header2, text="🟠  PÉRDIDAS POR FRICCIÓN (HAZEN-WILLIAMS)", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#F57C00").pack(pady=8, padx=10)
        
        content2 = ctk.CTkLabel(card2,
                               text="Las pérdidas por fricción se calculan con:\n\n"
                                    "   hf_tubería = (J_ℓ · L) · Q^1.852\n\n"
                                    "Donde J_ℓ es el coeficiente unitario de Hazen-Williams\n"
                                    "que depende del diámetro D y el coeficiente C_HW (rugosidad).",
                               font=ctk.CTkFont(family="Consolas", size=13),
                               text_color="#333", justify="left")
        content2.pack(fill="x", padx=15, pady=(0,15), anchor="w")
        
        # Sección 3: Selección de bomba
        card3 = ctk.CTkFrame(main, fg_color="white", corner_radius=12, border_width=2, border_color="#E0E0E0")
        card3.pack(fill="x", pady=(0,15))
        
        header3 = ctk.CTkFrame(card3, fg_color="#E8F5E9", corner_radius=8)
        header3.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header3, text="🟢  SELECCIÓN DE BOMBA (APARTADO B)", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#388E3C").pack(pady=8, padx=10)
        
        content3 = ctk.CTkLabel(card3,
                               text="Criterio de selección:\n\n"
                                    "1. Calcular Q_min a partir de h_mínima: Q_min = √(h_min / k_v2g)\n"
                                    "2. Calcular H_requerida en ese caudal\n"
                                    "3. Seleccionar la bomba MÁS PEQUEÑA que cumpla:\n"
                                    "      H_bomba(Q_min) ≥ H_requerida",
                               font=ctk.CTkFont(family="Consolas", size=13),
                               text_color="#333", justify="left")
        content3.pack(fill="x", padx=15, pady=(0,15), anchor="w")
        
        # Sección 4: Regulación con válvula
        card4 = ctk.CTkFrame(main, fg_color="white", corner_radius=12, border_width=2, border_color="#E0E0E0")
        card4.pack(fill="x", pady=(0,15))
        
        header4 = ctk.CTkFrame(card4, fg_color="#F3E5F5", corner_radius=8)
        header4.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(header4, text="🟣  REGULACIÓN CON VÁLVULA (APARTADO D)", 
                    font=ctk.CTkFont(size=14, weight="bold"), text_color="#7B1FA2").pack(pady=8, padx=10)
        
        content4 = ctk.CTkLabel(card4,
                               text="Para alcanzar una altura objetivo h_obj:\n\n"
                                    "1. Calcular Q_obj = √(h_obj / k_v2g)\n"
                                    "2. Determinar H_bomba(Q_obj) y H_sistema(Q_obj)\n"
                                    "3. La válvula debe disipar:\n"
                                    "      ΔH = H_bomba(Q_obj) - H_sistema(Q_obj)\n\n"
                                    "Si ΔH < 0 → IMPOSIBLE (bomba insuficiente)",
                               font=ctk.CTkFont(family="Consolas", size=13),
                               text_color="#333", justify="left")
        content4.pack(fill="x", padx=15, pady=(0,15), anchor="w")
        
        # Footer con información adicional
        footer = ctk.CTkFrame(main, fg_color="#ECEFF1", corner_radius=10)
        footer.pack(fill="x", pady=(5,0))
        ctk.CTkLabel(footer, text="💡 Tip: Usa los sliders en la pestaña 'Interactivo' para explorar diferentes configuraciones", 
                    font=ctk.CTkFont(size=12, slant="italic"), text_color="#546E7A").pack(pady=12, padx=15)



    # -------------------- Dibujo del chorro -------------------- #
    def _draw_jet(self, h_jet_m: float, h_obj_m: float | None = None):
        ax = self.ax_jet
        ax.cla()

        ymax = max(5.0, h_jet_m, h_obj_m or 0.0) * 1.2
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.6, 0.6)
        ax.set_aspect('auto')
        ax.set_xticks([])
        ax.set_ylabel(r"$H$ (m)")
        ax.set_title("Chorro")

        # Suelo y boquilla
        ax.plot([-0.5, 0.5], [0, 0], linewidth=2)
        ax.add_patch(plt.Rectangle((-0.1, 0.0), 0.2, 0.12, fill=True))

        # Chorro en azul
        ax.plot([0, 0], [0, h_jet_m], linewidth=6, alpha=0.85, solid_capstyle="round", color="tab:blue")

        # Cota
        ax.annotate("", xy=(0.35, h_jet_m), xytext=(0.35, 0), arrowprops=dict(arrowstyle="<->", lw=1.8))
        ax.text(0.38, h_jet_m/2, rf"$h={h_jet_m:.2f}$ m", va="center", rotation=90, bbox=dict(facecolor="white", alpha=0.6))

        # Objetivo
        if h_obj_m is not None:
            ax.axhline(h_obj_m, linestyle="--", linewidth=1.2, color="red")
            ax.text(-0.55, h_obj_m, rf"Obj$={h_obj_m:.2f}$ m", va="center", color="red")

        if h_obj_m is not None and h_jet_m < h_obj_m:
            ax.text(0, ymax*0.92, "⚠ Altura insuficiente", color="red", ha="center", va="top", fontsize=10, weight="bold")

    # -------------------- Dibujo base -------------------- #
    def _draw_static(self):
        self._plot_with_zoom(None, None)

    def _plot_with_zoom(self, Qpf, Hpf, reg_data=None):
        self.ax.cla()
        self.ax.grid(True, linestyle=":", alpha=0.6)
        self.ax.set_xlabel(r"$Q$ (L/s)")
        self.ax.set_ylabel(r"$H$ (m)")
        self.ax.set_title("Familia de Bombas vs Instalación")

        # Configurar limites Zoom o Full
        if Qpf is not None:
            span_q = 55; span_h = 25
            x_min = max(0, Qpf - span_q/2)
            x_max = x_max_raw = x_min + span_q
            
            y_min = max(0, Hpf - span_h/2)
            y_max = y_min + span_h
            
            # Si hay regulación, expandir vista para incluir toda la línea roja
            if reg_data:
                Qo, H_sys_o, H_pump_o = reg_data
                # Expandir X
                if Qo < x_min: x_min = max(0, Qo - 5)
                if Qo > x_max: x_max = Qo + 5
                # Expandir Y (con margen para texto)
                if H_sys_o < y_min: y_min = max(0, H_sys_o - 2)
                if H_pump_o > y_max: y_max = H_pump_o + 4 # margen superior para texto deltaH

            self.ax.set_xlim(x_min, x_max)
            self.ax.set_ylim(y_min, y_max)
        else:
            x_min, x_max = 0, 100
            self.ax.set_xlim(0, 100)
            self.ax.set_ylim(0, 45)

        # Dibujar TODAS las bombas con etiquetas distribuidas
        for idx, D in enumerate(RODETES_MM):
            Qc, Hc, _ = self.pump_curves[D]
            
            if D == self.active_D:
                color = "tab:orange"; lw = 3; ls = "-"
                lbl_legend = "Bomba Activa"
            else:
                color = "gray"; lw = 1; ls = "--"
                lbl_legend = None 
                
            self.ax.plot(Qc, Hc, ls=ls, lw=lw, color=color, alpha=0.6, label=lbl_legend)
            
            # Etiqueta: usar diferentes posiciones X para evitar solapamiento
            # Distribuir entre 70% y 95% del rango visible
            x_range = x_max - x_min
            # Posicionar cada etiqueta en un punto diferente de la curva
            label_x_fraction = 0.70 + (idx * 0.06)  # 0.70, 0.76, 0.82, 0.88, 0.94
            x_lbl = x_min + x_range * label_x_fraction
            
            # Verificar que x_lbl esté dentro del rango de la curva Y del viewport
            # Usar un rango más amplio para asegurar visibilidad
            if Qc[0] <= x_lbl <= Qc[-1]:
                y_lbl = interp_xy(Qc, Hc, x_lbl)
                ylim = self.ax.get_ylim()
                # Rango más permisivo para asegurar que las etiquetas aparezcan
                if (ylim[0] - 8) <= y_lbl <= (ylim[1] + 8):
                    self.ax.text(x_lbl, y_lbl, f"R-{int(D)}", 
                                 fontsize=8, color=color, va="bottom", ha="center", 
                                 weight="bold", clip_on=False,  # clip_on=False para forzar visibilidad
                                 bbox=dict(boxstyle="round,pad=0.3", facecolor="white", 
                                          edgecolor=color, alpha=0.8, linewidth=0.5))

        # Si hay Qpf, dibujar CCI y Punto
        if Qpf is not None:
            parsed = self._parse_and_get_params()
            if parsed:
                 _, _, J_lps, Le, kv2g, kc, z = parsed
                 Hcci = [z + (1+kc)*kv2g*(q**2) + (J_lps*Le)*(q**1.852) for q in self.Q_plot]
                 self.ax.plot(self.Q_plot, Hcci, "-", linewidth=2, color="tab:blue", label=r"Curva Sistema")
                 
                 # Punto de funcionamiento con color magenta suave
                 self.ax.plot([Qpf], [Hpf], "o", markersize=12, color="#9B59B6", 
                              markeredgecolor="white", markeredgewidth=2.5, zorder=11, label=r"Pto. Funcionamiento")
                 
                 # LINEA DE REGULACION (d) - SIEMPRE VISIBLE EN VERDE
                 if reg_data:
                     Qo, H_sys_o, H_pump_o = reg_data
                     # Línea verde sólida vertical
                     self.ax.vlines(x=Qo, ymin=H_sys_o, ymax=H_pump_o, colors="green", linestyles="-", linewidth=2.5, label=r"Regulación (Válvula)", zorder=9)
                     self.ax.plot([Qo], [H_pump_o], "o", color="green", markersize=6, zorder=10)
                     self.ax.plot([Qo], [H_sys_o], "o", color="green", markersize=6, zorder=10)
                     
                     # Texto delta H centrado o mensaje IMPOSIBLE
                     mid_y = (H_sys_o + H_pump_o)/2
                     delta_h = H_pump_o - H_sys_o
                     
                     # Ajustar alineación según donde esté Qpf
                     ha_txt = "right" if Qo < Qpf else "left"
                     off_x = -1.0 if Qo < Qpf else 1.0
                     
                     # Si delta_h es negativo, mostrar IMPOSIBLE
                     if delta_h < 0:
                         txt_label = "IMPOSIBLE"
                         txt_color = "red"
                         edge_color = "red"
                     else:
                         txt_label = rf"$\Delta H={delta_h:.2f}$ m"
                         txt_color = "green"
                         edge_color = "green"
                     
                     self.ax.text(Qo + off_x, mid_y, txt_label, 
                                  color=txt_color, fontsize=10, ha=ha_txt, va="center", weight="bold",
                                  bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=edge_color, alpha=0.9))

        self.ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
        self.canvas.draw_idle()

    # -------------------- Animación cambio de bomba -------------------- #
    def _animate_pump_switch(self, new_D_mm: float, on_done):
        win = ctk.CTkToplevel(self)
        win.title("CAMBIANDO BOMBA…")
        win.geometry("360x100")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text=f"Seleccionando rodete óptimo: {int(new_D_mm)} mm", font=self.font_h2).pack(pady=(15, 5))
        pb = ctk.CTkProgressBar(win)
        pb.pack(fill="x", padx=20, pady=5)
        pb.set(0.0)

        steps, i = 25, 0 
        def tick():
            nonlocal i
            i += 1
            pb.set(i/steps)
            if i < steps:
                win.after(15, tick)
            else:
                try: win.destroy()
                except: pass
                on_done()
        tick()

    # -------------------- Lógica -------------------- #
    def _parse_and_get_params(self):
        # Lee de Textvars y constantes
        try:
            s = float(self.geo_vals["s"])  # Ahora s es fijo
            # Geo fixed
            z = float(self.geo_vals["z"])
            Dp_m = float(self.geo_vals["Dp"])/1000.0
            Le = float(self.geo_vals["Le"])
            eps_cm = float(self.geo_vals["eps"])
            Dc_m = float(self.geo_vals["Dc"])/1000.0
            kc = float(self.geo_vals["kc"])
            
            # Derived
            C = choose_CHW_from_eps_over_D(eps_cm, Dp_m)
            kL = hazen_williams_k_per_length(Dp_m, C)
            J_lps = kL / (1000.0**1.852)
            
            A = np.pi*(Dc_m**2)/4.0
            kv2g = (1e-6) / (2*9.81*(A**2))
            
            return s, C, J_lps, Le, kv2g, kc, z
        except: return None

    def Hb_activa(self, Ql):
        Qc, Hc, _ = self.pump_curves[self.active_D]
        return interp_xy(Qc, Hc, Ql)

    def eta_activa(self, Ql):
        Qc, _, eta = self.pump_curves[self.active_D]
        return float(interp_xy(Qc, eta, Ql))

    def _update_pump_bar(self):
        for D, lbl in self.pump_labels.items():
            if D == self.active_D:
                lbl.configure(fg_color="#3B8ED0", text_color="white") # Azul activo
            else:
                lbl.configure(fg_color="#E0E0E0", text_color="black")

    def _update_badge(self):
        if self.badge_artist:
            try: self.badge_artist.remove()
            except: pass
        self.badge_artist = self.ax.text(
            0.98, 0.98, f"Rodete {int(self.active_D)}",
            transform=self.ax.transAxes, ha="right", va="top",
            bbox=dict(facecolor="#3B8ED0", alpha=0.9, boxstyle="round,pad=0.3"),
            color="white", weight="bold"
        )

    def calcular(self):
        # 1. Leer inputs
        try:
            s_val = float(self.geo_vals["s"])  # s es fijo ahora
            h8  = float(self.h8_var.get().replace(",", "."))
            hobj= float(self.hobj_var.get().replace(",", "."))
            pr  = float(self.precio_var.get().replace(",", "."))
        except: return 
        
        params = self._parse_and_get_params()
        if not params: return
        s, C, J_lps, Le, kv2g, kc, z = params

        # 2. SELECCIÓN DE BOMBA (Apartado B)
        # H_requerida para Q_min (h8)
        Q_min = np.sqrt(h8 / kv2g)
        H_req_min = z + (1+kc)*kv2g*(Q_min**2) + (J_lps*Le)*(Q_min**1.852)
        
        # Buscar en catálogo
        best_D = RODETES_MM[-1]; found = False
        for D in RODETES_MM:
            Qc, Hc, _ = self.pump_curves[D]
            H_disp = interp_xy(Qc, Hc, Q_min)
            if H_disp >= H_req_min * 1.0: # SIN margen (antes 1.05 = 5%)
                best_D = D
                found = True
                break
        
        # Si cambia bomba, animar y volver
        if best_D != self.active_D:
            self.active_D = best_D
            self._animate_pump_switch(best_D, self.calcular)
            return

        self._update_pump_bar()

        # 3. GUI CHECK (No redibujar excesivamente si es auto-update)
        # Simplemente procedemos al cálculo
        
        # C) PUNTO DE FUNCIONAMIENTO
        def func_bal(q):
            # H_bomba - H_sistema
            H_b = self.Hb_activa(q)
            H_s = z + (1+kc)*kv2g*(q**2) + (J_lps*Le)*(q**1.852)
            return H_b - H_s
        
        Qpf = bisect_root(func_bal, 0.1, 150)
        if Qpf is None: Qpf = 0.0
        
        Hpf = self.Hb_activa(Qpf)
        eta_pf = self.eta_activa(Qpf)
        
        gamma = 9800.0 * s_val
        Pabs_kW = gamma*(Qpf/1000.0)*Hpf / (max(eta_pf, 0.01)) / 1000.0
        coste = (Pabs_kW / (Qpf*3.6)) * pr if Qpf>0 else 0

        # D) REGULACIÓN VÁLVULA
        # Q necesario para h_obj
        Q_obj = np.sqrt(hobj / kv2g)
        H_bomb_obj = self.Hb_activa(Q_obj)
        H_syst_base = z + (1+kc)*kv2g*(Q_obj**2) + (J_lps*Le)*(Q_obj**1.852)
        
        hf_valv = H_bomb_obj - H_syst_base
        aviso_d = ""
        if hf_valv < 0:
            aviso_d = "IMPOSIBLE: Bomba insuficiente para h_obj."
        else:
            aviso_d = f"Válvula debe disipar {hf_valv:.2f} m."

        # --- ACTUALIZAR DASHBOARD ---
        self.res_Q.set(f"{Qpf:.2f}")
        self.res_H.set(f"{Hpf:.2f}")
        self.res_Eta.set(f"{eta_pf*100:.1f}")
        self.res_Pot.set(f"{Pabs_kW:.2f}")
        
        # Altura del chorro (h_chorro = v²/2g = kv2g * Q²)
        h_real = kv2g * (Qpf**2)
        self.res_hChorro.set(f"{h_real:.2f}")
        
        # Coste por m³ = (Potencia * Precio) / (Caudal en m³/h)
        # Q en l/s -> Q en m³/h = Q * 3.6
        Q_m3h = Qpf * 3.6
        coste_m3 = (Pabs_kW * pr / Q_m3h) if Q_m3h > 0 else 0
        self.res_Coste.set(f"{coste_m3:.4f}")
        
        # Coste por hora (más interpretable)
        coste_hora = Pabs_kW * pr if Qpf > 0 else 0
        self.res_Coste_Hora.set(f"{coste_hora:.3f}")
        
        self.res_Bomba.set(f"{int(self.active_D)}")
        
        # Actualizar selector visual de bombas
        for D, lbl in self.pump_display_labels.items():
            if D == self.active_D:
                lbl.configure(text_color="#2196F3", font=ctk.CTkFont(size=20, weight="bold"))
            else:
                lbl.configure(text_color="#999", font=ctk.CTkFont(size=16))
        
        # Delta H para válvula con color dinámico
        delta_h_valv = H_bomb_obj - H_syst_base
        if delta_h_valv >= 0:
            self.res_DeltaH.set(f"{delta_h_valv:.2f}")
            # Actualizar color del KPI a verde
            try:
                self.kpi_deltah.configure(fg_color="#C8E6C9")  # Verde claro
                for widget in self.kpi_deltah.winfo_children():
                    if isinstance(widget, ctk.CTkLabel) and widget.cget("font").cget("size") == 32:
                        widget.configure(text_color="#4CAF50")  # Verde
            except: pass
        else:
            self.res_DeltaH.set("IMPOSIBLE")
            # Actualizar color del KPI a rojo
            try:
                self.kpi_deltah.configure(fg_color="#FFCDD2")  # Rojo claro
                for widget in self.kpi_deltah.winfo_children():
                    if isinstance(widget, ctk.CTkLabel) and widget.cget("font").cget("size") == 32:
                        widget.configure(text_color="#F44336")  # Rojo
            except: pass

        # --- ACTUALIZAR TEXTOS IZQ/DER ---
        # Izquierda: A y B
        txt_a = (
            f"A) INSTALACIÓN:\n"
            f"   Hmi = {z} + {(1+kc)*kv2g:.5f}Q² + {(J_lps*Le):.5f}Q^1.852\n"
            f"   (C-HW: {C:.0f} para ε={self.geo_vals['eps']}cm)\n\n"
            f"B) SELECCIÓN (h_min={h8}m):\n"
            f"   Q_min = {Q_min:.2f} l/s -> H_req = {H_req_min:.2f} m\n"
            f"   Rodete selec.: {int(best_D)} mm {'(Cumple)' if found else '(Max disp.)'}"
        )
        self._set_text(self.txt_ab, txt_a)

        # Derecha: C y D (separados)
        txt_c = (
            f"C) FUNCIONAMIENTO:\n"
            f"   Q = {Qpf:.2f} l/s\n"
            f"   H = {Hpf:.2f} mca\n"
            f"   η = {eta_pf*100:.1f} %\n"
            f"   Pot = {Pabs_kW:.2f} kW\n"
            f"   h_chorro = {h_real:.2f} m\n"
            f"   Coste/volumen= {coste_m3:.4f} €/m³\n"
            f"   Coste/hora= {coste_hora:.3f} €/h"
        )
        txt_d = (
            f"D) REGULACIÓN (h_obj={hobj}m):\n"
            f"   Q_obj = {Q_obj:.2f} l/s\n"
            f"   {aviso_d}"
        )
        self._set_text(self.txt_c, txt_c)
        self._set_text(self.txt_d, txt_d)

        # Gráficas - ΔH siempre visible
        reg_data = (Q_obj, H_syst_base, H_bomb_obj)
        self._plot_with_zoom(Qpf, Hpf, reg_data=reg_data)
        
        # Chorro (ya calculado arriba)
        self._draw_jet(h_real, hobj)

    def reiniciar_valores(self):
        self.h8_var.set(self.defaults["h8"])
        self.hobj_var.set(self.defaults["hobj"])
        self.precio_var.set(self.defaults["precio"])
        self.active_D = 256.0
        self.calcular()

    def guardar_grafica(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if path: 
                self.fig.savefig(path, dpi=150)
                messagebox.showinfo("Guardado", f"Gráfica guardada en {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _volver_menu(self):
        """Cierra esta ventana (el menú ya está abierto de fondo)"""
        self.destroy()

if __name__ == "__main__":
    App().mainloop()
    
def main():
    App().mainloop()
