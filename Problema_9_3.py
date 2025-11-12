# -*- coding: utf-8 -*-
"""
IBS 9.3 – Instalación compuesta con sobrepresor y selección de bomba (curva realista)

Cambios de esta versión:
- Título encima de la gráfica: "A → C: Curva de instalación vs curva de la bomba".
- Resultados reubicados DEBAJO de la gráfica, en un panel scrollable.
- Sidebar izquierda queda solo para parámetros (con scroll).
"""

import math
import numpy as np

# GUI
try:
    import customtkinter as ctk
    from tkinter import StringVar, DoubleVar, IntVar
    TK_MODE = "ctk"
except Exception:
    import tkinter as ctk  # type: ignore
    from tkinter import StringVar, DoubleVar, IntVar  # type: ignore
    TK_MODE = "tk"

import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

g = 9.81
rho = 1000.0

# -----------------------
# Config de la curva de bomba (realista)
# -----------------------

# Puntos "IBS" (para referencia visual opcional)
IBS_Q = np.array([100.0, 111.1, 125.0, 138.9, 150.0, 166.7, 200.0], dtype=float)
IBS_H = np.array([72.0,   71.0,  70.0,  68.0,  66.0,  63.5,  56.0], dtype=float)
SHOW_IBS_POINTS = False

# Puntos ANCLA "catálogo" para D=450 @ 1450 rpm (ajústalos si quieres clavar tu anexo)
CAT_Q = np.array([  0.0, 120.0, 160.0, 200.0])   # l/s
CAT_H = np.array([ 78.0,  72.0,  66.0,  56.0])   # m
CAT_POLY_DEG = 3  # 3=suave tipo catálogo, 2=parabólica estricta

# -----------------------
# Hidráulica
# -----------------------

def C_from_eps_over_D(epsilon_m, D_m):
    if D_m <= 0:
        return 130.0
    ratio = epsilon_m / D_m
    C = 160.0 - 100000.0*ratio  # lineal entre (2e-4->140) y (3e-4->130)
    return max(60.0, min(160.0, C))

def hf_hazen_williams(Q_m3s, L, D, C):
    Q = np.maximum(Q_m3s, 1e-12)  # vectorizable: vale para escalar y arrays
    return 10.67 * L * (Q**1.852) / ((C**1.852) * (D**4.8704))

def velocity_from_QD(Q_m3s, D_m):
    A = math.pi*(D_m**2)/4.0
    return Q_m3s / max(A, 1e-12)

# -----------------------
# Modelo 9.3
# -----------------------

class Model93:
    def __init__(self, cfg):
        self.cfg = cfg
        self._fit_catalog_curve()

    def _fit_catalog_curve(self):
        deg = min(CAT_POLY_DEG, len(CAT_Q)-1)
        self.cat_coeffs = np.polyfit(CAT_Q, CAT_H, deg=deg)

    # ---- (a) y (b)
    def solve_a_b(self):
        p = self.cfg
        zA, zC, zD, zE = p["zA"], p["zC"], p["zD"], p["zE"]
        PE_kg = p["PE_kgcm2"]
        Q3_target_Ls = p["Q3_target_Ls"]

        eps_m = p["epsilon_cm"] / 100.0 / 100.0  # cm -> m
        D1, D2, D3 = p["D1"], p["D2"], p["D3"]
        L1, L2, L3 = p["L1"], p["L2"], p["L3"]
        C1 = C_from_eps_over_D(eps_m, D1)
        C2 = C_from_eps_over_D(eps_m, D2)
        C3 = C_from_eps_over_D(eps_m, D3)

        BE = zE + 10.0*PE_kg
        Q3_m3s = Q3_target_Ls/1000.0
        hf3 = hf_hazen_williams(Q3_m3s, L3, D3, C3)
        BN = BE + hf3  # energía en el nudo

        K_noz = p["K_nozzle"]
        D_boq = p["D_nozzle"]
        N_boq = p["N_nozzles"]

        def f_Q2(Q2_Ls):
            Q2 = max(Q2_Ls/1000.0, 0.0)
            q_each = Q2 / max(N_boq, 1)
            V = velocity_from_QD(q_each, D_boq)
            Vh = V*V/(2.0*g)
            hf2 = hf_hazen_williams(Q2, L2, D2, C2)
            return (zD + (1.0+K_noz)*Vh + hf2) - BN

        # Bisección
        left, right = 0.0, 250.0
        fL = f_Q2(left); fR = f_Q2(right)
        tries = 0
        while fL*fR > 0.0 and right < 1000.0 and tries < 20:
            right *= 1.5
            fR = f_Q2(right); tries += 1

        Q2_star_Ls = None
        if fL == 0.0:
            Q2_star_Ls = left
        elif fR == 0.0:
            Q2_star_Ls = right
        elif fL*fR < 0.0:
            for _ in range(80):
                mid = 0.5*(left+right)
                fm = f_Q2(mid)
                if fL*fm <= 0.0:
                    right, fR = mid, fm
                else:
                    left, fL = mid, fm
                if abs(right-left) < 1e-6:
                    break
            Q2_star_Ls = 0.5*(left+right)

        Q1_Ls = None; V_boq = None; Pc_kg = None; hf1 = None
        if Q2_star_Ls is not None:
            Q1_Ls = Q2_star_Ls + Q3_target_Ls
            Q1 = Q1_Ls/1000.0
            hf1 = hf_hazen_williams(Q1, L1, D1, C1)
            Pc_m = BN + hf1 - zC
            Pc_kg = Pc_m/10.0
            q_each = (Q2_star_Ls/1000.0)/N_boq
            V_boq = velocity_from_QD(q_each, D_boq)

        return {
            "BN": BN,
            "Q2_Ls": Q2_star_Ls,
            "Q1_Ls": Q1_Ls,
            "V_boq_ms": V_boq,
            "Pc_kgcm2": Pc_kg,
            "hf1_m": hf1,
            "C_HW": {"C1": C1, "C2": C2, "C3": C3}
        }

    # ---- (c)
    def check_c(self, Pc_from_a_kg):
        p = self.cfg
        zC, zE = p["zC"], p["zE"]
        D3, L3 = p["D3"], p["L3"]
        eps_m = p["epsilon_cm"]/100.0/100.0
        C3 = C_from_eps_over_D(eps_m, D3)
        PE_kg = p["PE_kgcm2"]

        Q3_c_Ls = 65.0
        Q3_c = Q3_c_Ls/1000.0
        BE = zE + 10.0*PE_kg
        hf3 = hf_hazen_williams(Q3_c, L3, D3, C3)
        BN_req = BE + hf3

        Bc = zC + 10.0*Pc_from_a_kg
        feasible = Bc >= BN_req
        return {"BN_req": BN_req, "Bc": Bc, "feasible": feasible}

    # ---- Curvas Hmi y Hmb
    def Hmi_curve(self, Q_Ls):
        p = self.cfg
        zA, zC = p["zA"], p["zC"]
        Pc_given_kg = p["Pc_given_kgcm2"]
        D0, L0 = p["D0"], p["L0"]
        eps_m = p["epsilon_cm"]/100.0/100.0
        C0 = C_from_eps_over_D(eps_m, D0)

        Q = np.asarray(Q_Ls, dtype=float)/1000.0
        static = (zC + 10.0*Pc_given_kg) - zA
        hf0 = hf_hazen_williams(Q, L0, D0, C0)
        return static + hf0

    def Hmb_curve(self, Q_Ls):
        Q = np.asarray(Q_Ls, dtype=float)
        return np.polyval(self.cat_coeffs, Q)

# -----------------------
# GUI con sidebar izquierda y resultados debajo de la gráfica
# -----------------------

class App(ctk.CTk if TK_MODE=="ctk" else ctk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IBS 9.3 – Instalación compuesta y selección de bomba (curva realista)")
        try:
            self.geometry("1400x860")
        except Exception:
            pass
        if TK_MODE == "ctk":
            ctk.set_appearance_mode("light")
            ctk.set_default_color_theme("blue")

        # Defaults del enunciado
        self.cfg = {
            "zA": 600.0, "zC": 620.0, "zD": 630.0, "zE": 625.0,
            "PE_kgcm2": 2.0,
            "D0": 0.200, "L0": 137.0,  # A→C (eq. con piezas)
            "D1": 0.300, "L1": 300.0,  # C→N
            "D2": 0.200, "L2": 500.0,  # N→boquillas
            "D3": 0.200, "L3": 500.0,  # N→E
            "epsilon_cm": 0.006,
            "Q3_target_Ls": 50.0,      # (a)
            "Pc_given_kgcm2": 3.5,     # (d/e)
            "N_nozzles": 4, "D_nozzle": 0.050, "K_nozzle": 0.3,
            "eta_guess": 0.804, "energy_price_eur_kWh": 0.10,
            "Q_target_e_Ls": 125.0
        }

        self.model = Model93(self.cfg)
        self._after_id = None

        self._build_layout()
        self._write_defaults_into_controls()
        self._recompute_and_plot()

    def _build_layout(self):
        # columnas: 0 sidebar, 1 panel derecho con gráfica + resultados
        self.grid_columnconfigure(0, weight=0, minsize=420)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar scrollable (PARÁMETROS)
        if TK_MODE == "ctk":
            self.sidebar = ctk.CTkScrollableFrame(self, width=400)
        else:
            self.sidebar = ttk.Frame(self)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=8, pady=8)

        self.controls_container = ctk.CTkFrame(self.sidebar) if TK_MODE=="ctk" else ttk.Frame(self.sidebar)
        self.controls_container.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        # Panel derecho
        self.right = ctk.CTkFrame(self) if TK_MODE=="ctk" else ttk.Frame(self)
        self.right.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        # 3 filas: título, gráfica, resultados
        self.right.grid_rowconfigure(1, weight=1)  # la gráfica estira
        self.right.grid_columnconfigure(0, weight=1)

        # TÍTULO ENCIMA DE LA GRÁFICA
        title_lbl = ctk.CTkLabel(self.right, text="A → C: Curva de instalación vs curva de la bomba") \
            if TK_MODE=="ctk" else ttk.Label(self.right, text="A → C: Curva de instalación vs curva de la bomba", font=("Segoe UI", 11, "bold"))
        title_lbl.grid(row=0, column=0, sticky="w", padx=6, pady=(2,6))

        # GRÁFICA
        self.fig = Figure(figsize=(8.8, 5.2), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Q (L/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")

        # RESULTADOS DEBAJO DE LA GRÁFICA (scrollable)
        if TK_MODE == "ctk":
            self.results_panel = ctk.CTkScrollableFrame(self.right, height=320)
        else:
            self.results_panel = ttk.Frame(self.right)
        self.results_panel.grid(row=2, column=0, sticky="nsew", padx=4, pady=(6,0))
        self._build_results(self.results_panel)

        # Construir controles en la sidebar
        self._build_controls(self.controls_container)

    def _build_results(self, parent):
        for i in range(1):
            parent.grid_columnconfigure(i, weight=1)

        # Variables de texto
        self.var_a_pc = StringVar(value="-")
        self.var_b_q2 = StringVar(value="-")
        self.var_b_v = StringVar(value="-")
        self.var_c_chk = StringVar(value="-")
        self.var_d_pto = StringVar(value="-")
        self.var_d_pabs = StringVar(value="-")
        self.var_d_cost = StringVar(value="-")
        self.var_e_val = StringVar(value="-")

        def add_line(r, label, var):
            lbl = ctk.CTkLabel(parent, text=label) if TK_MODE=="ctk" else ttk.Label(parent, text=label)
            val = ctk.CTkLabel(parent, textvariable=var) if TK_MODE=="ctk" else ttk.Label(parent, textvariable=var)
            lbl.grid(row=r, column=0, sticky="w", padx=6, pady=(2,0))
            val.grid(row=r+1, column=0, sticky="w", padx=12, pady=(0,4))

        # Título resultados
        title = ctk.CTkLabel(parent, text="Resultados") if TK_MODE=="ctk" else ttk.Label(parent, text="Resultados", font=("Segoe UI", 10, "bold"))
        title.grid(row=0, column=0, sticky="w", padx=6, pady=(6,4))

        add_line(1,  "(a) Pc requerida", self.var_a_pc)
        add_line(3,  "(b) Q₂ total", self.var_b_q2)
        add_line(5,  "    Velocidad por boquilla", self.var_b_v)
        add_line(7,  "(c) Q₃=65 l/s ¿viable?", self.var_c_chk)
        add_line(9,  "(d) Punto de funcionamiento Q*, H*, η", self.var_d_pto)
        add_line(11, "Potencia absorbida", self.var_d_pabs)
        add_line(13, "Coste €/m³", self.var_d_cost)
        add_line(15, "(e) hf_válvula / ΔPc para Q objetivo", self.var_e_val)

    def _build_controls(self, parent):
        self.controls = {}
        row = 0

        def section(title):
            nonlocal row
            t = ctk.CTkLabel(parent, text=title) if TK_MODE=="ctk" else ttk.Label(parent, text=title, font=("Segoe UI",10,"bold"))
            t.grid(row=row, column=0, sticky="w", padx=6, pady=(10,2))
            row += 1

        def add_slider(key, label, v0, vmin, vmax, step, unit=""):
            nonlocal row
            frm = ctk.CTkFrame(parent) if TK_MODE=="ctk" else ttk.Frame(parent)
            frm.grid(row=row, column=0, sticky="ew", padx=6, pady=3)
            if TK_MODE!="ctk":
                frm.grid_columnconfigure(0, weight=1)
                frm.grid_columnconfigure(1, weight=0)
                frm.grid_columnconfigure(2, weight=0)
            lab = ctk.CTkLabel(frm, text=f"{label} ({unit})") if TK_MODE=="ctk" else ttk.Label(frm, text=f"{label} ({unit})")
            lab.grid(row=0, column=0, sticky="w")
            var = DoubleVar(value=v0)
            if TK_MODE=="ctk":
                sld = ctk.CTkSlider(frm, from_=vmin, to=vmax, number_of_steps=int(round((vmax-vmin)/step)) if step>0 else 0,
                                    command=lambda v, k=key: self._on_slider(k,float(v)))
                sld.set(v0)
            else:
                sld = tk.Scale(frm, from_=vmin, to=vmax, resolution=step, orient="horizontal", showvalue=0,
                               command=lambda v, k=key: self._on_slider(k,float(v)))
                sld.set(v0)
            sld.grid(row=1, column=0, sticky="ew")
            ent_var = StringVar(value=f"{v0:.6g}")
            ent = ctk.CTkEntry(frm) if TK_MODE=="ctk" else ttk.Entry(frm, width=10)
            ent.configure(textvariable=ent_var)
            ent.grid(row=1, column=1, padx=(6,0))
            btn = ctk.CTkButton(frm, text="✔", width=28, command=lambda k=key, ev=ent_var: self._apply_entry(k,ev)) if TK_MODE=="ctk" else ttk.Button(frm, text="✔", width=3, command=lambda k=key, ev=ent_var: self._apply_entry(k,ev))
            btn.grid(row=1, column=2, padx=(6,0))
            self.controls[key] = {"var": var, "slider": sld, "entry": ent_var}
            row += 1

        section("Cotas")
        add_slider("zA", "z_A",  self.cfg["zA"], 550, 700, 0.5, "m")
        add_slider("zC", "z_C",  self.cfg["zC"], 550, 700, 0.5, "m")
        add_slider("zD", "z_D",  self.cfg["zD"], 550, 700, 0.5, "m")
        add_slider("zE", "z_E",  self.cfg["zE"], 550, 700, 0.5, "m")

        section("Presiones")
        add_slider("PE_kgcm2",        "P_E", self.cfg["PE_kgcm2"], 0.0, 5.0, 0.05, "kg/cm²")
        add_slider("Pc_given_kgcm2",  "Pc (para d-e)", self.cfg["Pc_given_kgcm2"], 0.0, 6.0, 0.05, "kg/cm²")

        section("Tuberías (D en m, L en m)")
        add_slider("D0", "D0 A→C", self.cfg["D0"], 0.05, 0.5, 0.001, "m")
        add_slider("L0", "L0 A→C (eq.)", self.cfg["L0"], 10, 400, 1, "m")
        add_slider("D1", "D1 C→N", self.cfg["D1"], 0.05, 0.5, 0.001, "m")
        add_slider("L1", "L1 C→N", self.cfg["L1"], 10, 600, 1, "m")
        add_slider("D2", "D2 N→boq", self.cfg["D2"], 0.05, 0.5, 0.001, "m")
        add_slider("L2", "L2 N→boq", self.cfg["L2"], 10, 800, 1, "m")
        add_slider("D3", "D3 N→E", self.cfg["D3"], 0.05, 0.5, 0.001, "m")
        add_slider("L3", "L3 N→E", self.cfg["L3"], 10, 800, 1, "m")

        section("Rugosidad")
        add_slider("epsilon_cm", "ε (cm)", self.cfg["epsilon_cm"], 0.001, 0.02, 0.0001, "cm")

        section("Boquillas")
        add_slider("N_nozzles", "Nº boquillas", float(self.cfg["N_nozzles"]), 1, 12, 1, "unid")
        add_slider("D_nozzle", "Diámetro boquilla", self.cfg["D_nozzle"], 0.01, 0.1, 0.001, "m")
        add_slider("K_nozzle", "K boquilla", self.cfg["K_nozzle"], 0.0, 2.0, 0.01, "-")

        section("Objetivos")
        add_slider("Q3_target_Ls", "Q3 objetivo (a)", self.cfg["Q3_target_Ls"], 0.0, 150.0, 0.5, "L/s")
        add_slider("Q_target_e_Ls", "Q objetivo (e)", self.cfg["Q_target_e_Ls"], 50.0, 220.0, 0.5, "L/s")

        section("Bomba y energía")
        add_slider("eta_guess", "η estimada", self.cfg["eta_guess"], 0.5, 0.95, 0.005, "-")
        add_slider("energy_price_eur_kWh", "€/kWh", self.cfg["energy_price_eur_kWh"], 0.01, 0.50, 0.005, "€/kWh")

        # Botón manual
        frm = ctk.CTkFrame(parent) if TK_MODE=="ctk" else ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", padx=6, pady=(8,6))
        btn = ctk.CTkButton(frm, text="Recalcular", command=self._recompute_and_plot) if TK_MODE=="ctk" else ttk.Button(frm, text="Recalcular", command=self._recompute_and_plot)
        btn.grid(row=0, column=0, sticky="ew")

    def _write_defaults_into_controls(self):
        for k, ctrl in self.controls.items():
            v = self.cfg.get(k, None)
            if v is None: 
                continue
            ctrl["var"].set(v)
            try:
                ctrl["slider"].set(v)
            except Exception:
                pass
            ctrl["entry"].set(f"{v:.6g}")

    def _on_slider(self, key, val):
        if key in self.controls:
            self.controls[key]["entry"].set(f"{val:.6g}")
            self.controls[key]["var"].set(val)
        self._debounced_update()

    def _apply_entry(self, key, entry_var):
        try:
            val = float(entry_var.get().replace(",", "."))
        except ValueError:
            return
        if key in self.controls:
            self.controls[key]["var"].set(val)
            try:
                self.controls[key]["slider"].set(val)
            except Exception:
                pass
        self._recompute_and_plot()

    def _debounced_update(self, ms=150):
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(ms, self._recompute_and_plot)

    def _sync_cfg_from_controls(self):
        for k, ctrl in self.controls.items():
            v = float(ctrl["var"].get())
            if k == "N_nozzles":
                v = int(round(v))
            self.cfg[k] = v

    def _recompute_and_plot(self):
        self._after_id = None
        self._sync_cfg_from_controls()
        self.model = Model93(self.cfg)

        # (a)(b)
        ab = self.model.solve_a_b()

        # (c)
        c_part = None
        if ab["Pc_kgcm2"] is not None:
            c_part = self.model.check_c(ab["Pc_kgcm2"])

        # (d) Curvas y punto
        Q_plot = np.linspace(0.0, 220.0, 700)
        Hmi = self.model.Hmi_curve(Q_plot)
        Hmb = self.model.Hmb_curve(Q_plot)

        # Bisección en escalar
        def f(q):
            qf = float(q)
            return float(self.model.Hmb_curve(qf) - self.model.Hmi_curve(qf))

        left, right = 60.0, 220.0
        fL, fR = f(left), f(right)
        tries = 0
        while fL*fR > 0 and tries < 20:
            right *= 1.1
            fR = f(right); tries += 1
        Qs = Hs = None
        if fL*fR <= 0:
            for _ in range(80):
                mid = 0.5*(left+right)
                fm = f(mid)
                if fL*fm <= 0:
                    right, fR = mid, fm
                else:
                    left, fL = mid, fm
                if abs(right-left) < 1e-6:
                    break
            Qs = 0.5*(left+right)
            Hs = float(self.model.Hmb_curve(Qs))

        # (e) objetivo Qe
        Qe = self.cfg["Q_target_e_Ls"]
        Hmi_e = float(self.model.Hmi_curve(Qe))
        Hmb_e = float(self.model.Hmb_curve(Qe))
        diff = Hmb_e - Hmi_e
        if diff >= 0:
            hf_valve = diff
            dPc_kg = 0.0
        else:
            hf_valve = 0.0
            dPc_kg = (-diff)/10.0

        # Plot
        self.ax.cla()
        self.ax.set_xlabel("Q (L/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.grid(True)
        # título dentro de la figura por si exportas imagen
        self.ax.set_title("A → C", loc="left")
        self.ax.plot(Q_plot, Hmi, label="Hmi: instalación A→C")
        self.ax.plot(Q_plot, Hmb, label="Hmb: bomba (catálogo suave)")
        if SHOW_IBS_POINTS:
            self.ax.scatter(IBS_Q, IBS_H, marker='^', label="Puntos IBS (ref.)")
        if Qs is not None and Hs is not None:
            self.ax.scatter([Qs], [Hs], s=80, color="green", edgecolors="black", zorder=5,
                            label="Punto de funcionamiento")
            self.ax.axvline(Qs, linestyle="--", linewidth=1, color="green")
            self.ax.axhline(Hs, linestyle="--", linewidth=1, color="green")
        self.ax.legend(loc="best")
        y_all = np.concatenate([Hmi, Hmb])
        y_min, y_max = float(np.nanmin(y_all)), float(np.nanmax(y_all))
        pad = 0.05*max(1.0, y_max-y_min)
        self.ax.set_xlim(0, 220)
        self.ax.set_ylim(y_min - pad, y_max + pad)
        self.canvas.draw_idle()

        # Resultados (debajo de la gráfica)
        if ab["Pc_kgcm2"] is not None:
            self.var_a_pc.set(f"Pc = {ab['Pc_kgcm2']:.3f} kg/cm²  (C1={ab['C_HW']['C1']:.0f})")
        else:
            self.var_a_pc.set("Pc = —")

        if ab["Q2_Ls"] is not None and ab["V_boq_ms"] is not None:
            self.var_b_q2.set(f"Q₂ = {ab['Q2_Ls']:.3f} L/s")
            self.var_b_v.set(f"V_boq = {ab['V_boq_ms']:.3f} m/s")
        else:
            self.var_b_q2.set("Q₂ = —"); self.var_b_v.set("V_boq = —")

        if c_part is not None:
            feas = "SÍ" if c_part["feasible"] else "NO"
            self.var_c_chk.set(f"Bc = {c_part['Bc']:.2f} m; BN_req = {c_part['BN_req']:.2f} m → {feas}")
        else:
            self.var_c_chk.set("—")

        if Qs is not None and Hs is not None:
            eta = max(0.01, min(0.99, self.cfg["eta_guess"]))
            self.var_d_pto.set(f"Q* = {Qs:.1f} L/s; H* = {Hs:.1f} m; η = {eta*100:.1f}%")
            Qs_m3s = Qs/1000.0
            Pabs_W = rho*g*Qs_m3s*Hs/eta
            Pabs_kW = Pabs_W/1000.0
            flow_m3h = Qs*3.6
            cost_h = Pabs_kW*self.cfg["energy_price_eur_kWh"]
            cost_per_m3 = cost_h / max(flow_m3h, 1e-9)
            self.var_d_pabs.set(f"{Pabs_kW:.1f} kW")
            self.var_d_cost.set(f"{cost_per_m3:.3f} €/m³")
        else:
            self.var_d_pto.set("Sin intersección en rango")
            self.var_d_pabs.set("—")
            self.var_d_cost.set("—")

        self.var_e_val.set(f"hf_válvula = {hf_valve:.2f} m; ΔPc ≈ {dPc_kg:.2f} kg/cm²")

if __name__ == "__main__":
    app = App()
    app.mainloop()
