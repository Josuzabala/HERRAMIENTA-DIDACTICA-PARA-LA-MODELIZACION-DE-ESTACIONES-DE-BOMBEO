# -*- coding: utf-8 -*-
"""
IBS 9.4 – NPSH: Cálculo de Z_D y verificación de cavitación (DOS FASES)

FASE 1: Cálculo de Z_D a partir de parámetros (Q, años, z, T)
FASE 2: Visualización de NPSH_req vs NPSH_disp con alarma de cavitación
"""

import numpy as np
import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

gamma = 9800.0  # N/m³

# Curva NPSHreq(Q) leída de la gráfica (anexo)
ANCHOR_Q = np.array([12, 16, 20, 25, 28, 30], dtype=float)        # L/s
ANCHOR_H = np.array([1.0, 1.8, 3.2, 5.2, 6.5, 8.0], dtype=float)  # m

# Crear spline cúbico para interpolación suave
_npsh_req_spline = CubicSpline(ANCHOR_Q, ANCHOR_H, bc_type='natural')

def npsh_req(Q_Ls: float | np.ndarray) -> float | np.ndarray:
    """NPSH requerido con interpolación cúbica suave"""
    return _npsh_req_spline(Q_Ls)

# hf = k·Q²·(1 + 0.15·años), con Q en L/s
# Basado en datos documentados del problema: hf(28 L/s, 0 años) = 0.2 m
Q0 = 28.0
hf0 = 0.2  # Valor documentado del problema
K_HF = hf0 / (Q0**2)

def hf_aspiracion(Q_Ls: float, anios: float) -> float:
    return K_HF * (max(0.0, Q_Ls)**2) * (1.0 + 0.15*max(0.0, anios))

# P_atm(z) en bar
def patm_bar_from_z(z_m: float) -> float:
    z = min(max(0.0, z_m), 3000.0)
    patm_mca = 10.33 - z/900.0
    return (patm_mca * gamma) / 1e5

# Pv(T) por tabla
T_TAB = np.array([0,10,20,30,40,50,60,70,80,90,100,120,140], dtype=float)
PV_MMCA_TAB = np.array([63,125,238,432,752,1258,2032,3178,4829,7151,10330,20250,37046], dtype=float)

def pv_mca_from_T(T_c: float) -> float:
    T = min(max(T_c, float(T_TAB.min())), float(T_TAB.max()))
    pv_mm = np.interp(T, T_TAB, PV_MMCA_TAB)
    return pv_mm / 1000.0

def pv_bar_from_T(T_c: float) -> float:
    return (pv_mca_from_T(T_c) * gamma) / 1e5

# Fórmulas NPSH
def deltaZ_required(Patm_bar: float, Pv_bar: float, hf_asp_m: float, npsh_req_m: float, npsh_seg_m: float) -> float:
    """ΔZ = (Patm-Pv)/γ - hf_asp - (NPSHreq + NPSHseg)"""
    Patm, Pv = Patm_bar*1e5, Pv_bar*1e5
    head_press = (Patm - Pv)/gamma
    return head_press - hf_asp_m - (npsh_req_m + npsh_seg_m)

def npsh_disp(Patm_bar: float, Pv_bar: float, Z_a: float, Z_D: float, Q_Ls: float, anios: float) -> float:
    """NPSH disponible = (P_atm - P_v)/γ + Z_a - Z_D - hf_asp(Q)"""
    Patm, Pv = Patm_bar*1e5, Pv_bar*1e5
    hf_asp_m = hf_aspiracion(Q_Ls, anios)
    return (Patm - Pv)/gamma + Z_a - Z_D - hf_asp_m

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Problema nº3: Cavitación (NPSH)")
        try:
            self.geometry("1380x900")
            self.after(0, lambda: self.state('zoomed'))
        except:
            pass
        
        # Estado
        self.phase = 1
        self.defaults = {
            "Q_Ls": 28.0,
            "NPSH_seg": 0.5,
            "anios": 0.0,
            "z_m": 2000.0,
            "T_C": 20.0,
        }
        self.cfg = dict(self.defaults)
        self.Z_D_calculated = None
        self.Z_D_fijo = None  # Z_D congelado al entrar en Fase 2
        
        # Layout (mantener estructura original)
        self._build_layout()
        self._build_controls(self.sidebar)
        self._build_badge(self.badge_panel)
        self._apply_defaults_to_controls()
        self._recompute()
        
        # Mostrar diálogo introductorio
        self.after(500, self._show_intro_dialog)
        
        # Botón volver al menú
        self.back_btn = ctk.CTkButton(self, text="← Volver al Menú", 
                                       command=self._volver_menu,
                                       width=140, height=32,
                                       fg_color="#666666", hover_color="#444444")
        self.back_btn.place(x=10, y=10)
        
    def _show_intro_dialog(self):
        """Muestra diálogo explicativo de las dos fases"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Bienvenido - IBS 9.4")
        dialog.transient(self)
        dialog.grab_set()
        
        # Centrar diálogo
        w, h = 600, 400
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = int((sw - w) / 2)
            y = int((sh - h) / 3)
            dialog.geometry(f"{w}x{h}+{x}+{y}")
        except:
            pass
        
        # Contenido
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(container, 
                            text="💧 Análisis NPSH - Dos Fases",
                            font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(0,20))
        
        text = (
            "Este programa simula el proceso completo de instalación \n"
            "y verificación de una bomba centrífuga:\n\n"
            "🔧 FASE 1: DISEÑO E INSTALACIÓN\n"
            "   • Calculas la altura óptima de instalación (Z_D)\n"
            "   • Defines las condiciones de diseño\n"
            "   • Al finalizar, pulsas 'Instalar Bomba'\n\n"
            "✅ FASE 2: VERIFICACIÓN OPERACIONAL\n"
            "   • La bomba ya está instalada (Z_D fijo)\n"
            "   • Puedes cambiar condiciones operacionales\n"
            "   • Verificas si hay riesgo de cavitación\n\n"
            "Objetivo: Entender cómo las condiciones reales pueden\n"
            "diferir del diseño y causar problemas de cavitación."
        )
        
        msg = ctk.CTkLabel(container, text=text, 
                          font=ctk.CTkFont(size=13),
                          justify="left")
        msg.pack(pady=10)
        
        btn = ctk.CTkButton(container, text="Comenzar",
                           command=dialog.destroy,
                           font=ctk.CTkFont(size=14, weight="bold"),
                           height=40)
        btn.pack(pady=20)
    
    def _build_layout(self):
        """Layout original: sidebar | centro | badge"""
        self.grid_columnconfigure(0, weight=0, minsize=440)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=300)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar (con padding superior para no solapar con botón volver)
        self.sidebar = ctk.CTkScrollableFrame(self, width=430)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=8, pady=(50,8))
        
        # Centro
        center = ctk.CTkFrame(self)
        center.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        center.grid_rowconfigure(0, weight=0)
        center.grid_rowconfigure(1, weight=1)
        center.grid_columnconfigure(0, weight=1)
        
        # Título dinámico (muestra fase actual)
        self.title_var = tk.StringVar(value="FASE 1: CÁLCULO DE Z_D")
        lbl = ctk.CTkLabel(center, textvariable=self.title_var, 
                          font=ctk.CTkFont(size=16, weight="bold"),
                          text_color="#3F51B5")
        lbl.grid(row=0, column=0, sticky="w", padx=6, pady=(0,6))
        
        # Figura (aspecto 2:1 - más ancho que alto)
        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=center)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        
        # Badge
        self.badge_panel = ctk.CTkFrame(self)
        self.badge_panel.grid(row=0, column=2, sticky="n", padx=(8,8), pady=(8,8))
    
    def _build_controls(self, parent):
        """Controles en sidebar (mantener estilo original)"""
        self.controls = {}
        row = 0
        
        def section(text):
            nonlocal row
            w = ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=14, weight="bold"))
            w.grid(row=row, column=0, sticky="w", padx=6, pady=(10,2))
            row += 1
        
        def add_slider(key, label, v0, vmin, vmax, step, unit):
            nonlocal row
            frm = ctk.CTkFrame(parent)
            frm.grid(row=row, column=0, sticky="ew", padx=6, pady=4)
            frm.grid_columnconfigure(0, weight=1)
            
            lab = ctk.CTkLabel(frm, text=label)
            lab.grid(row=0, column=0, sticky="w")
            
            var = tk.DoubleVar(value=v0)
            readout = tk.StringVar(value=f"{v0:.6g} {unit}")
            
            nsteps = max(1, int(round((vmax - vmin) / max(step, 1e-9))))
            sld = ctk.CTkSlider(frm, from_=vmin, to=vmax, number_of_steps=nsteps,
                               command=lambda v, k=key, u=unit: self._on_slider(k, float(v), u))
            sld.set(v0)
            sld.grid(row=1, column=0, sticky="ew", pady=(2,0))
            
            lbl_val = ctk.CTkLabel(frm, textvariable=readout)
            lbl_val.grid(row=1, column=1, sticky="e", padx=(8,0))
            
            self.controls[key] = {"var": var, "slider": sld, "readout": readout, "unit": unit}
            row += 1
        
        def add_label(key, text_init):
            nonlocal row
            lab = ctk.CTkLabel(parent, text=f"    {text_init}", font=ctk.CTkFont(size=11))
            lab.grid(row=row, column=0, sticky="w", padx=(24,6), pady=(0,2))
            self.controls[key] = {"label": lab}
            row += 1
        
        section("Parámetros")
        add_slider("Q_Ls", "Q seleccionado", self.cfg["Q_Ls"], 10, 30, 0.1, "L/s")
        add_slider("NPSH_seg", "NPSH de seguridad", self.cfg["NPSH_seg"], 0, 2, 0.05, "m")
        
        add_slider("anios", "Tiempo de uso", self.cfg["anios"], 0, 20, 0.1, "años")
        add_label("hf_label", "hf (aspiración) = k·Q²·(1+0.15·años) → — m")
        
        add_slider("z_m", "Altura de la instalación z", self.cfg["z_m"], 0, 3000, 5, "m")
        add_label("patm_label", "P_atm(z): — m.c.a.")
        
        add_slider("T_C", "Temperatura del agua", self.cfg["T_C"], 0, 100, 1, "°C")
        add_label("pv_label", "P_v(T): — mm.c.a. (— m.c.a.)")
        
        # Botones de fase
        section("Navegación")
        btn_row = ctk.CTkFrame(parent)
        btn_row.grid(row=row, column=0, sticky="ew", padx=6, pady=(6,8))
        
        self.btn_phase = ctk.CTkButton(btn_row, text="🔨 Instalar Bomba →",
                                       command=self._toggle_phase,
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       height=40)
        self.btn_phase.grid(row=0, column=0, sticky="ew")
    
    def _build_badge(self, parent):
        """Badge lateral rediseñado con valores fijos y dinámicos"""
        title = ctk.CTkLabel(parent, text="Estado del Sistema", 
                            font=ctk.CTkFont(size=16, weight="bold"))
        title.grid(row=0, column=0, sticky="w", padx=10, pady=(10,15))
        
        # Sección FIJA (Bomba instalada)
        fixed_frame = ctk.CTkFrame(parent, fg_color=("#E8F5E9", "#1B5E20"), corner_radius=8)
        fixed_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(fixed_frame, text="🔧 BOMBA INSTALADA",
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8,2))
        
        self.lbl_zd_val = ctk.CTkLabel(fixed_frame, text="Z_D = — m",
                                       font=ctk.CTkFont(size=20, weight="bold"),
                                       text_color="#2E7D32")
        self.lbl_zd_val.pack(pady=2)
        
        self.lbl_dz_val = ctk.CTkLabel(fixed_frame, text="ΔZ = — m",
                                       font=ctk.CTkFont(size=14))
        self.lbl_dz_val.pack(pady=(0,8))
        
        # Sección DINÁMICA (Condiciones actuales)
        dynamic_frame = ctk.CTkFrame(parent, corner_radius=8)
        dynamic_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(dynamic_frame, text="📊 CONDICIONES ACTUALES",
                    font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(8,5))
        
        self.lbl_npsh_disp = ctk.CTkLabel(dynamic_frame, text="NPSH disp = — m",
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color="#1976D2")
        self.lbl_npsh_disp.pack(pady=2)
        
        self.lbl_npsh_req = ctk.CTkLabel(dynamic_frame, text="NPSH req = — m",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        text_color="#1976D2")
        self.lbl_npsh_req.pack(pady=2)
        
        # Separador
        sep = ctk.CTkFrame(dynamic_frame, height=2, fg_color="gray")
        sep.pack(fill="x", padx=20, pady=5)
        
        self.lbl_margen = ctk.CTkLabel(dynamic_frame, text="Margen: — m",
                                      font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_margen.pack(pady=(5,10))
    
    def _on_slider(self, key, val, unit):
        if key in self.controls:
            if "var" in self.controls[key]:
                self.controls[key]["var"].set(val)
            if "readout" in self.controls[key]:
                self.controls[key]["readout"].set(f"{val:.6g} {unit}")
        
        self.cfg[key] = float(val)
        self._recompute()
    
    def _apply_defaults_to_controls(self):
        for k, v in self.defaults.items():
            if k in self.controls:
                try:
                    self.controls[k]["slider"].set(v)
                except:
                    pass
                if "var" in self.controls[k]:
                    self.controls[k]["var"].set(v)
                if "readout" in self.controls[k]:
                    self.controls[k]["readout"].set(f"{v:.6g} {self.controls[k]['unit']}")
        self.cfg = dict(self.defaults)
    
    def _toggle_phase(self):
        """Alterna entre Fase 1 y Fase 2"""
        if self.phase == 1:
            self.phase = 2
            # CONGELAR Z_D al entrar en Fase 2 (bomba instalada)
            self.Z_D_fijo = self.Z_D_calculated
            self.btn_phase.configure(text="← Volver a Fase 1 (Rediseñar)")
            self.title_var.set("FASE 2: VERIFICACIÓN OPERACIONAL (Bomba instalada a Z_D fijo)")
            # Deshabilitar z_m en Fase 2 (no tiene sentido cambiar altura con bomba instalada)
            if "z_m" in self.controls and "slider" in self.controls["z_m"]:
                self.controls["z_m"]["slider"].configure(state="disabled")
        else:
            self.phase = 1
            self.Z_D_fijo = None  # Liberar Z_D al volver a Fase 1
            if hasattr(self, '_dZ_fijo'):
                delattr(self, '_dZ_fijo')  # Liberar ΔZ congelado
            if hasattr(self, '_badge_fixed_set'):
                delattr(self, '_badge_fixed_set')  # Reset flag
            self.btn_phase.configure(text="🔨 Instalar Bomba →")
            self.title_var.set("FASE 1: CÁLCULO DE Z_D (Diseño)")
            # Rehabilitar z_m en Fase 1
            if "z_m" in self.controls and "slider" in self.controls["z_m"]:
                self.controls["z_m"]["slider"].configure(state="normal")
        self._recompute()
    
    def _recompute(self):
        """Recalcula y redibuja según la fase actual"""
        Q = self.cfg["Q_Ls"]
        NPSH_seg = self.cfg["NPSH_seg"]
        anios = self.cfg["anios"]
        z = self.cfg["z_m"]
        T = self.cfg["T_C"]
        
        # Cálculos comunes
        hf_m = hf_aspiracion(Q, anios)
        Patm_bar = patm_bar_from_z(z)
        Pv_bar = pv_bar_from_T(T)
        H_req = float(npsh_req(Q))
        
        # Actualizar labels informativos
        if "hf_label" in self.controls:
            self.controls["hf_label"]["label"].configure(text=f"    hf (aspiración) = k·Q²·(1+0.15·años) → {hf_m:.3f} m")
        patm_mca = (Patm_bar*1e5)/gamma
        if "patm_label" in self.controls:
            self.controls["patm_label"]["label"].configure(text=f"    P_atm(z): {patm_mca:.3f} m.c.a.")
        pv_mca = (Pv_bar*1e5)/gamma
        if "pv_label" in self.controls:
            self.controls["pv_label"]["label"].configure(text=f"    P_v(T): {pv_mca*1000:.0f} mm.c.a. ({pv_mca:.3f} m.c.a.)")
        
        # Calcular Z_D
        dZ = deltaZ_required(Patm_bar, Pv_bar, hf_m, H_req, NPSH_seg)
        self.Z_D_calculated = z + dZ
        
        # Actualizar badge - usar Z_D congelado en Fase 2
        if self.phase == 2 and self.Z_D_fijo is not None:
            # En Fase 2: mostrar valores congelados
            self.lbl_zd_val.configure(text=f"Z_D = {self.Z_D_fijo:.3f} m")
            # ΔZ también se congela (calculado al entrar en Fase 2)
            if not hasattr(self, '_dZ_fijo'):
                self._dZ_fijo = dZ
            self.lbl_dz_val.configure(text=f"ΔZ = {self._dZ_fijo:.3f} m")
        else:
            # En Fase 1: mostrar valores actuales
            self.lbl_zd_val.configure(text=f"Z_D = {self.Z_D_calculated:.3f} m")
            self.lbl_dz_val.configure(text=f"ΔZ = {dZ:.3f} m")
        
        # Limpiar sección dinámica en Fase 1
        if self.phase == 1:
            self.lbl_npsh_disp.configure(text="NPSH disp = — m")
            self.lbl_npsh_req.configure(text="NPSH req = — m")
            self.lbl_margen.configure(text="Margen: — m", text_color="gray")
        
        # Dibujar según fase
        if self.phase == 1:
            self._plot_phase_1(Q, hf_m, Patm_bar, Pv_bar, H_req, NPSH_seg, dZ)
        else:
            self._plot_phase_2(Q, hf_m, Patm_bar, Pv_bar, H_req, NPSH_seg, dZ)
    
    def _plot_phase_1(self, Q, hf_m, Patm_bar, Pv_bar, H_req, NPSH_seg, dZ):
        """Fase 1: Renderizado simplificado y robusto"""
        self.ax.cla()
        self.ax.axis('off')
        
        # 1. Título
        self.ax.text(0.5, 0.95, r"FASE 1: DISEÑO - Cálculo de $Z_D$", 
                    ha='center', va='top', fontsize=16, weight='bold', color='#1565C0')
        
        self.ax.text(0.5, 0.88, r"Objetivo: Calcular $Z_D$ para $NPSH_{disp} \geq NPSH_{req} + NPSH_{seg}$",
                    ha='center', va='top', fontsize=12)

        # 2. Fórmulas
        self.ax.text(0.5, 0.75, r"$\Delta Z = \frac{P_{atm} - P_v}{\gamma} - h_f - (NPSH_{req} + NPSH_{seg})$",
                    ha='center', va='center', fontsize=14, 
                    bbox=dict(boxstyle="round,pad=0.5", fc="#E3F2FD", ec="#2196F3"))
        
        self.ax.text(0.5, 0.65, r"$Z_D = z + \Delta Z$",
                    ha='center', va='center', fontsize=14)

        # 3. Datos (Dos columnas)
        col1_x = 0.25; col2_x = 0.75; row_y = 0.52
        step_y = 0.06
        
        self.ax.text(0.5, 0.58, "Condiciones de Diseño:", ha='center', fontsize=12, weight='bold', style='italic')
        
        # Columna 1
        self.ax.text(col1_x, row_y, rf"$Q = {Q:.2f}\ L/s$", ha='center', fontsize=11)
        self.ax.text(col1_x, row_y-step_y, rf"$P_{{atm}} = {(Patm_bar*1e5/gamma):.3f}\ m.c.a.$", ha='center', fontsize=11)
        self.ax.text(col1_x, row_y-2*step_y, rf"$P_v = {(Pv_bar*1e5/gamma):.3f}\ m.c.a.$", ha='center', fontsize=11)
        
        # Columna 2
        self.ax.text(col2_x, row_y, rf"$NPSH_{{req}} = {H_req:.3f}\ m$", ha='center', fontsize=11)
        self.ax.text(col2_x, row_y-step_y, rf"$NPSH_{{seg}} = {NPSH_seg:.3f}\ m$", ha='center', fontsize=11)
        self.ax.text(col2_x, row_y-2*step_y, rf"$h_f = {hf_m:.3f}\ m$", ha='center', fontsize=11)

        # 4. Resultados
        res_y = 0.20
        self.ax.text(0.5, res_y+0.05, rf"$\Delta Z = {dZ:.3f}\ m$", ha='center', fontsize=14)
        
        bg_color = "#C8E6C9" if self.phase == 1 else "#EEEEEE"
        self.ax.text(0.5, res_y-0.08, rf"$Z_D = {self.cfg['z_m']:.3f} + {dZ:.3f} = \mathbf{{{self.Z_D_calculated:.3f}\ m}}$",
                    ha='center', va='center', fontsize=18, color="#2E7D32",
                    bbox=dict(boxstyle="round,pad=1.0", fc=bg_color, ec="#4CAF50", lw=2))

        self.canvas.draw_idle()
    
    def _plot_phase_2(self, Q_sel, hf_m, Patm_bar, Pv_bar, H_req, NPSH_seg, dZ):
        """Fase 2: Verificación operacional con Z_D fijo (bomba ya instalada)"""
        # Usar Z_D CONGELADO (capturado al entrar en Fase 2)
        Z_D_fijo = self.Z_D_fijo
        
        # Las condiciones operacionales pueden cambiar
        Z_a = self.cfg["z_m"]
        anios = self.cfg["anios"]
        T = self.cfg["T_C"]
        
        # Recalcular P_atm y P_v con condiciones actuales
        Patm_bar_actual = patm_bar_from_z(Z_a)
        Pv_bar_actual = pv_bar_from_T(T)
        
        # Calcular NPSH_disp en el punto seleccionado CON Z_D FIJO
        H_disp_sel = npsh_disp(Patm_bar_actual, Pv_bar_actual, Z_a, Z_D_fijo, Q_sel, anios)
        H_req_sel = float(npsh_req(Q_sel))
        NPSH_seg_real = H_disp_sel - H_req_sel  # Margen real disponible
        
        # CAVITACIÓN: ocurre cuando NPSH_disp < NPSH_req
        cavita = H_disp_sel < H_req_sel
        
        # Advertencia de margen: cuando NPSH_seg_real < NPSH_seg configurado
        margen_insuficiente = NPSH_seg_real < NPSH_seg and not cavita
        
        # Curvas para todo el rango de Q (con condiciones actuales)
        Qplot = np.linspace(10, 30, 350)
        H_req_curve = npsh_req(Qplot)
        H_disp_curve = np.array([npsh_disp(Patm_bar_actual, Pv_bar_actual, Z_a, Z_D_fijo, q, anios) for q in Qplot])
        
        self.ax.cla()
        
        # Fondo rojo si cavita en el punto seleccionado
        if cavita:
            self.ax.set_facecolor("#FFECEC")
        else:
            self.ax.set_facecolor("white")
        
        self.ax.set_title(rf"FASE 2: Verificación Operacional ($Z_D={Z_D_fijo:.3f}$ m FIJO)", fontsize=14, weight="bold")
        self.ax.set_xlabel(r"$Q$ (L/s)", fontsize=12)
        self.ax.set_ylabel(r"$NPSH$ (m.c.a.)", fontsize=12)
        self.ax.set_xlim(10, 30)  # Rango fijo de Q
        self.ax.set_ylim(0, 10)   # Rango fijo de NPSH
        self.ax.grid(True, alpha=0.3)
        
        # Curvas principales
        self.ax.plot(Qplot, H_req_curve, linewidth=2.5, label=r"$NPSH_{req}$ (catálogo)", color="#1976D2")
        self.ax.plot(Qplot, H_disp_curve, linewidth=2.5, linestyle="--", label=r"$NPSH_{disp}$ (condiciones actuales)", color="#388E3C")
        
        # Zona de riesgo (donde NPSH_disp < NPSH_req + NPSH_seg)
        H_req_plus_seg = H_req_curve + NPSH_seg
        self.ax.fill_between(Qplot, H_req_plus_seg, H_disp_curve,
                            where=(H_disp_curve < H_req_plus_seg), alpha=0.25, color="red", label="Zona de riesgo")
        self.ax.fill_between(Qplot, H_req_plus_seg, H_disp_curve,
                            where=(H_disp_curve >= H_req_plus_seg), alpha=0.15, color="green", label="Zona segura")
        
        # Línea de NPSH_req + NPSH_seg
        self.ax.plot(Qplot, H_req_plus_seg, color="orange", linestyle=":", linewidth=2, label=rf"$NPSH_{{req}} + NPSH_{{seg}}$ ({NPSH_seg:.2f} m)", alpha=0.8)
        
        # Línea vertical en Q seleccionado mostrando NPSH_seg_real
        if cavita:
            # Rojo: NPSH_disp < NPSH_req → CAVITACIÓN
            self.ax.vlines(Q_sel, H_disp_sel, H_req, colors="red", linewidth=3.5, zorder=10, label=f"NPSH seg @ Q={Q_sel:.1f} (CAVITA)")
            self.ax.plot([Q_sel], [H_req], "v", markersize=8, color="red", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            self.ax.plot([Q_sel], [H_disp_sel], "v", markersize=8, color="red", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            color_text = "red"
        elif margen_insuficiente:
            # Naranja: NPSH_seg_real < NPSH_seg configurado → ADVERTENCIA
            self.ax.vlines(Q_sel, H_req, H_disp_sel, colors="orange", linewidth=3.5, zorder=10, label=f"NPSH seg @ Q={Q_sel:.1f} (ADVERTENCIA)")
            self.ax.plot([Q_sel], [H_req], "^", markersize=8, color="orange", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            self.ax.plot([Q_sel], [H_disp_sel], "^", markersize=8, color="orange", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            color_text = "orange"
        else:
            # Verde: NPSH_seg_real >= NPSH_seg → OK
            self.ax.vlines(Q_sel, H_req, H_disp_sel, colors="green", linewidth=3.5, zorder=10, label=f"NPSH seg @ Q={Q_sel:.1f} (OK)")
            self.ax.plot([Q_sel], [H_req], "^", markersize=8, color="green", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            self.ax.plot([Q_sel], [H_disp_sel], "^", markersize=8, color="green", markeredgecolor="white", markeredgewidth=1.5, zorder=11)
            color_text = "green"
        
        # Texto NPSH_seg_real
        mid_y = (H_req + H_disp_sel) / 2
        offset_x = 1.5 if Q_sel < 20 else -1.5
        ha = "left" if Q_sel < 20 else "right"
        self.ax.text(Q_sel + offset_x, mid_y, rf"$\Delta H={NPSH_seg_real:.3f}$ m",
                    fontsize=11, weight="bold", color=color_text, ha=ha, va="center",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=color_text, linewidth=2))
        
        # Texto adicional si no cumple
        if cavita:
            deficit = NPSH_seg - NPSH_seg_real
            self.ax.text(Q_sel + offset_x, H_req + NPSH_seg, rf"Falta {deficit:.3f} m",
                        fontsize=9, color="orange", ha=ha, va="bottom",
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="orange", linewidth=1.5))
        
        # Alarma de cavitación
        if cavita:
            self.ax.text(0.5, 0.5, "⚠ PELIGRO DE CAVITACIÓN ⚠",
                        transform=self.ax.transAxes,
                        fontsize=28, weight="bold", color="red",
                        ha="center", va="center", # alpha=0.85 ya no es necesario en el texto si el fondo es alpha
                        bbox=dict(boxstyle="round,pad=0.8", facecolor="#FFCDD2", edgecolor="red", linewidth=2, alpha=0.7))
        
        self.ax.legend(loc="upper right", fontsize=9)
        self.canvas.draw_idle()
        
        # Actualizar badge - Sección FIJA (solo en Fase 1 o al entrar en Fase 2)
        if self.phase == 1 or not hasattr(self, '_badge_fixed_set'):
            self.lbl_zd_val.configure(text=f"Z_D = {Z_D_fijo:.3f} m")
            self.lbl_dz_val.configure(text=f"ΔZ = {dZ:.3f} m")
            if self.phase == 2:
                self._badge_fixed_set = True
        
        # Actualizar badge - Sección DINÁMICA (siempre)
        self.lbl_npsh_disp.configure(text=f"NPSH disp = {H_disp_sel:.2f} m")
        self.lbl_npsh_req.configure(text=f"NPSH req = {H_req_sel:.2f} m")
        
        if cavita:
            self.lbl_margen.configure(text=f"⚠ Déficit: {abs(NPSH_seg_real):.3f} m",
                                     text_color="red")
        elif margen_insuficiente:
            deficit = NPSH_seg - NPSH_seg_real
            self.lbl_margen.configure(text=f"⚠ Falta: {deficit:.3f} m",
                                     text_color="orange")
        else:
            margen = NPSH_seg_real - NPSH_seg
            self.lbl_margen.configure(text=f"✓ Margen: +{margen:.3f} m",
                                     text_color="green")
    
    def _volver_menu(self):
        """Cierra esta ventana (el menú ya está abierto de fondo)"""
        self.destroy()

def main():
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
