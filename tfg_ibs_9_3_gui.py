# -*- coding: utf-8 -*-
"""
IBS 9.4 – Dos gráficos con didáctica y alerta de cavitación
Diseño original (colores/avisos) + funcionamiento definitivo.

Reglas:
- Z_D calculado = z + ΔZ_req y se actualiza con cualquier deslizador.
- Z_D fijo solo cambia cuando se mueve z: Z_D_fijo += (z_new − z_old) + (ΔZ_new − ΔZ_old).
"""

import numpy as np

# GUI: customtkinter si está, si no tkinter
try:
    import customtkinter as ctk
    from tkinter import StringVar, DoubleVar
    TK_MODE = "ctk"
except Exception:
    import tkinter as ctk  # type: ignore
    from tkinter import StringVar, DoubleVar  # type: ignore
    TK_MODE = "tk"

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

gamma = 9800.0  # N/m^3
EPS_OK = 1e-2   # tolerancia para no pintar cavitación si está justo en el límite

# Curva NPSHreq(Q) leída de la gráfica (anexo)
ANCHOR_Q = np.array([12, 16, 20, 25, 28, 30], dtype=float)        # L/s
ANCHOR_H = np.array([1.0, 1.8, 3.2, 5.2, 6.5, 8.0], dtype=float)  # m

def npsh_req(Q_Ls: float | np.ndarray) -> float | np.ndarray:
    return np.interp(Q_Ls, ANCHOR_Q, ANCHOR_H)

# --------- Modelos ----------
# hf = k·Q^2·(1 + 0.01·años), con Q en L/s. Ajustado a hf(28 L/s, 0 años) = 0.2 m
Q0 = 28.0
hf0 = 0.2
K_HF = hf0 / (Q0**2)

def hf_aspiracion(Q_Ls: float, anios: float) -> float:
    return K_HF * (max(0.0, Q_Ls)**2) * (1.0 + 0.01*max(0.0, anios))

# P_atm(z) en mca → bar
def patm_bar_from_z(z_m: float) -> float:
    z = min(max(0.0, z_m), 3000.0)
    patm_mca = 10.33 - z/900.0
    return (patm_mca * gamma) / 1e5  # bar

# Pv(T) por tabla (mmca -> mca -> bar)
T_TAB = np.array([0,10,20,30,40,50,60,70,80,90,100,120,140], dtype=float)
PV_MMCA_TAB = np.array([63,125,238,432,752,1258,2032,3178,4829,7151,10330,20250,37046], dtype=float)

def pv_mca_from_T(T_c: float) -> float:
    T = min(max(T_c, float(T_TAB.min())), float(T_TAB.max()))
    pv_mm = np.interp(T, T_TAB, PV_MMCA_TAB)
    return pv_mm / 1000.0  # mca

def pv_bar_from_T(T_c: float) -> float:
    return (pv_mca_from_T(T_c) * gamma) / 1e5  # bar

# --------- Fórmulas NPSH ----------
def deltaZ_required(Patm_bar: float, Pv_bar: float, hf_asp_m: float,
                    npsh_req_m: float, npsh_seg_m: float) -> float:
    """ΔZ = (Patm-Pv)/γ - hf_asp - (NPSHreq + NPSHseg)"""
    Patm = Patm_bar*1e5
    Pv   = Pv_bar*1e5
    head_press = (Patm - Pv)/gamma
    return head_press - hf_asp_m - (npsh_req_m + npsh_seg_m)

def npsh_disp_from_dZ(Patm_bar: float, Pv_bar: float, hf_asp_m: float, dZ_m: float) -> float:
    """NPSH disponible para un ΔZ dado"""
    Patm = Patm_bar*1e5
    Pv   = Pv_bar*1e5
    return (Patm - Pv)/gamma - dZ_m - hf_asp_m

INTRO_TEXT = (
    "¿Qué ves en estos dos gráficos?\n\n"
    "Gráfico 1 — “Cálculo de Z_D requerido”\n"
    "Ajusta automáticamente la altura de la bomba (Z_D) para el caudal seleccionado Q. "
    "Calcula el ΔZ necesario para cumplir NPSH_disp = NPSH_req(Q) + NPSH_seg.\n\n"
    "Gráfico 2 — “Verificación de cavitación con Z_D fijo”\n"
    "Aquí Z_D es constante (lo controla el usuario) y solo cambia cuando cambias la altitud z. "
    "Si en el caudal elegido NPSH_disp < NPSH_req(Q) + NPSH_seg, el fondo se pone rojo y aparece “CAVITACIÓN!”.\n\n"
)

class App(ctk.CTk if TK_MODE=="ctk" else ctk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IBS 9.4 – NPSH: cálculo de Z_D y verificación de cavitación")
        try:
            self.geometry("1380x900")
        except Exception:
            pass
        if TK_MODE=="ctk":
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")

        # Valores de enunciado
        self.defaults = {
            "Q_Ls": 28.0,
            "NPSH_seg": 0.5,
            "anios": 0.0,      # 0..20
            "z_m": 2000.0,     # 0..3000
            "T_C": 20.0,       # 0..140
            "Z_D_fijo": 2000.675
        }
        self.cfg = dict(self.defaults)
        self._last_z = self.defaults["z_m"]

        # Layout y UI
        self._build_layout()
        self._build_controls(self.sidebar)
        self._build_badge(self.badge_panel)
        self._apply_defaults_to_controls()
        self._recompute_and_plot()

        # Overlay
        self.after(1000, self._show_intro_overlay)

    # ----- Layout raíz -----
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0, minsize=440)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0, minsize=300)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkScrollableFrame(self, width=430) if TK_MODE=="ctk" else ttk.Frame(self)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=8, pady=8)

        # Centro
        center = ctk.CTkFrame(self) if TK_MODE=="ctk" else ttk.Frame(self)
        center.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        center.grid_rowconfigure(0, weight=0)
        center.grid_rowconfigure(1, weight=1)
        center.grid_columnconfigure(0, weight=1)

        # Título dinámico
        self.title_var = tk.StringVar(value="")
        lbl = ctk.CTkLabel(center, textvariable=self.title_var) if TK_MODE=="ctk" \
              else ttk.Label(center, textvariable=self.title_var, font=("Segoe UI", 11, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=6, pady=(0,6))

        # Figura
        self.fig = Figure(figsize=(9.8, 6.8), dpi=100)
        self.ax1 = self.fig.add_subplot(211)
        self.ax2 = self.fig.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.fig, master=center)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        # Badge
        self.badge_panel = ctk.CTkFrame(self) if TK_MODE=="ctk" else ttk.Frame(self, relief="groove", padding=10)
        self.badge_panel.grid(row=0, column=2, sticky="n", padx=(8,8), pady=(8,8))

    # ----- Controles -----
    def _build_controls(self, parent):
        self.controls = {}
        row = 0

        def section(text):
            nonlocal row
            w = ctk.CTkLabel(parent, text=text) if TK_MODE=="ctk" else ttk.Label(parent, text=text, font=("Segoe UI",10,"bold"))
            w.grid(row=row, column=0, sticky="w", padx=6, pady=(10,2))
            row += 1

        def add_slider(key, label, v0, vmin, vmax, step, unit):
            nonlocal row
            frm = ctk.CTkFrame(parent) if TK_MODE=="ctk" else ttk.Frame(parent)
            frm.grid(row=row, column=0, sticky="ew", padx=6, pady=4)
            if TK_MODE != "ctk":
                frm.grid_columnconfigure(0, weight=1)
                frm.grid_columnconfigure(1, weight=0)
            lab = ctk.CTkLabel(frm, text=label) if TK_MODE=="ctk" else ttk.Label(frm, text=label)
            lab.grid(row=0, column=0, sticky="w")
            var = DoubleVar(value=v0)
            readout = StringVar(value=f"{v0:.6g} {unit}")
            if TK_MODE=="ctk":
                nsteps = max(1, int(round((vmax - vmin) / max(step, 1e-9))))
                sld = ctk.CTkSlider(frm, from_=vmin, to=vmax,
                                    number_of_steps=nsteps,
                                    command=lambda v, k=key, u=unit: self._on_slider(k, float(v), u))
                sld.set(v0)
                lbl_val = ctk.CTkLabel(frm, textvariable=readout)
            else:
                sld = tk.Scale(frm, from_=vmin, to=vmax, resolution=step, orient="horizontal", showvalue=0,
                               command=lambda v, k=key, u=unit: self._on_slider(k, float(v), u))
                sld.set(v0)
                lbl_val = ttk.Label(frm, textvariable=readout)
            sld.grid(row=1, column=0, sticky="ew", pady=(2,0))
            lbl_val.grid(row=1, column=1, sticky="e", padx=(8,0))
            self.controls[key] = {"var": var, "slider": sld, "readout": readout, "unit": unit}
            row += 1

        def add_label(key, text_init):
            nonlocal row
            lab = ctk.CTkLabel(parent, text=f"    {text_init}") if TK_MODE=="ctk" else ttk.Label(parent, text=f"    {text_init}")
            lab.grid(row=row, column=0, sticky="w", padx=(24,6), pady=(0,2))
            self.controls[key] = {"label": lab}
            row += 1

        section("Parámetros")
        add_slider("Q_Ls",     "Q seleccionado",     self.cfg["Q_Ls"],     10, 30, 0.1,   "L/s")
        add_slider("NPSH_seg", "NPSH de seguridad",  self.cfg["NPSH_seg"], 0,  2,  0.05,  "m")

        add_slider("anios",    "Tiempo de uso",      self.cfg["anios"],    0,  20, 0.1,   "años")
        add_label("hf_label",  "hf (aspiración) = k·Q²·(1+0.01·años) → — m")

        add_slider("z_m",      "Altura de la instalación z", self.cfg["z_m"], 0, 3000, 5, "m")
        add_label("patm_label","P_atm(z): — mca")

        add_slider("T_C",      "Temperatura del agua", self.cfg["T_C"], 0, 100, 1, "°C")
        add_label("pv_label",  "P_v(T): — mmca (— mca)")

        section("Z_D fijo (Gráfico 2)")
        add_slider("Z_D_fijo", "Z_D fijo para verificación",
                   self.cfg["Z_D_fijo"], 1999, 2003, 0.001, "m")

        btn_row = ctk.CTkFrame(parent) if TK_MODE=="ctk" else ttk.Frame(parent)
        btn_row.grid(row=row, column=0, sticky="ew", padx=6, pady=(6,8))
        reset_btn = ctk.CTkButton(btn_row, text="Reset a enunciado",
                                  command=self._reset_defaults) if TK_MODE=="ctk" \
                    else ttk.Button(btn_row, text="Reset a enunciado", command=self._reset_defaults)
        reset_btn.grid(row=0, column=0, sticky="ew")

    # ----- Badge (panel de resultados) -----
    def _build_badge(self, parent):
        big = ("Segoe UI", 26, "bold")
        small = ("Segoe UI", 12, "normal")

        if TK_MODE=="ctk":
            title = ctk.CTkLabel(parent, text="Resultados clave", font=("Segoe UI", 16, "bold"))
            self.lbl_zd_calc_title = ctk.CTkLabel(parent, text="Z_D calculado (Gráfico 1):", font=small)
            self.lbl_zd_calc_val   = ctk.CTkLabel(parent, text="— m", font=big)
            self.lbl_zd_fijo_title = ctk.CTkLabel(parent, text="Z_D fijo (Gráfico 2):", font=small)
            self.lbl_zd_fijo_val   = ctk.CTkLabel(parent, text="— m", font=big)
            self.lbl_dz_val        = ctk.CTkLabel(parent, text="ΔZ calculado: — m", font=small)
        else:
            title = ttk.Label(parent, text="Resultados clave", font=("Segoe UI", 16, "bold"))
            self.lbl_zd_calc_title = ttk.Label(parent, text="Z_D calculado (Gráfico 1):", font=small)
            self.lbl_zd_calc_val   = tk.Label(parent, text="— m", font=big)
            self.lbl_zd_fijo_title = ttk.Label(parent, text="Z_D fijo (Gráfico 2):", font=small)
            self.lbl_zd_fijo_val   = tk.Label(parent, text="— m", font=big)
            self.lbl_dz_val        = ttk.Label(parent, text="ΔZ calculado: — m", font=small)

        title.grid(row=0, column=0, sticky="w", padx=10, pady=(8,4))
        self.lbl_zd_calc_title.grid(row=1, column=0, sticky="w", padx=10)
        self.lbl_zd_calc_val.grid(row=2, column=0, sticky="w", padx=10, pady=(0,8))
        self.lbl_zd_fijo_title.grid(row=3, column=0, sticky="w", padx=10)
        self.lbl_zd_fijo_val.grid(row=4, column=0, sticky="w", padx=10, pady=(0,8))
        self.lbl_dz_val.grid(row=5, column=0, sticky="w", padx=10, pady=(8,8))

    # ----- Overlay -----
    def _show_intro_overlay(self):
        self.intro = ctk.CTkToplevel(self) if TK_MODE=="ctk" else tk.Toplevel(self)
        self.intro.title("Introducción")
        self.intro.transient(self)
        try:
            self.intro.attributes("-topmost", True)
        except Exception:
            pass
        w, h = 720, 420
        try:
            sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        except Exception:
            sw, sh = 1400, 900
        x = int((sw - w) / 2); y = int((sh - h) / 3)
        try:
            self.intro.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

        container = ctk.CTkFrame(self.intro, corner_radius=10) if TK_MODE=="ctk" else ttk.Frame(self.intro, padding=12, relief="groove")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        title = "Guía rápida"
        if TK_MODE=="ctk":
            lbl_title = ctk.CTkLabel(container, text=title, font=("Segoe UI", 16, "bold"))
            lbl_body  = ctk.CTkLabel(container, text=INTRO_TEXT, justify="left", wraplength=680)
            btn_ok    = ctk.CTkButton(container, text="Entendido", command=self._close_intro)
        else:
            lbl_title = ttk.Label(container, text=title, font=("Segoe UI", 12, "bold"))
            lbl_body  = ttk.Label(container, text=INTRO_TEXT, justify="left", wraplength=680)
            btn_ok    = ttk.Button(container, text="Entendido", command=self._close_intro)

        lbl_title.pack(anchor="w", padx=6, pady=(6,4))
        lbl_body.pack(fill="both", expand=True, padx=6, pady=(0,10))
        btn_ok.pack(anchor="e", padx=6, pady=(0,6))

    def _close_intro(self):
        try:
            self.intro.destroy()
        except Exception:
            pass

    # ---- Helper: ΔZ_req evaluado en una z dada, con el resto del estado actual ----
    def _dZ_req_at(self, z_val: float) -> float:
        Q_sel    = self.cfg["Q_Ls"]
        anios    = self.cfg.get("anios", 0.0)
        T_c      = self.cfg.get("T_C", 20.0)
        NPSH_seg = self.cfg["NPSH_seg"]

        hf_m     = hf_aspiracion(Q_sel, anios)
        Patm_bar = patm_bar_from_z(z_val)
        Pv_bar   = pv_bar_from_T(T_c)
        H_req_Q  = float(npsh_req(Q_sel))
        return deltaZ_required(Patm_bar, Pv_bar, hf_m, H_req_Q, NPSH_seg)

    # ----- Interacción -----
    def _on_slider(self, key, val, unit):
        # Actualiza lectura y cfg del control movido
        if key in self.controls:
            if "var" in self.controls[key]:
                self.controls[key]["var"].set(val)
            if "readout" in self.controls[key]:
                self.controls[key]["readout"].set(f"{val:.6g} {unit}")

        if key == "z_m":
            # Solo aquí se ajusta Z_D_fijo (regla definitiva)
            z_new = float(val)
            z_old = self._last_z

            zd_fijo_old = self.cfg["Z_D_fijo"]
            zd_fijo_new = zd_fijo_old + (z_new - z_old)  # solo mantiene ΔZ, sin compensar P_atm


            # Recentrar rango del slider Z_D_fijo alrededor del nuevo z y aplicar
            try:
                sld = self.controls["Z_D_fijo"]["slider"]
                if TK_MODE == "ctk":
                    sld.configure(from_=z_new - 1.0, to=z_new + 3.0)
                else:
                    sld.config(from_=z_new - 1.0, to=z_new + 3.0)
                zd_fijo_clamped = max(z_new - 1.0, min(z_new + 3.0, zd_fijo_new))
                sld.set(zd_fijo_clamped)
                self.controls["Z_D_fijo"]["var"].set(zd_fijo_clamped)
                self.controls["Z_D_fijo"]["readout"].set(f"{zd_fijo_clamped:.6g} m")
                self.cfg["Z_D_fijo"] = float(zd_fijo_clamped)
            except Exception:
                self.cfg["Z_D_fijo"] = float(zd_fijo_new)

            self._last_z = z_new

        # Guardar y recomputar
        self.cfg[key] = float(val)
        self._recompute_and_plot()

    def _apply_defaults_to_controls(self):
        for k, v in self.defaults.items():
            if k in self.controls:
                try:
                    self.controls[k]["slider"].set(v)
                except Exception:
                    pass
                if "var" in self.controls[k]:
                    self.controls[k]["var"].set(v)
                if "readout" in self.controls[k]:
                    self.controls[k]["readout"].set(f"{v:.6g} {self.controls[k]['unit']}")
        self.cfg = dict(self.defaults)
        self._last_z = self.defaults["z_m"]

    def _reset_defaults(self):
        self._apply_defaults_to_controls()
        try:
            z0 = self.cfg["z_m"]
            sld = self.controls["Z_D_fijo"]["slider"]
            if TK_MODE == "ctk":
                sld.configure(from_=z0 - 1.0, to=z0 + 3.0)
            else:
                sld.config(from_=z0 - 1.0, to=z0 + 3.0)
        except Exception:
            pass
        self._recompute_and_plot()

    # ----- Cálculo + gráficos -----
    def _recompute_and_plot(self):
        # Lecturas
        Q_sel    = self.cfg["Q_Ls"]
        anios    = self.cfg.get("anios", 0.0)
        z_inst   = self.cfg.get("z_m", 2000.0)   # nivel del depósito = altitud elegida
        T_c      = self.cfg.get("T_C", 20.0)
        NPSH_seg = self.cfg["NPSH_seg"]
        ZD_fijo  = self.cfg["Z_D_fijo"]

        # Derivados y etiquetas info
        hf_m       = hf_aspiracion(Q_sel, anios)
        Patm_bar   = patm_bar_from_z(z_inst)
        Pv_bar     = pv_bar_from_T(T_c)

        if "hf_label" in self.controls:
            self.controls["hf_label"]["label"].configure(text=f"    hf (aspiración) = k·Q²·(1+0.01·años) → {hf_m:.3f} m")
        patm_mca = (Patm_bar*1e5)/gamma
        if "patm_label" in self.controls:
            self.controls["patm_label"]["label"].configure(text=f"    P_atm(z): {patm_mca:.3f} mca")
        pv_mca = (Pv_bar*1e5)/gamma
        if "pv_label" in self.controls:
            self.controls["pv_label"]["label"].configure(text=f"    P_v(T): {pv_mca*1000:.0f} mmca ({pv_mca:.3f} mca)")

        # Título dinámico
        self.title_var.set(f"Altitud de instalación z = {z_inst:.3f} m. Gráfico 1 recalcula Z_D. Gráfico 2 verifica con Z_D fijo.")

        # Curvas requeridas
        H_req_Q = float(npsh_req(Q_sel))
        H_req_plus_Q = H_req_Q + NPSH_seg

        Qplot = np.linspace(10, 30, 350)
        H_req_curve = npsh_req(Qplot)
        H_req_plus_curve = H_req_curve + NPSH_seg

        # ----- Gráfico 1: cálculo de Z_D (base en z_inst) -----
        dZ_calc = deltaZ_required(Patm_bar, Pv_bar, hf_m, H_req_Q, NPSH_seg)
        ZD_calc = z_inst + dZ_calc
        H_disp_calc = npsh_disp_from_dZ(Patm_bar, Pv_bar, hf_m, dZ_calc)

        ax1 = self.ax1
        ax1.cla()
        ax1.set_title("NPSH_req + NPSH_seg vs NPSH_disp: cálculo de Z_D requerido")
        ax1.set_xlabel("Q (L/s)"); ax1.set_ylabel("NPSH (m)"); ax1.grid(True)

        # Diseño original (colores/estilo)
        ax1.plot(Qplot, H_req_curve, label="NPSH requerido (catálogo)")
        ax1.plot(Qplot, H_req_plus_curve, linestyle="--", label="NPSH requerido + seguridad")
        ax1.axhline(H_disp_calc, color="tab:green", linestyle="--", label="NPSH disp (con ΔZ calculado)")

        margin1 = H_disp_calc - H_req_plus_curve
        ax1.fill_between(Qplot, H_req_plus_curve, H_disp_calc,
                         where=(margin1 >= 0), alpha=0.18, color="#5dade2", label="Zona segura")
        ax1.fill_between(Qplot, H_req_plus_curve, H_disp_calc,
                         where=(margin1 < 0), alpha=0.18, color="#f1948a", label="Riesgo cavitación")

        ax1.scatter([Q_sel], [H_req_plus_Q], s=110, marker="^", color="green", edgecolors="black", zorder=6)
        ax1.legend(loc="best")

        # ----- Gráfico 2: Z_D fijo y verificación de cavitación -----
        dZ_fijo = ZD_fijo - z_inst
        H_disp_fijo = npsh_disp_from_dZ(Patm_bar, Pv_bar, hf_m, dZ_fijo)

        ax2 = self.ax2
        ax2.cla()
        ok = (H_disp_fijo + EPS_OK) >= H_req_plus_Q  # tolerancia
        ax2.set_facecolor("#FFECEC" if not ok else "white")  # Fondo rojo claro si cavita
        ax2.set_title("NPSH_req + NPSH_seg vs NPSH_disp: verificación de cavitación con Z_D fijo")
        ax2.set_xlabel("Q (L/s)"); ax2.set_ylabel("NPSH (m)"); ax2.grid(True)

        ax2.plot(Qplot, H_req_curve, label="NPSH requerido (catálogo)")
        ax2.plot(Qplot, H_req_plus_curve, linestyle="--", label="NPSH requerido + seguridad")
        ax2.axhline(H_disp_fijo, color="tab:green", linestyle="--", label=f"NPSH disp (Z_D fijo = {ZD_fijo:.3f} m)")

        margin2 = H_disp_fijo - H_req_plus_curve
        ax2.fill_between(Qplot, H_req_plus_curve, H_disp_fijo,
                         where=(margin2 >= 0), alpha=0.18, color="#5dade2", label="Zona segura")
        ax2.fill_between(Qplot, H_req_plus_curve, H_disp_fijo,
                         where=(margin2 < 0), alpha=0.18, color="#f1948a", label="Riesgo cavitación")

        marker = "^" if ok else "v"
        mcolor = "green" if ok else "red"
        ax2.scatter([Q_sel], [H_req_plus_Q], s=120, marker=marker, color=mcolor, edgecolors="black", zorder=6)

        if not ok:
            ax2.text(0.5, 0.5, "CAVITACIÓN!", transform=ax2.transAxes,
                     fontsize=28, fontweight="bold", color="red", ha="center", va="center", alpha=0.85)

        ax2.legend(loc="best")

        # Render
        self.canvas.draw_idle()

        # Badge: actualizar valores clave
        self.lbl_zd_calc_val.configure(text=f"{ZD_calc:.3f} m")
        self.lbl_zd_fijo_val.configure(text=f"{ZD_fijo:.3f} m")
        self.lbl_dz_val.configure(text=f"ΔZ calculado (Gráfico 1): {dZ_calc:.3f} m")

if __name__=="__main__":
    app = App()
    app.mainloop()
