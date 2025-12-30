# -*- coding: utf-8 -*-
"""
TFG – Problema 9.2 (GUI) - Versión Optimizada Tutora V2

Cambios:
- Gráfica más grande (zoom centrado en la intersección).
- Redistribución de resultados: A y B a la izquierda, C y D a la derecha.
- Aprovechamiento del espacio (cuadros de texto más ajustados).
- Panel izquierdo fijo y estético.
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
Qb_base_ls = np.array([40, 50, 60, 70, 80, 90], dtype=float)
Hb_base_m  = np.array([22, 22, 22, 21.8, 21.0, 19.7], dtype=float)
eta_base   = np.array([0.72, 0.76, 0.79, 0.78, 0.76, 0.72], dtype=float)
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
        self.title("Problema 9.2 – Fuente de chorro vertical (GUI)")
        self.geometry("1280x900")
        self.minsize(1120, 800)

        self.Q_plot = np.linspace(0.0, 140.0, 500)  # Rango amplio para cálculos
        self._update_job = None

        # Estado de bomba activa
        self.active_D = 256.0
        self.pump_curves = {D: gen_curve_for_diameter(D) for D in RODETES_MM}

        # Fuentes
        self.font_h1 = ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=13)

        # Pestañas
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.tab_inter = self.tabs.add("Interactivo")
        self.tab_res   = self.tabs.add("Resultados")
        self.tab_notas = self.tabs.add("Notas")

        self._build_interactivo()
        self._build_resultados()
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

        # Columna izquierda: controles + botones
        leftcol = ctk.CTkFrame(root, width=380)
        leftcol.grid(row=0, column=0, sticky="nsw", padx=(0, 10), pady=0)
        leftcol.grid_columnconfigure(0, weight=1)

        controls = ctk.CTkFrame(leftcol, fg_color="transparent")
        controls.pack(fill="x", expand=False, pady=(0, 10))

        # Variables por defecto
        self.defaults = dict(
            s="1.0", z="3.0", Dp="175", Le="75", eps="0.015",
            Dc="80", kc="0.8", h8="8.0", hobj="8.0", precio="0.11"
        )
        self.s_var     = ctk.StringVar(value=self.defaults["s"])
        self.z_var     = ctk.StringVar(value=self.defaults["z"])
        self.Dp_var    = ctk.StringVar(value=self.defaults["Dp"])
        self.Le_var    = ctk.StringVar(value=self.defaults["Le"])
        self.eps_var   = ctk.StringVar(value=self.defaults["eps"])
        self.Dc_var    = ctk.StringVar(value=self.defaults["Dc"])
        self.kc_var    = ctk.StringVar(value=self.defaults["kc"])
        self.h8_var    = ctk.StringVar(value=self.defaults["h8"])
        self.hobj_var  = ctk.StringVar(value=self.defaults["hobj"])
        self.precio_var= ctk.StringVar(value=self.defaults["precio"])

        # --- SECCIÓN 1: CONSTANTES ---
        ctk.CTkLabel(controls, text="Datos Fijos (Enunciado)", font=self.font_h2).pack(anchor="w", padx=8, pady=(8, 4))
        grid_const = ctk.CTkFrame(controls)
        grid_const.pack(fill="x", padx=6, pady=4)
        
        def add_const_box(parent, r, c, label, var_name, unit):
            f = ctk.CTkFrame(parent, fg_color="#EBEBEB", corner_radius=6)
            f.grid(row=r, column=c, padx=4, pady=4, sticky="ew")
            ctk.CTkLabel(f, text=label, font=ctk.CTkFont(size=11), text_color="gray30").pack()
            ctk.CTkLabel(f, text=f"{self.defaults[var_name]} {unit}", font=ctk.CTkFont(size=14, weight="bold"), text_color="black").pack()

        grid_const.grid_columnconfigure((0,1), weight=1)
        add_const_box(grid_const, 0, 0, "z (Elevación)", "z", "m")
        add_const_box(grid_const, 0, 1, "D tubería", "Dp", "mm")
        add_const_box(grid_const, 1, 0, "L equivalente", "Le", "m")
        add_const_box(grid_const, 1, 1, "Rugosidad", "eps", "cm")
        add_const_box(grid_const, 2, 0, "D boquilla", "Dc", "mm")
        add_const_box(grid_const, 2, 1, "k boquilla", "kc", "")

        # --- SECCIÓN 2: VARIABLES (SLIDERS) ---
        ctk.CTkLabel(controls, text="Variables de Diseño", font=self.font_h2).pack(anchor="w", padx=8, pady=(12, 4))

        def add_entry_slider(parent, label, var, unit, vmin, vmax, step, fmt, trace_cb=None):
            row = ctk.CTkFrame(parent); row.pack(fill="x", padx=6, pady=(6,0))
            ctk.CTkLabel(row, text=label, font=self.font_body).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(row, text=unit,  font=self.font_body).grid(row=0, column=2, sticky="w", padx=(6,0))
            sframe = ctk.CTkFrame(parent); sframe.pack(fill="x", padx=6, pady=(2,10))
            sframe.grid_columnconfigure(0, weight=1)
            slider = ctk.CTkSlider(sframe, from_=vmin, to=vmax, number_of_steps=max(1, int(round((vmax-vmin)/step))))
            try: init = float(str(var.get()).replace(",", "."))
            except: init = vmin
            slider.set(min(max(init, vmin), vmax))
            slider.grid(row=0, column=0, sticky="ew", padx=(4,6), pady=2)
            ent = ctk.CTkEntry(sframe, textvariable=var, width=80, justify="right")
            ent.grid(row=0, column=1, sticky="e")

            def on_slide(val):
                var.set(fmt.format(val))
                if trace_cb: trace_cb()
                self._schedule_recalc()
            slider.configure(command=on_slide)
            
            def on_entry_change(*_):
                try: x = float(str(var.get()).replace(",", "."))
                except: return
                slider.set(min(max(x, vmin), vmax))
                if trace_cb: trace_cb()
                self._schedule_recalc()
            var.trace_add("write", on_entry_change)
            return ent, slider

        add_entry_slider(controls, "s (densidad relativa)", self.s_var, "-", 0.80, 1.40, 0.01, "{:.2f}")

        def sync_h_obj(*args):
            try: self.hobj_var.set(self.h8_var.get())
            except: pass
        add_entry_slider(controls, "h mínima (b)", self.h8_var, "m", 5.00, 10.0, 0.10, "{:.2f}", trace_cb=sync_h_obj)

        row_obj = ctk.CTkFrame(controls)
        row_obj.pack(fill="x", padx=6, pady=(0, 10))
        ctk.CTkLabel(row_obj, text="↳ h objetivo (d) [AUTO]", font=self.font_body, text_color="gray").pack(side="left")
        ctk.CTkEntry(row_obj, textvariable=self.hobj_var, width=80, justify="right", state="disabled", fg_color="#EEEEEE", text_color="gray40").pack(side="right")
        
        add_entry_slider(controls, "Precio energía", self.precio_var, "€/kWh", 0.00, 0.50, 0.01, "{:.2f}")

        btnrow = ctk.CTkFrame(leftcol)
        btnrow.pack(fill="x", pady=(20,0))
        btnrow.grid_columnconfigure((0,1,2), weight=1)
        ctk.CTkButton(btnrow, text="Calcular", command=self.calcular).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btnrow, text="Reiniciar", command=self.reiniciar_valores).grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        ctk.CTkButton(btnrow, text="Guardar", command=self.guardar_grafica).grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        # Lado derecho: Estructura Principal
        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, sticky="nsew")
        # Damos mucho más peso a la fila 0 (gráfica) para que coma sitio a los resultados
        right.grid_rowconfigure(0, weight=10) 
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # 1. Gráfica (Grande)
        g = ctk.CTkFrame(right); g.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4,2))
        self.fig = plt.Figure(figsize=(7.2, 5.5)) # Ligeramente más alta
        gs = self.fig.add_gridspec(1, 2, width_ratios=[2.5, 1.0])
        self.ax  = self.fig.add_subplot(gs[0, 0])
        self.ax_jet = self.fig.add_subplot(gs[0, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=g)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)
        self.badge_artist = None

        # 2. Resultados (Divididos Izq/Der)
        res = ctk.CTkFrame(right)
        res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1)
        res.grid_columnconfigure(1, weight=1)
        res.grid_rowconfigure(0, weight=1)

        # Columna Izquierda (A, B)
        col_left = ctk.CTkFrame(res, fg_color="transparent")
        col_left.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        
        ctk.CTkLabel(col_left, text="Resultados A y B", font=self.font_h1).pack(anchor="w", padx=4)
        self.txt_a = ctk.CTkTextbox(col_left, height=60, font=self.font_body) # Altura reducida
        self.txt_a.pack(fill="x", padx=4, pady=(2,4))
        
        self.txt_b = ctk.CTkTextbox(col_left, height=50, font=self.font_body)
        self.txt_b.pack(fill="x", padx=4, pady=(2,4))
        
        self.pump_bar = ctk.CTkFrame(col_left)
        self.pump_bar.pack(fill="x", padx=4, pady=2)
        ctk.CTkLabel(self.pump_bar, text="Bombas disponibles:", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=4)
        self.pump_labels = {}
        row_p = ctk.CTkFrame(self.pump_bar, fg_color="transparent")
        row_p.pack(fill="x", pady=2)
        for D in RODETES_MM:
            lbl = ctk.CTkLabel(row_p, text=f"{int(D)}", corner_radius=6, padx=6, pady=2, font=ctk.CTkFont(size=11))
            lbl.pack(side="left", padx=2)
            self.pump_labels[D] = lbl

        # Columna Derecha (C, D)
        col_right = ctk.CTkFrame(res, fg_color="transparent")
        col_right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        
        ctk.CTkLabel(col_right, text="Resultados C y D", font=self.font_h1).pack(anchor="w", padx=4)
        self.txt_c = ctk.CTkTextbox(col_right, height=60, font=self.font_body)
        self.txt_c.pack(fill="x", padx=4, pady=(2,4))
        
        self.txt_d = ctk.CTkTextbox(col_right, height=60, font=self.font_body) # Altura reducida
        self.txt_d.pack(fill="x", padx=4, pady=(2,4))

        # Inicializar textos
        for tb in (self.txt_a, self.txt_b, self.txt_c, self.txt_d):
            tb.insert("end", "Pendiente...\n")
            tb.configure(state="disabled")

    # -------------------- TAB: RESULTADOS -------------------- #
    def _build_resultados(self):
        box = ctk.CTkFrame(self.tab_res); box.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_res = ctk.CTkTextbox(box, font=self.font_body)
        self.text_res.pack(fill="both", expand=True, padx=8, pady=8)
        self.text_res.insert("end", "Pulsa ‘Calcular’ en la pestaña Interactivo.\n")
        self.text_res.configure(state="disabled")

    # -------------------- TAB: NOTAS -------------------- #
    def _build_notas(self):
        notes = ctk.CTkTextbox(self.tab_notas, font=self.font_body)
        notes.pack(fill="both", expand=True, padx=8, pady=8)
        notes.insert("end", "Notas del problema 9.2...")
        notes.configure(state="disabled")

    # -------------------- Dibujo Chorro -------------------- #
    def _draw_jet(self, h_jet_m: float, h_obj_m: float | None = None):
        ax = self.ax_jet
        ax.cla()
        ymax = max(5.0, h_jet_m, h_obj_m or 0.0) * 1.2
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.6, 0.6)
        ax.set_aspect('auto')
        ax.set_xticks([])
        ax.set_ylabel("Altura (m)")
        ax.set_title("Chorro")
        ax.plot([-0.5, 0.5], [0, 0], linewidth=2, color="black")
        ax.add_patch(plt.Rectangle((-0.1, 0.0), 0.2, 0.12, fill=True, color="gray"))
        ax.plot([0, 0], [0, h_jet_m], linewidth=6, alpha=0.85, solid_capstyle="round", color="tab:blue")
        if h_obj_m:
            ax.axhline(h_obj_m, linestyle="--", linewidth=1.2, color="red")
            ax.text(-0.55, h_obj_m, f"h_obj", va="center", color="red", fontsize=8)
        if h_obj_m and h_jet_m < h_obj_m:
            ax.text(0, ymax*0.92, "!", color="red", ha="center", weight="bold", fontsize=14)

    # -------------------- Dibujo Estático -------------------- #
    def _draw_static(self):
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características – 9.2")
        
        # Dibujar familia completa
        for D in RODETES_MM:
            Qc, Hc, _ = self.pump_curves[D]
            if D == self.active_D:
                self.ax.plot(Qc, Hc, "-", linewidth=3.0, color="tab:orange", label=f"Rodete {int(D)}", zorder=5)
            else:
                self.ax.plot(Qc, Hc, "--", linewidth=1.0, alpha=0.4, color="gray", zorder=2)
        
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, 50)
        self._update_badge()
        self.canvas.draw_idle()

    # -------------------- Animación -------------------- #
    def _animate_pump_switch(self, new_D_mm: float, on_done):
        # Versión simple para no molestar
        win = ctk.CTkToplevel(self)
        win.title("...")
        win.geometry("200x60")
        win.transient(self)
        ctk.CTkLabel(win, text=f"Cambiando a {int(new_D_mm)} mm").pack(pady=10)
        self.after(500, lambda: [win.destroy(), on_done()])

    # -------------------- Lógica -------------------- #
    def _parse(self):
        try:
            s = float(self.s_var.get().replace(",", "."))
            z = float(self.z_var.get().replace(",", "."))
            Dp_m = float(self.Dp_var.get().replace(",", "."))/1000.0
            Le = float(self.Le_var.get().replace(",", "."))
            eps = float(self.eps_var.get().replace(",", "."))
            Dc_m = float(self.Dc_var.get().replace(",", "."))/1000.0
            kc = float(self.kc_var.get().replace(",", "."))
            h8 = float(self.h8_var.get().replace(",", "."))
            hobj = h8
            precio = float(self.precio_var.get().replace(",", "."))
            return s, z, Dp_m, Le, eps, Dc_m, kc, h8, hobj, precio
        except: return None

    def _J_unit_lps(self, Dp_m, eps_cm):
        C = choose_CHW_from_eps_over_D(eps_cm, Dp_m)
        kL = hazen_williams_k_per_length(Dp_m, C)
        return C, kL / (1000.0**1.852)

    def _kv2g_from_Dc(self, Dc_m):
        A = np.pi*(Dc_m**2)/4.0
        return (1e-6) / (2*9.81*(A**2))

    def H_inst(self, Q_lps, z, J_lps, L, kv2g, kc, Kv_add=0.0):
        return z + (1.0 + kc + Kv_add) * kv2g * (Q_lps**2) + (J_lps*L) * (Q_lps**1.852)

    def Hb_activa(self, Ql):
        Qc, Hc, _ = self.pump_curves[self.active_D]
        return interp_xy(Qc, Hc, Ql)

    def eta_activa(self, Ql):
        Qc, _, eta = self.pump_curves[self.active_D]
        return float(interp_xy(Qc, eta, Ql))

    def _select_pump_for_requirement(self, Qmin, Hneed, margin=0.05):
        feasible = []
        for D in RODETES_MM:
            Qc, Hc, _ = self.pump_curves[D]
            Hb_at_Qmin = interp_xy(Qc, Hc, Qmin)
            if Hb_at_Qmin >= Hneed*(1+margin):
                feasible.append(D)
        if feasible:
            chosen = min(feasible)
            return chosen, (chosen != self.active_D), True
        return max(RODETES_MM), (max(RODETES_MM) != self.active_D), False

    def _update_pump_bar(self):
        for D, lbl in self.pump_labels.items():
            if D == self.active_D:
                lbl.configure(fg_color="#4CAF50", text_color="white")
            else:
                lbl.configure(fg_color="#E0E0E0", text_color="gray")

    def _update_badge(self):
        if self.badge_artist:
            try: self.badge_artist.remove()
            except: pass
        self.badge_artist = self.ax.text(
            0.98, 0.98, f"Rodete {int(self.active_D)}",
            transform=self.ax.transAxes, ha="right", va="top", fontsize=10,
            bbox=dict(facecolor="white", alpha=0.8, boxstyle="round,pad=0.2")
        )

    def calcular(self):
        parsed = self._parse()
        if not parsed: return
        s, z, Dp_m, Le, eps_cm, Dc_m, kc, h8, hobj, precio = parsed
        C_HW, J_lps = self._J_unit_lps(Dp_m, eps_cm)
        kv2g = self._kv2g_from_Dc(Dc_m)
        Jtot = J_lps * Le

        Q_min8 = np.sqrt(h8 / kv2g)
        Hmin8  = self.H_inst(Q_min8, z, J_lps, Le, kv2g, kc)
        new_D, changed, feasible = self._select_pump_for_requirement(Q_min8, Hmin8)

        def render_everything():
            self.active_D = new_D
            self._update_pump_bar()

            def equilibrio(q): return self.Hb_activa(q) - self.H_inst(q, z, J_lps, Le, kv2g, kc)
            Qpf = bisect_root(equilibrio, 0.0, 140.0)
            if Qpf is None: return
            Hpf = self.Hb_activa(Qpf)
            etapf = self.eta_activa(Qpf)
            Pabs_kW = (9800.0 * s) * (Qpf/1000.0) * Hpf / max(etapf,1e-9) / 1000.0
            coste = (Pabs_kW / (Qpf*3.6)) * precio

            Qobj = np.sqrt(hobj / kv2g)
            H_inst_base = self.H_inst(Qobj, z, J_lps, Le, kv2g, kc)
            H_bomb_obj  = self.Hb_activa(Qobj)
            hf_val = H_bomb_obj - H_inst_base
            Kv_add = hf_val / (kv2g * Qobj**2) if hf_val >= 0 else 0

            # --- Textos Optimizados ---
            self._set_text(self.txt_a, f"[a] CCI: H={z:.1f}+{(1+kc)*kv2g:.5f}Q²+{Jtot:.5f}Q^1.85\n    (C={C_HW:.0f}, J={J_lps:.5f}/m)")
            self._set_text(self.txt_b, f"[b] Q_min={Q_min8:.1f} l/s → H_req={Hmin8:.1f} m\n    Bomba: {int(self.active_D)} mm")
            self._set_text(self.txt_c, f"[c] Pto func: {Qpf:.1f} l/s @ {Hpf:.1f} m\n    η={etapf*100:.1f}%, Coste={coste:.4f}€/m³")
            
            if hf_val >= 0:
                self._set_text(self.txt_d, f"[d] Para h_obj={hobj:.1f}m (Q={Qobj:.1f}l/s):\n    Cerrar válvula: ΔH={hf_val:.2f} m")
            else:
                self._set_text(self.txt_d, f"[d] Imposible alcanzar {hobj:.1f}m\n    con esta bomba.")

            # --- GRÁFICA ZOOM ---
            self.ax.cla()
            self.ax.grid(True, linestyle=":", alpha=0.7)
            self.ax.set_xlabel("Q (l/s)")
            self.ax.set_ylabel("H (m)")
            
            # Dibujar todas las bombas
            for D in RODETES_MM:
                Qc, Hc, _ = self.pump_curves[D]
                if D == self.active_D:
                    self.ax.plot(Qc, Hc, "-", lw=3, color="tab:orange", zorder=5)
                else:
                    self.ax.plot(Qc, Hc, "--", lw=1, alpha=0.3, color="gray", zorder=2)

            # CCI
            Hcci = [self.H_inst(q, z, J_lps, Le, kv2g, kc) for q in self.Q_plot]
            self.ax.plot(self.Q_plot, Hcci, label="CCI", lw=2, color="tab:blue", zorder=4)

            # Punto funcionamiento
            self.ax.plot([Qpf], [Hpf], "s", markersize=8, color="black", zorder=6)
            
            # Punto D (Objetivo)
            if hf_val >= 0:
                 self.ax.plot([Qobj], [H_bomb_obj], "D", markersize=6, color="green", zorder=6)
                 self.ax.vlines(Qobj, H_inst_base, H_bomb_obj, colors="red", linestyles="solid", lw=2, label="Válvula")

            # **ZOOM INTELIGENTE**
            # Centramos en Qpf. Mostramos +/- 35 l/s y +/- 15 m
            q_center = Qpf
            h_center = Hpf
            
            margin_q = 35
            margin_h = 15

            self.ax.set_xlim(max(0, q_center - margin_q), q_center + margin_q)
            self.ax.set_ylim(max(0, h_center - margin_h), h_center + margin_h)
            
            self._update_badge()
            self._draw_jet(kv2g * (Qpf**2), hobj)
            self.canvas.draw_idle()

        if changed:
            self._animate_pump_switch(new_D, render_everything)
        else:
            render_everything()

    def reiniciar_valores(self):
        self.s_var.set(self.defaults["s"])
        self.z_var.set(self.defaults["z"])
        self.Dp_var.set(self.defaults["Dp"])
        self.Le_var.set(self.defaults["Le"])
        self.eps_var.set(self.defaults["eps"])
        self.Dc_var.set(self.defaults["Dc"])
        self.kc_var.set(self.defaults["kc"])
        self.h8_var.set(self.defaults["h8"])
        self.hobj_var.set(self.defaults["hobj"])
        self.precio_var.set(self.defaults["precio"])
        self.active_D = 256.0
        self._update_pump_bar()
        self._draw_static()
        for tb in (self.txt_a, self.txt_b, self.txt_c, self.txt_d):
            tb.configure(state="normal"); tb.delete("1.0", "end"); tb.insert("end", "Pendiente...\n"); tb.configure(state="disabled")

    def guardar_grafica(self):
        try:
            path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
            if path:
                self.fig.savefig(path, dpi=200, bbox_inches="tight")
                messagebox.showinfo("OK", "Guardado.")
        except: pass

def main():
    App().mainloop()

if __name__ == "__main__":
    main()