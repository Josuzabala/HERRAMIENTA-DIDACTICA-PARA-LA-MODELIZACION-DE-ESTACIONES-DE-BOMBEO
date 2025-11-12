# -*- coding: utf-8 -*-
"""
TFG – Problema 9.1 (GUI) con customtkinter
Extensión: válvula de asiento en aspiración + variación de rpm del rodete
(leyenda fuera, tres puntos de funcionamiento, tres curvas de bomba)
"""

import numpy as np
import customtkinter as ctk
from tkinter import messagebox, ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# ----------- Utilidades hidráulicas ----------- #
def hazen_williams_k_per_length(D_m, C):
    return 10.67 / (C**1.852 * D_m**4.87)

def choose_CHW_from_eps_over_D(eps_cm, D_m):
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

# ----------- Curva de la bomba base (referencia 1490 rpm) ----------- #
Qb_ls = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65], dtype=float)
Hb_m  = np.array([38,38,38,38,38,37,36,34,32,30,26,20,13,0], dtype=float)
eta_p = np.array([ 0,26,45,58,67,74,77,78,77,75,68,80,30,0], dtype=float)

N_REF_RPM = 1490.0
RPM_COMPARE = [1490.0, 1316.0, 1221.0]  # las tres rpm a superponer

def scaled_pump_arrays(n_rpm):
    a = float(n_rpm) / N_REF_RPM
    Q_scaled = Qb_ls * a
    H_scaled = Hb_m * (a**2)
    eta_scaled = eta_p.copy()
    return Q_scaled, H_scaled, eta_scaled

def H_bomba_n(Ql, n_rpm):
    Qs, Hs, _ = scaled_pump_arrays(n_rpm)
    return interp_xy(Qs, Hs, Ql)

def eta_bomba_n(Ql, n_rpm):
    Qs, _, etas = scaled_pump_arrays(n_rpm)
    return interp_xy(Qs, etas, Ql)/100.0

# ----------- Válvula (Kv relativo Fisher) ----------- #
VALVE_OPEN_PCT = np.array([0, 10, 20, 40, 60, 80, 100], dtype=float)
VALVE_PHI_REL  = np.array([0.00, 0.20, 0.30, 0.50, 0.60, 0.80, 1.00], dtype=float)

def phi_from_open(pct_open):
    pct = max(0.0, min(100.0, float(pct_open)))
    return float(interp_xy(VALVE_OPEN_PCT, VALVE_PHI_REL, pct))

def hf_valve_from_Kv(Q_lps, s_rel, Kv_max_m3h, pct_open):
    # hf = 10.197*s*(Q_m3h/Kv)^2 ; a 100% → 0
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
        self.title("Problema 9.1 – Bombeo entre depósitos (GUI)")
        self.geometry("1200x900")
        self.minsize(1100, 800)

        # Estado
        self.delta_z = 10.0
        self.Q_plot = np.linspace(0, Qb_ls[-1], 400)
        self.k_lps = None
        self.last_Qpf = None; self.last_Hpf = None; self.last_eta = None
        self._update_job = None

        # Fuentes
        self.font_h1 = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=14)

        # Pestañas
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_datos = self.tabs.add("Interactivo")
        self.tab_result = self.tabs.add("Resultados")
        self.tab_notas = self.tabs.add("Notas")

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

        # Vars
        self.s_var   = ctk.StringVar(value="1.2")
        self.nu_var  = ctk.StringVar(value="1e-6")
        self.D1_var  = ctk.StringVar(value="200")
        self.L1_var  = ctk.StringVar(value="200")
        self.D2_var  = ctk.StringVar(value="150")
        self.L2_var  = ctk.StringVar(value="500")
        self.eps_var = ctk.StringVar(value="0.01")  # cm
        self.PB_var  = ctk.StringVar(value="")
        self.rpm_var   = ctk.StringVar(value=f"{int(N_REF_RPM)}")  # 1490
        self.open_var  = ctk.StringVar(value="100")                # %
        self.kvmax_var = ctk.StringVar(value="1600")               # Kv_max m3/h

        ctk.CTkLabel(controls, text="Parámetros", font=self.font_h1).pack(anchor="w", padx=6, pady=(6,2))

        # Helper: slider + entry sincronizados
        def add_entry_slider(parent, label, var, unit, vmin, vmax, step, fmt):
            row = ctk.CTkFrame(parent); row.pack(fill="x", padx=6, pady=(6,0))
            ctk.CTkLabel(row, text=label, font=self.font_body).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=unit, font=self.font_body).grid(row=0, column=2, sticky="w", padx=(6,0))
            sframe = ctk.CTkFrame(parent); sframe.pack(fill="x", padx=6, pady=(2,8))
            sframe.grid_columnconfigure(0, weight=1)
            slider = ctk.CTkSlider(sframe, from_=vmin, to=vmax, number_of_steps=max(1,int((vmax-vmin)/step)))
            try: init = float(str(var.get()).replace(",", "."))
            except Exception: init = vmin
            init = min(max(init, vmin), vmax)
            slider.set(init)
            slider.grid(row=0, column=0, sticky="ew", padx=(4,6), pady=2)
            ent = ctk.CTkEntry(sframe, textvariable=var, width=80, justify="right")
            ent.grid(row=0, column=1, sticky="e")
            def on_slide(val):
                var.set(fmt.format(val)); self._schedule_recalc()
            slider.configure(command=on_slide)
            def on_entry_change(*_):
                txt = str(var.get()).replace(",", ".").strip()
                try: x = float(txt)
                except ValueError: return
                x = min(max(x, vmin), vmax); slider.set(x); self._schedule_recalc()
            var.trace_add("write", on_entry_change)
            def on_focus_out(_):
                txt = str(var.get()).replace(",", ".").strip()
                try: x = float(txt)
                except ValueError: x = slider.get()
                x = min(max(x, vmin), vmax); var.set(fmt.format(x)); slider.set(x)
            ent.bind("<FocusOut>", on_focus_out); ent.bind("<Return>", lambda e: on_focus_out(e))
            return ent, slider

        self.ent_s,  self.sl_s  = add_entry_slider(controls, "s (densidad relativa)", self.s_var, "-", 0.8, 1.4, 0.01, "{:.2f}")
        row_nu = ctk.CTkFrame(controls); row_nu.pack(fill="x", padx=6, pady=(6,8))
        ctk.CTkLabel(row_nu, text="ν (m²/s)", font=self.font_body).pack(side="left")
        ctk.CTkEntry(row_nu, textvariable=self.nu_var, width=100, justify="right").pack(side="left", padx=6)
        ctk.CTkLabel(row_nu, text="m²/s", font=self.font_body).pack(side="left")
        self.ent_D1, self.sl_D1 = add_entry_slider(controls, "D1", self.D1_var, "mm", 50.0, 400.0, 1.0, "{:.0f}")
        self.ent_L1, self.sl_L1 = add_entry_slider(controls, "L1", self.L1_var, "m", 10.0, 1000.0, 1.0, "{:.0f}")
        self.ent_D2, self.sl_D2 = add_entry_slider(controls, "D2", self.D2_var, "mm", 50.0, 400.0, 1.0, "{:.0f}")
        self.ent_L2, self.sl_L2 = add_entry_slider(controls, "L2", self.L2_var, "m", 10.0, 1500.0, 1.0, "{:.0f}")
        self.ent_eps,self.sl_eps= add_entry_slider(controls, "ε (cm)", self.eps_var, "cm", 0.001, 0.10, 0.001, "{:.3f}")

        ctk.CTkLabel(controls, text="Bomba y válvula", font=self.font_h2).pack(anchor="w", padx=6, pady=(8,2))
        self.ent_rpm, self.sl_rpm   = add_entry_slider(controls, "n (velocidad de giro)", self.rpm_var, "rpm", 1200.0, 1800.0, 1.0, "{:.0f}")
        self.ent_open, self.sl_open = add_entry_slider(controls, "Apertura válvula", self.open_var, "%", 0.0, 100.0, 1.0, "{:.0f}")

        kv_row = ctk.CTkFrame(controls); kv_row.pack(fill="x", padx=6, pady=(4,8))
        ctk.CTkLabel(kv_row, text="Kv_max (m³/h) válvula", font=self.font_body).pack(side="left")
        ctk.CTkEntry(kv_row, textvariable=self.kvmax_var, width=90, justify="right").pack(side="left", padx=6)

        btns = ctk.CTkFrame(controls); btns.pack(fill="x", padx=6, pady=(8,12))
        self.calc_btn = ctk.CTkButton(btns, text="Calcular a) b) c)", command=self.calcular)
        self.calc_btn.pack(fill="x")

        pres = ctk.CTkFrame(controls); pres.pack(fill="x", padx=6, pady=(4,8))
        ctk.CTkLabel(pres, text="d) PB (kg/cm²) manométrica en B", font=self.font_body).pack(anchor="w")
        pb_row = ctk.CTkFrame(pres); pb_row.pack(fill="x", pady=4)
        ctk.CTkEntry(pb_row, textvariable=self.PB_var, width=120, justify="right").pack(side="left", padx=4)
        self.d_btn = ctk.CTkButton(pb_row, text="Aplicar d) presurización",
                                   command=self.aplicar_presion_B, state="disabled")
        self.d_btn.pack(side="left", padx=4)

        ctk.CTkButton(controls, text="Limpiar", command=self.limpiar).pack(fill="x", padx=6, pady=(6,10))

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

        # Derecha: gráfico y resultados
        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=4)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        plot_frame = ctk.CTkFrame(right)
        plot_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4,2))
        self.fig = plt.Figure(figsize=(6.8, 4.8))
        self.ax = self.fig.add_subplot(111)
        self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características y punto de funcionamiento"); self.ax.grid(True)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Resultados en dos columnas
        res = ctk.CTkFrame(right)
        res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1)
        res.grid_columnconfigure(1, weight=1)

        left_col  = ctk.CTkFrame(res); left_col.grid(row=0, column=0, sticky="nsew", padx=(6,3), pady=6)
        right_col = ctk.CTkFrame(res); right_col.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)

        ctk.CTkLabel(left_col, text="Resultados a, b, c", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.lbl_a = ctk.CTkLabel(left_col, text="[a] Curva característica de la instalación", font=self.font_h2)
        self.lbl_a.pack(anchor="w", padx=8, pady=(6,0))
        self.txt_a = ctk.CTkTextbox(left_col, height=70, font=self.font_body)
        self.txt_a.pack(fill="x", padx=8, pady=(2,4))
        self.txt_a.insert("end", "Pendiente de cálculo…\n"); self.txt_a.configure(state="disabled")

        self.lbl_b = ctk.CTkLabel(left_col, text="[b] Punto de funcionamiento", font=self.font_h2)
        self.lbl_b.pack(anchor="w", padx=8, pady=(4,0))
        self.txt_b = ctk.CTkTextbox(left_col, height=56, font=self.font_body)
        self.txt_b.pack(fill="x", padx=8, pady=(2,4))
        self.txt_b.insert("end", "Pendiente de cálculo…\n"); self.txt_b.configure(state="disabled")

        self.lbl_c = ctk.CTkLabel(left_col, text="[c] Potencia absorbida", font=self.font_h2)
        self.lbl_c.pack(anchor="w", padx=8, pady=(4,0))
        self.txt_c = ctk.CTkTextbox(left_col, height=48, font=self.font_body)
        self.txt_c.pack(fill="x", padx=8, pady=(2,6))
        self.txt_c.insert("end", "Pendiente de cálculo…\n"); self.txt_c.configure(state="disabled")

        ctk.CTkLabel(right_col, text="Resultados d, e", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.lbl_d = ctk.CTkLabel(right_col, text="[d] Con depósito B presurizado", font=self.font_h2)
        self.lbl_d.pack(anchor="w", padx=8, pady=(6,0))
        self.txt_d = ctk.CTkTextbox(right_col, height=64, font=self.font_body)
        self.txt_d.pack(fill="x", padx=8, pady=(2,6))
        self.txt_d.insert("end", "Introduce PB y pulsa el botón.\n"); self.txt_d.configure(state="disabled")

        self.lbl_e = ctk.CTkLabel(right_col, text="[e] PB_límite en el depósito B (umbral sin circulación)", font=self.font_h2)
        self.lbl_e.pack(anchor="w", padx=8, pady=(4,0))
        self.txt_e = ctk.CTkTextbox(right_col, height=48, font=self.font_body)
        self.txt_e.pack(fill="x", padx=8, pady=(2,8))
        self.txt_e.insert("end", "Disponible tras aplicar d).\n"); self.txt_e.configure(state="disabled")

    # -------------------- TAB: RESULTADOS -------------------- #
    def _build_resultados(self):
        box = ctk.CTkFrame(self.tab_result)
        box.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_res = ctk.CTkTextbox(box, font=self.font_body)
        self.text_res.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_res.insert("end", "Pulsa ‘Calcular’ en la pestaña Interactivo.\n")
        self.text_res.configure(state="disabled")

    # -------------------- TAB: NOTAS -------------------- #
    def _build_notas(self):
        notes = ctk.CTkTextbox(self.tab_notas, font=self.font_body)
        notes.pack(fill="both", expand=True, padx=8, pady=8)
        notes.insert(
            "end",
            ("Notas:\n"
             "• Hmi = Δz + hf. Hazen–Williams por tramos.\n"
             "• Bomba referida a n_ref=1490 rpm. Afinidad: Q~n, H~n², P~n³.\n"
             "• Válvula globo: Kv(α)=Φ(α)·Kv_max; hf = 10.197·s·(Qm3/h/Kv)^2.\n"
             "• A 100% apertura: hf válvula = 0 (compatibilidad base).\n")
        )
        notes.configure(state="disabled")

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
        self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características y punto de funcionamiento")
        self.ax.plot(Qb_ls, Hb_m, "o-", label=f"CC bomba (n={int(N_REF_RPM)} rpm)", linewidth=2)
        self.ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
        self.canvas.draw_idle()

    def _parse_inputs(self):
        try:
            s   = float(self.s_var.get().replace(",", "."))
            nu  = float(self.nu_var.get().replace(",", "."))
            D1m = float(self.D1_var.get().replace(",", "."))/1000.0
            L1  = float(self.L1_var.get().replace(",", "."))
            D2m = float(self.D2_var.get().replace(",", "."))/1000.0
            L2  = float(self.L2_var.get().replace(",", "."))
            eps = float(self.eps_var.get().replace(",", "."))
            rpm = float(self.rpm_var.get().replace(",", "."))
            open_pct = float(self.open_var.get().replace(",", "."))
            kvmax = float(self.kvmax_var.get().replace(",", "."))
            if D1m <= 0 or D2m <= 0 or L1 <= 0 or L2 <= 0 or s <= 0 or kvmax <= 0:
                raise ValueError
            rpm = min(max(rpm, 1200.0), 1800.0)
            open_pct = round(min(max(open_pct, 0.0), 100.0))
            return s, nu, D1m, L1, D2m, L2, eps, rpm, open_pct, kvmax
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
        base = (self.delta_z + dH0) + k_lps*(q_lps**1.852)
        hf_val = hf_valve_from_Kv(q_lps, s_rel, kvmax_m3h, pct_open)
        return base + hf_val

    # -------------------- Acciones principales -------------------- #
    def calcular(self):
        parsed = self._parse_inputs()
        if not parsed: return
        s, nu, D1m, L1, D2m, L2, eps_cm, rpm, open_pct, kvmax = parsed

        C1, C2, J1_lps, J2_lps, k_lps = self._cci_params(D1m, L1, D2m, L2, eps_cm)
        self.k_lps = k_lps

        qs = np.arange(0.0, 61.0+1e-9, 5.0)

        def equilibrio(q):  # contra CCI actual
            return H_bomba_n(q, rpm) - self.H_inst_lps(q, k_lps, s, kvmax, open_pct)

        Qmax_busca = max(65.0, Qb_ls[-1]*rpm/N_REF_RPM)
        Qpf = bisect_root(equilibrio, 0.0, Qmax_busca, tol=1e-8)

        if Qpf is None:
            self._plot_curvas(rpm, k_lps, s, kvmax, open_pct, Qpf=None)
            self._pinta_resultados_sin_interseccion(C1, C2, J1_lps, J2_lps, k_lps, rpm, open_pct, kvmax, s)
            self.d_btn.configure(state="disabled")
            for row in self.tree.get_children(): self.tree.delete(row)
            for q in qs:
                self.tree.insert("", "end", values=(f"{q:5.0f}", f"{self.H_inst_lps(q, k_lps, s, kvmax, open_pct):6.2f}"))
            return

        Hpf = H_bomba_n(Qpf, rpm); etapf = eta_bomba_n(Qpf, rpm)

        gamma = 9800.0 * s
        Pabs_kW = gamma*(Qpf/1000.0)*Hpf/max(etapf,1e-9)/1000.0

        Hb0 = H_bomba_n(0.0, rpm)
        dH0_lim_m = max(Hb0 - self.delta_z, 0.0)
        PB_lim_kPa = 9800.0 * s * dH0_lim_m / 1000.0
        PB_lim_kgcm2 = s * dH0_lim_m / 10.0

        self.text_res.configure(state="normal"); self.text_res.delete("1.0","end")
        self.text_res.insert("end","[a] Curva característica de la instalación:\n")
        self.text_res.insert("end",f"    C_HW1={C1:.0f}, C_HW2={C2:.0f}\n")
        self.text_res.insert("end",f"    Hmi(Q) = {self.delta_z:.3f} + {k_lps:.6f} · Q^1.852 + hf_válvula(Q)\n\n")
        self.text_res.insert("end","[b] Punto de funcionamiento:\n")
        self.text_res.insert("end",f"    n = {rpm:.0f} rpm, apertura = {open_pct:.0f} %, Kv_max = {kvmax:.0f} m³/h\n")
        self.text_res.insert("end",f"    Q = {Qpf:.2f} l/s,  H = {Hpf:.2f} m,  η = {etapf*100:.1f} %\n\n")
        self.text_res.insert("end","[c] Potencia absorbida:\n")
        self.text_res.insert("end",f"    P_abs ≈ {Pabs_kW:.2f} kW\n\n")
        self.text_res.insert("end","[e] PB_límite en depósito B:\n")
        self.text_res.insert("end",f"    ΔH0_lím = max(Hb(0)−Δz,0) = {dH0_lim_m:.2f} mcl → PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm² (≈ {PB_lim_kPa:.0f} kPa)\n")
        self.text_res.configure(state="disabled")

        for row in self.tree.get_children(): self.tree.delete(row)
        for q in qs:
            self.tree.insert("", "end", values=(f"{q:5.0f}", f"{self.H_inst_lps(q, k_lps, s, kvmax, open_pct):6.2f}"))

        self._plot_curvas(rpm, k_lps, s, kvmax, open_pct, Qpf=Qpf, Hpf=Hpf)

        self._set_text(self.txt_a,
            f"C_HW1={C1:.0f}, C_HW2={C2:.0f} (según ε/D).\n"
            f"Hmi(Q) = {self.delta_z:.2f} + {k_lps:.6f}·Q^1.852 + hf_válvula(Q).\n"
        )
        self._set_text(self.txt_b, f"n = {rpm:.0f} rpm, apertura = {open_pct:.0f} %.\nQ = {Qpf:.2f} l/s, H = {Hpf:.2f} m, η = {etapf*100:.1f} %.\n")
        self._set_text(self.txt_c, f"P_abs ≈ {Pabs_kW:.2f} kW.\n")
        self._set_text(self.txt_e, f"PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm²  (≈ {PB_lim_kPa:.0f} kPa).\n")

        self.last_Qpf, self.last_Hpf, self.last_eta = Qpf, Hpf, etapf
        self.d_btn.configure(state="normal")

    def _plot_curvas(self, rpm, k_lps, s, kvmax, open_pct, Qpf=None, Hpf=None):
        """
        CCI + tres curvas de bomba (1490, 1316, 1221 rpm).
        Leyenda SOLO con las 3 curvas de bomba, colocada arriba-izquierda.
        """
        self.ax.cla(); self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características y punto de funcionamiento")

        Q_plot = self.Q_plot

        # CCI base y CCI con válvula (ocultas en leyenda)
        H_inst_base = [self.H_inst_lps(q, k_lps, s, kvmax, 100.0)    for q in Q_plot]
        H_inst      = [self.H_inst_lps(q, k_lps, s, kvmax, open_pct) for q in Q_plot]
        self.ax.plot(Q_plot, H_inst_base, linestyle="--", linewidth=1.5,
                    color="tab:blue", label="_nolegend_")
        self.ax.plot(Q_plot, H_inst, linewidth=2, color="orange", label="_nolegend_")

        # Curvas de bomba
        colores = {1490.0: "green", 1316.0: "red", 1221.0: "purple"}
        pump_handles, pump_labels = [], []

        for ncmp in [1490.0, 1316.0, 1221.0]:
            Qs, Hs, _ = scaled_pump_arrays(ncmp)
            ln, = self.ax.plot(Qs, Hs, "o-", linewidth=2, color=colores.get(ncmp))
            pump_handles.append(ln)
            pump_labels.append(f"CC bomba (n={int(ncmp)} rpm)")

            # Punto de funcionamiento de ESA rpm (círculo, SIN leyenda)
            def equilibrio(q): return H_bomba_n(q, ncmp) - self.H_inst_lps(q, k_lps, s, kvmax, open_pct)
            Qpf_n = bisect_root(equilibrio, 0.0, max(65.0, Qb_ls[-1]*ncmp/N_REF_RPM), tol=1e-8)
            if Qpf_n is not None:
                Hpf_n = H_bomba_n(Qpf_n, ncmp)
                self.ax.scatter([Qpf_n], [Hpf_n], s=60, marker='o', edgecolors='k',
                                color=colores.get(ncmp), zorder=5, label="_nolegend_")

        # Base piezométrica (sin leyenda)
        self.ax.axhline(self.delta_z, linestyle=":", linewidth=1, color="tab:blue")
        self.ax.text(Q_plot.max()*0.02, self.delta_z+0.5, "Base piezométrica", fontsize=9)

        # Leyenda: solo bombas, arriba-izquierda
        self.ax.legend(pump_handles, pump_labels, loc="upper left", framealpha=0.95)
        self.canvas.draw_idle()

    def _pinta_resultados_sin_interseccion(self, C1, C2, J1, J2, k_lps, rpm, open_pct, kvmax, s):
        self.text_res.configure(state="normal"); self.text_res.delete("1.0","end")
        self.text_res.insert("end","[a] Curva característica de la instalación:\n")
        self.text_res.insert("end",f"    C_HW1={C1:.0f}, C_HW2={C2:.0f}\n")
        self.text_res.insert("end",f"    Hmi(Q) = {self.delta_z:.3f} + {k_lps:.6f}·Q^1.852 + hf_válvula(Q)\n\n")
        self.text_res.insert("end","[b] Punto de funcionamiento:\n")
        self.text_res.insert("end",f"    n = {rpm:.0f} rpm, apertura = {open_pct:.0f} %, Kv_max = {kvmax:.0f} m³/h\n")
        self.text_res.insert("end","    Sin intersección: la válvula en aspiración impide el caudal (Q=0).\n\n")
        self.text_res.insert("end","[c] Potencia absorbida:\n")
        self.text_res.insert("end","    No aplicable (sin Q).\n\n")
        Hb0 = H_bomba_n(0.0, rpm)
        dH0_lim_m = max(Hb0 - self.delta_z, 0.0)
        PB_lim_kPa = 9800.0 * s * dH0_lim_m / 1000.0
        PB_lim_kgcm2 = s * dH0_lim_m / 10.0
        self.text_res.insert("end","[e] PB_límite:\n")
        self.text_res.insert("end",f"    ΔH0_lím = {dH0_lim_m:.2f} mcl → PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm² (≈ {PB_lim_kPa:.0f} kPa)\n")
        self.text_res.configure(state="disabled")

    # -------------------- d) Presurización en B -------------------- #
    def aplicar_presion_B(self):
        parsed = self._parse_inputs()
        if not parsed:
            messagebox.showinfo("Primero calcula", "Calcula a) b) c) antes de aplicar d).")
            return
        s, nu, D1m, L1, D2m, L2, eps_cm, rpm, open_pct, kvmax = parsed
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
        def equilibrio(q):  return H_bomba_n(q, rpm) - H_inst_pres(q)

        Qpf2 = bisect_root(equilibrio, 0.0, max(65.0, Qb_ls[-1]*rpm/N_REF_RPM), tol=1e-8)

        Hb0 = H_bomba_n(0.0, rpm)
        dH0_lim_m = max(Hb0 - self.delta_z, 0.0)
        PB_lim_kPa = 9800.0 * s * dH0_lim_m / 1000.0
        PB_lim_kgcm2 = s * dH0_lim_m / 10.0

        if Qpf2 is None:
            messagebox.showwarning("Sin intersección", "Con esa PB no hay corte entre CCI y CCB.")
            self._set_text(self.txt_d, f"PB = {PB:.3f} kg/cm² → ΔH0 ≈ {dH0:.2f} mcl.\nNo hay intersección.\n")
        else:
            Hpf2 = H_bomba_n(Qpf2, rpm); eta2 = eta_bomba_n(Qpf2, rpm)
            gamma = 9800.0 * s
            Pabs2_kW = gamma*(Qpf2/1000.0)*Hpf2/max(eta2,1e-9)/1000.0

            self.text_res.configure(state="normal")
            self.text_res.insert("end", "\n[d] Con depósito B presurizado:\n")
            self.text_res.insert("end", f"    PB = {PB:.3f} kg/cm² → ΔH0 ≈ {dH0:.2f} mcl\n")
            self.text_res.insert("end", f"    Q' = {Qpf2:.2f} l/s,  H' = {Hpf2:.2f} m,  η' = {eta2*100:.1f} %,  P'_abs ≈ {Pabs2_kW:.2f} kW\n")
            self.text_res.configure(state="disabled")

            # Gráfica con presurización
            self.ax.cla(); self.ax.grid(True)
            self.ax.set_xlabel("Q (l/s)"); self.ax.set_ylabel("H (m)")
            self.ax.set_title("Efecto de presurizar el depósito B")
            Q_plot = self.Q_plot
            base  = [self.H_inst_lps(q, self.k_lps, s, kvmax, open_pct) for q in Q_plot]
            shift = [H_inst_pres(q) for q in Q_plot]
            Qs, Hs, _ = scaled_pump_arrays(rpm)
            self.ax.plot(Q_plot, base,  label="CCI instalación", linewidth=2)
            self.ax.plot(Q_plot, shift, label="CCI con PB", linewidth=2)
            self.ax.plot(Qs, Hs, "o-", label=f"CC bomba (n={int(rpm)} rpm)", linewidth=2)
            if self.last_Qpf is not None:
                self.ax.plot([self.last_Qpf], [self.last_Hpf], "s", markersize=8, label="Punto base")
            self.ax.plot([Qpf2], [Hpf2], "o", markersize=6, label="Punto con PB")
            self.ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
            self.canvas.draw_idle()

        estado = "PB ≥ PB_lím ⇒ no hay circulación" if PB >= PB_lim_kgcm2 else "PB < PB_lím ⇒ hay circulación"
        self._set_text(self.txt_e, f"PB_lím ≈ {PB_lim_kgcm2:.2f} kg/cm² (≈ {PB_lim_kPa:.0f} kPa). {estado}.\n")

    # -------------------- Utilidades UI -------------------- #
    def limpiar(self):
        self.text_res.configure(state="normal"); self.text_res.delete("1.0","end")
        self.text_res.insert("end", "Pulsa ‘Calcular’ en la pestaña Interactivo.\n")
        self.text_res.configure(state="disabled")
        for row in self.tree.get_children(): self.tree.delete(row)
        self._set_text(self.txt_a, "Pendiente de cálculo…\n")
        self._set_text(self.txt_b, "Pendiente de cálculo…\n")
        self._set_text(self.txt_c, "Pendiente de cálculo…\n")
        self._set_text(self.txt_d, "Introduce PB y pulsa el botón.\n")
        self._set_text(self.txt_e, "Disponible tras aplicar d).\n")
        self._draw_static_ccb()
        self.k_lps = None
        self.last_Qpf = self.last_Hpf = self.last_eta = None
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

def main():
    App().mainloop()

if __name__ == "__main__":
    main()
