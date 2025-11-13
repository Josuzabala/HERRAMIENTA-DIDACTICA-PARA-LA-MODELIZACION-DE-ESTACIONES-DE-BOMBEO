# -*- coding: utf-8 -*-
"""
TFG – Problema 9.2 (GUI)

Cambios solicitados:
- Solo se dibuja la curva de la bomba activa; si la activa != 256 mm, se muestra además la 256 mm discontinua y tenue.
- Botonera fija abajo a la izquierda: Calcular, Reiniciar valores, Guardar gráfica.
- Reiniciar valores restablece parámetros a los del enunciado.
- Mantiene: selección automática de bomba, dashboard de rodetes, badge, barra “CAMBIANDO BOMBA…”, chorro azul y h_obj rojo.
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
        self.title("Problema 9.2 – Fuente de chorro vertical (GUI)")
        self.geometry("1220x880")
        self.minsize(1120, 800)

        self.Q_plot = np.linspace(0.0, 100.0, 400)  # l/s
        self._update_job = None

        # Estado de bomba activa
        self.active_D = 256.0
        self.pump_curves = {D: gen_curve_for_diameter(D) for D in RODETES_MM}

        # Fuentes
        self.font_h1 = ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        self.font_h2 = ctk.CTkFont(family="Segoe UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Segoe UI", size=14)

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

        # Columna izquierda con dos filas: controles scroll + botones fijos
        leftcol = ctk.CTkFrame(root)
        leftcol.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
        leftcol.grid_rowconfigure(0, weight=1)  # scrollable ocupa todo
        leftcol.grid_rowconfigure(1, weight=0)  # botones fijos abajo
        leftcol.grid_columnconfigure(0, weight=1)

        # Controles scrollables
        controls = ctk.CTkScrollableFrame(leftcol, width=440)
        controls.grid(row=0, column=0, sticky="nsew")

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

        ctk.CTkLabel(controls, text="Parámetros", font=self.font_h1).pack(anchor="w", padx=8, pady=(8, 6))

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
            try:
                init = float(str(var.get()).replace(",", "."))
            except Exception:
                init = vmin
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
                x = min(max(x, vmin), vmax)
                slider.set(x); self._schedule_recalc()
            var.trace_add("write", on_entry_change)

            def on_focus_out(_):
                txt = str(var.get()).replace(",", ".").strip()
                try: x = float(txt)
                except ValueError: x = slider.get()
                x = min(max(x, vmin), vmax)
                var.set(fmt.format(x)); slider.set(x)
            ent.bind("<FocusOut>", on_focus_out); ent.bind("<Return>", lambda e: on_focus_out(e))
            return ent, slider

        # Controles
        add_entry_slider(controls, "s (densidad relativa)", self.s_var, "-",     0.80, 1.40, 0.01, "{:.2f}")
        add_entry_slider(controls, "z (salida - A)",        self.z_var, "m",     0.00, 10.0, 0.10, "{:.2f}")
        add_entry_slider(controls, "D tubería",             self.Dp_var, "mm",   50.0, 400., 1.00, "{:.0f}")
        add_entry_slider(controls, "L equivalente",         self.Le_var, "m",    10.0, 300., 1.00, "{:.0f}")
        add_entry_slider(controls, "ε (rugosidad)",         self.eps_var,"cm",   0.001,0.05, 0.001,"{:.3f}")
        add_entry_slider(controls, "D boquilla",            self.Dc_var, "mm",   20.0, 120., 1.00, "{:.0f}")
        add_entry_slider(controls, "k_c (× Vc²/2g)",        self.kc_var, "-",    0.00, 2.00, 0.05, "{:.2f}")
        add_entry_slider(controls, "h mínima (b)",          self.h8_var, "m",    4.00, 12.0, 0.10, "{:.2f}")
        add_entry_slider(controls, "h objetivo (d)",        self.hobj_var,"m",   1.00, 10.0, 0.10, "{:.2f}")
        add_entry_slider(controls, "Precio energía",        self.precio_var,"€/kWh", 0.00, 0.50, 0.01, "{:.2f}")

        # Botonera fija (no scroll)
        btnrow = ctk.CTkFrame(leftcol)
        btnrow.grid(row=1, column=0, sticky="ew", pady=(8,0))
        btnrow.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(btnrow, text="Calcular a) b) c) d)", command=self.calcular).grid(row=0, column=0, sticky="ew", padx=4, pady=4)
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

        # Resultados (dos columnas)
        res = ctk.CTkFrame(right); res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1); res.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(res);  left.grid(row=0, column=0, sticky="nsew", padx=(6,3), pady=6)
        rightc= ctk.CTkFrame(res); rightc.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)

        ctk.CTkLabel(left, text="Resultados a, b, c", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.txt_a = ctk.CTkTextbox(left, height=96, font=self.font_body); self.txt_a.pack(fill="x", padx=8, pady=4)

        self.txt_b = ctk.CTkTextbox(left, height=72, font=self.font_body); self.txt_b.pack(fill="x", padx=8, pady=(4,2))
        self.pump_bar = ctk.CTkFrame(left); self.pump_bar.pack(fill="x", padx=8, pady=(2,6))
        ctk.CTkLabel(self.pump_bar, text="Bombas disponibles (rodete):", font=self.font_body).pack(anchor="w", pady=(4,2))
        self.pump_labels = {}
        row = ctk.CTkFrame(self.pump_bar); row.pack(fill="x", pady=(0,6))
        for D in RODETES_MM:
            lbl = ctk.CTkLabel(row, text=f"{int(D)} mm", corner_radius=10, padx=10, pady=6)
            lbl.pack(side="left", padx=4)
            self.pump_labels[D] = lbl

        self.txt_c = ctk.CTkTextbox(left, height=72, font=self.font_body); self.txt_c.pack(fill="x", padx=8, pady=4)
        for tb in (self.txt_a, self.txt_b, self.txt_c):
            tb.insert("end", "Pendiente de cálculo…\n"); tb.configure(state="disabled")

        ctk.CTkLabel(rightc, text="Resultado d", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.txt_d = ctk.CTkTextbox(rightc, height=160, font=self.font_body); self.txt_d.pack(fill="x", padx=8, pady=4)
        self.txt_d.insert("end", "Pulsa ‘Calcular’ o mueve deslizadores para dimensionar la válvula.\n"); self.txt_d.configure(state="disabled")

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
        notes.insert("end",
            "Notas 9.2 (resumen):\n"
            "• H_mi(Q) = z + (1 + k_c)·(V_c^2/2g) + hf_tubería(Q).\n"
            "• V_c = Q·10^-3 / (π D_c^2/4); con Q en l/s ⇒ V_c^2/2g = k_v2g(D_c)·Q^2.\n"
            "• hf_tubería = (J_ℓ·L)·Q^1.852, siendo J_ℓ el coef. unitario Hazen–Williams para Q en l/s.\n"
            "• b) h_mín fija Q_min. Si la bomba activa no da H en Q_min → seleccionar otra curva (rodete) por afinidad.\n"
            "• d) Para h = h_obj: se añade hf_válvula para que la CCI pase por (Q_obj, H_bomba(Q_obj)).\n"
        )
        notes.configure(state="disabled")

    # -------------------- Dibujo del chorro -------------------- #
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

        # Suelo y boquilla
        ax.plot([-0.5, 0.5], [0, 0], linewidth=2)
        ax.add_patch(plt.Rectangle((-0.1, 0.0), 0.2, 0.12, fill=True))

        # Chorro en azul
        ax.plot([0, 0], [0, h_jet_m], linewidth=6, alpha=0.85, solid_capstyle="round", color="tab:blue")

        # Cota del chorro
        ax.annotate("",
            xy=(0.35, h_jet_m), xytext=(0.35, 0),
            arrowprops=dict(arrowstyle="<->", lw=1.8))
        ax.text(0.38, h_jet_m/2, f"h = {h_jet_m:.2f} m",
                va="center", rotation=90,
                bbox=dict(facecolor="white", alpha=0.6, boxstyle="round,pad=0.2"))

        # Objetivo en rojo
        if h_obj_m is not None:
            ax.axhline(h_obj_m, linestyle="--", linewidth=1.2, color="red")
            ax.text(-0.55, h_obj_m, f"h_obj = {h_obj_m:.2f} m", va="center", color="red")

        # Aviso si no se alcanza
        if h_obj_m is not None and h_jet_m < h_obj_m:
            ax.text(0, ymax*0.92, "⚠ Potencia del chorro insuficiente",
                    color="red", ha="center", va="top", fontsize=11, weight="bold")

    # -------------------- Dibujo base -------------------- #
    def _draw_static(self):
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características – 9.2")

        # Bomba activa
        Qc, Hc, _ = self.pump_curves[self.active_D]
        self.ax.plot(Qc, Hc, "-", linewidth=2.6, color="tab:orange", label=f"Rodete {int(self.active_D)} mm (activo)")
        # Si no es 256, mostrar también la 256 difuminada
        if self.active_D != 256.0:
            Qb, Hb, _ = self.pump_curves[256.0]
            self.ax.plot(Qb, Hb, "--", linewidth=1.2, alpha=0.5, color="tab:orange", label="Rodete 256 mm (ref)")

        self.ax.set_xlim(0, 100)
        yref = max(self.pump_curves[self.active_D][1].max(), self.pump_curves[256.0][1].max())
        self.ax.set_ylim(0, yref*1.25)
        self._update_badge()
        self.ax.legend(loc="best")

        # Chorro vacío
        self.ax_jet.cla()
        self.ax_jet.set_title("Chorro")
        self.ax_jet.set_ylabel("Altura (m)")
        self.ax_jet.set_xticks([])
        self.ax_jet.set_ylim(0, 10)
        self.ax_jet.plot([-0.5, 0.5], [0, 0], linewidth=2)
        self.ax_jet.add_patch(plt.Rectangle((-0.1, 0.0), 0.2, 0.12, fill=True))

        self.canvas.draw_idle()

    # -------------------- Animación cambio de bomba -------------------- #
    def _animate_pump_switch(self, new_D_mm: float, on_done):
        win = ctk.CTkToplevel(self)
        win.title("CAMBIANDO BOMBA…")
        win.geometry("360x120")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(win, text=f"Cambiando a rodete {int(new_D_mm)} mm…",
                     font=self.font_h2).pack(pady=(16, 8))
        pb = ctk.CTkProgressBar(win)
        pb.pack(fill="x", padx=20, pady=(0, 14))
        pb.set(0.0)

        steps, i = 40, 0  # ~0.8 s
        def tick():
            nonlocal i
            i += 1
            pb.set(i/steps)
            if i < steps:
                win.after(20, tick)
            else:
                try: win.destroy()
                except Exception: pass
                on_done()
        tick()

    # -------------------- Modelo -------------------- #
    def _parse(self):
        try:
            s    = float(self.s_var.get().replace(",", "."))
            z    = float(self.z_var.get().replace(",", "."))
            Dp_m = float(self.Dp_var.get().replace(",", "."))/1000.0
            Le   = float(self.Le_var.get().replace(",", "."))
            eps  = float(self.eps_var.get().replace(",", "."))
            Dc_m = float(self.Dc_var.get().replace(",", "."))/1000.0
            kc   = float(self.kc_var.get().replace(",", "."))
            h8   = float(self.h8_var.get().replace(",", "."))
            hobj = float(self.hobj_var.get().replace(",", "."))
            precio = float(self.precio_var.get().replace(",", "."))
            assert all(v>0 for v in [s, z, Dp_m, Le, eps, Dc_m]) and h8>0 and hobj>0 and precio>=0
            return s, z, Dp_m, Le, eps, Dc_m, kc, h8, hobj, precio
        except Exception:
            messagebox.showerror("Error", "Entrada no válida. Revisa las casillas.")
            return None

    def _J_unit_lps(self, Dp_m, eps_cm):
        C = choose_CHW_from_eps_over_D(eps_cm, Dp_m)
        kL = hazen_williams_k_per_length(Dp_m, C)
        J_lps = kL / (1000.0**1.852)  # Q en l/s
        return C, J_lps

    def _kv2g_from_Dc(self, Dc_m):
        A = np.pi*(Dc_m**2)/4.0
        kv2g = (1e-6) / (2*9.81*(A**2))
        return kv2g

    def H_inst(self, Q_lps, z, J_lps, L, kv2g, kc, Kv_add=0.0):
        return z + (1.0 + kc + Kv_add) * kv2g * (Q_lps**2) + (J_lps*L) * (Q_lps**1.852)

    def Hb_activa(self, Ql):
        Qc, Hc, _ = self.pump_curves[self.active_D]
        return interp_xy(Qc, Hc, Ql)

    def eta_activa(self, Ql):
        Qc, _, eta = self.pump_curves[self.active_D]
        return float(interp_xy(Qc, eta, Ql))

    # -------------------- Selección de bomba -------------------- #
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
        chosen = max(RODETES_MM)
        return chosen, (chosen != self.active_D), False

    def _update_pump_bar(self):
        for D, lbl in self.pump_labels.items():
            if D == self.active_D:
                lbl.configure(text=f"{int(D)} mm ✓", fg_color="#E6FFE6", text_color="black", corner_radius=12)
            else:
                lbl.configure(text=f"{int(D)} mm", fg_color="#F0F0F0", text_color="gray20", corner_radius=10)

    def _update_badge(self):
        if self.badge_artist:
            try: self.badge_artist.remove()
            except Exception: pass
        self.badge_artist = self.ax.text(
            0.98, 0.98, f"Rodete {int(self.active_D)} mm",
            transform=self.ax.transAxes, ha="right", va="top",
            bbox=dict(facecolor="white", alpha=0.85, boxstyle="round,pad=0.2")
        )

    # -------------------- Acción: calcular -------------------- #
    def calcular(self):
        parsed = self._parse()
        if not parsed: return
        s, z, Dp_m, Le, eps_cm, Dc_m, kc, h8, hobj, precio = parsed

        C_HW, J_lps = self._J_unit_lps(Dp_m, eps_cm)
        kv2g = self._kv2g_from_Dc(Dc_m)
        Jtot = J_lps * Le

        # b) caudal mínimo para altura h8
        Q_min8 = np.sqrt(h8 / kv2g)
        Hmin8  = self.H_inst(Q_min8, z, J_lps, Le, kv2g, kc, Kv_add=0.0)

        # Selección automática de bomba según requisito en Q_min
        new_D, changed, feasible = self._select_pump_for_requirement(Q_min8, Hmin8, margin=0.05)

        def render_everything():
            self.active_D = new_D
            self._update_pump_bar()

            # c) punto de funcionamiento
            def equilibrio(q):
                return self.Hb_activa(q) - self.H_inst(q, z, J_lps, Le, kv2g, kc, Kv_add=0.0)
            Qpf = bisect_root(equilibrio, 0.0, 100.0, tol=1e-8)
            if Qpf is None:
                messagebox.showwarning("Sin intersección", "No hay corte entre CCI y la curva de bomba en [0,100] l/s.")
                return
            Hpf  = self.Hb_activa(Qpf)
            etapf = self.eta_activa(Qpf)
            gamma = 9800.0 * s
            Pabs_kW = gamma * (Qpf/1000.0) * Hpf / max(etapf,1e-9) / 1000.0
            coste_eur_m3 = (Pabs_kW / (Qpf*3.6)) * precio

            # d) válvula para h_obj
            Qobj = np.sqrt(hobj / kv2g)
            H_inst_base = self.H_inst(Qobj, z, J_lps, Le, kv2g, kc, Kv_add=0.0)
            H_bomb_obj  = self.Hb_activa(Qobj)
            hf_val = H_bomb_obj - H_inst_base
            if hf_val < 0:
                Kv_add = 0.0
                estado_d = "La bomba aporta menos altura que la CCI a Q_obj; no se alcanza h_obj solo con válvula."
            else:
                Kv_add = hf_val / (kv2g * Qobj**2)
                estado_d = "Se añade pérdida en válvula para que la CCI pase por (Q_obj, H_bomba(Q_obj))."

            # Texto largo
            self.text_res.configure(state="normal"); self.text_res.delete("1.0", "end")
            self.text_res.insert("end", "[a] Curva característica (CCI):\n")
            self.text_res.insert("end", f"    Hmi(Q) = {z:.2f} + {(1+kc)*kv2g:.6e}·Q^2 + {Jtot:.6e}·Q^1.852   (Q en l/s, H en m)\n")
            self.text_res.insert("end", f"    (C_HW≈{C_HW:.0f}, J_ℓ={J_lps:.6e}/m; Dp={Dp_m*1000:.0f} mm, Le={Le:.0f} m, Dc={Dc_m*1000:.0f} mm, kc={kc:.2f})\n\n")
            self.text_res.insert("end", f"[b] h≥{h8:.1f} m → Q_min≈{Q_min8:.2f} l/s; Hmi(Q_min)≈{Hmin8:.2f} m\n")
            feas_txt = "OK" if feasible else "NO cubierta por la familia; seleccionada la mayor disponible"
            self.text_res.insert("end", f"    Selección de bomba: rodete {int(self.active_D)} mm ({feas_txt}).\n\n")
            self.text_res.insert("end", f"[c] Q≈{Qpf:.2f} l/s, H≈{Hpf:.2f} m, η≈{etapf*100:.1f} %, P_abs≈{Pabs_kW:.2f} kW, coste≈{coste_eur_m3:.4f} €/m³ (precio={precio:.2f} €/kWh)\n\n")
            self.text_res.insert("end", f"[d] h_obj={hobj:.1f} m → Q_obj≈{Qobj:.2f} l/s; H_bomba≈{H_bomb_obj:.2f} m, Hmi_base≈{H_inst_base:.2f} m\n")
            if hf_val >= 0:
                self.text_res.insert("end", f"    hf_val≈{hf_val:.2f} m  (K_equiv≈{Kv_add:.2f})\n")
            else:
                self.text_res.insert("end", f"    {estado_d}\n")
            self.text_res.configure(state="disabled")

            # Cortos
            self._set_text(self.txt_a, f"[a] Hmi(Q)={z:.2f}+{(1+kc)*kv2g:.6e}·Q²+{Jtot:.6e}·Q^1.852  (C_HW≈{C_HW:.0f}, J_ℓ={J_lps:.6e}/m)\n")
            self._set_text(self.txt_b, f"[b] Q_min≈{Q_min8:.2f} l/s; Hmi(Q_min)≈{Hmin8:.2f} m\n"
                                       f"    Bomba activa: rodete {int(self.active_D)} mm\n")
            self._set_text(self.txt_c, f"[c] Q≈{Qpf:.2f} l/s, H≈{Hpf:.2f} m, η≈{etapf*100:.1f} %, P_abs≈{Pabs_kW:.2f} kW, coste≈{coste_eur_m3:.4f} €/m³\n")
            # <-- Añadir este bloque para mostrar siempre d)
            if hf_val >= 0:
                self._set_text(
                    self.txt_d,
                    f"[d] Q_obj≈{Qobj:.2f} l/s → hf_val≈{hf_val:.2f} m  (K_equiv≈{Kv_add:.2f})\n"
                )
            else:
                self._set_text(
                    self.txt_d,
                    f"[d] {estado_d}\n"
                )

            self._update_pump_bar()

            # Gráfica Q-H
            self.ax.cla()
            self.ax.grid(True)
            self.ax.set_xlabel("Q (l/s)")
            self.ax.set_ylabel("H (m)")
            self.ax.set_title("Curvas características – 9.2")

            # CCI
            Hcci = [self.H_inst(q, z, J_lps, Le, kv2g, kc, Kv_add=0.0) for q in self.Q_plot]
            self.ax.plot(self.Q_plot, Hcci, label="CCI instalación", linewidth=2)

            # Bomba activa
            Qc, Hc, _ = self.pump_curves[self.active_D]
            self.ax.plot(Qc, Hc, "-", linewidth=2.6, color="tab:orange", label=f"Rodete {int(self.active_D)} mm (activo)")

            # Si la activa no es 256, mostrar 256 como referencia discontinua
            if self.active_D != 256.0:
                Qb, Hb, _ = self.pump_curves[256.0]
                self.ax.plot(Qb, Hb, "--", linewidth=1.2, alpha=0.5, color="tab:orange", label="Rodete 256 mm (ref)")

            # Punto de funcionamiento
            self.ax.plot([Qpf], [Hpf], "s", markersize=8, label="Punto de funcionamiento")

            # Marcadores d)
            Qobj = np.sqrt(hobj / kv2g)
            H_bomb_obj  = self.Hb_activa(Qobj)
            H_inst_base = self.H_inst(Qobj, z, J_lps, Le, kv2g, kc, Kv_add=0.0)
            self.ax.axvline(Qobj, linestyle="--", linewidth=1)
            self.ax.plot([Qobj], [H_bomb_obj], "D", markersize=7, label="Bomba @ Q_obj")
            self.ax.plot([Qobj], [H_inst_base], "^", markersize=7, label="CCI base @ Q_obj")

            self.ax.set_xlim(0, 100)
            ymax = max(self.pump_curves[self.active_D][1].max(),
                       self.pump_curves[256.0][1].max(),
                       max(Hcci), H_bomb_obj, Hpf) * 1.15
            self.ax.set_ylim(0, max(25.0, ymax))
            self._update_badge()
            self.ax.legend(loc="best")

            # Chorro dinámico
            h_pf = kv2g * (Qpf**2)
            self._draw_jet(h_pf, hobj)

            self.canvas.draw_idle()

        if changed:
            self._animate_pump_switch(new_D, render_everything)
        else:
            render_everything()

    # -------------------- Acciones varias -------------------- #
    def reiniciar_valores(self):
        # restablecer parámetros y refrescar
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
        # limpiar textos
        for tb in (self.txt_a, self.txt_b, self.txt_c):
            tb.configure(state="normal"); tb.delete("1.0", "end")
            tb.insert("end", "Pendiente de cálculo…\n"); tb.configure(state="disabled")
        self.txt_d.configure(state="normal"); self.txt_d.delete("1.0", "end")
        self.txt_d.insert("end", "Pulsa ‘Calcular’ o mueve deslizadores para dimensionar la válvula.\n")
        self.txt_d.configure(state="disabled")
        self.text_res.configure(state="normal")
        self.text_res.delete("1.0", "end")
        self.text_res.insert("end", "Pulsa ‘Calcular’ en la pestaña Interactivo.\n")
        self.text_res.configure(state="disabled")

    def guardar_grafica(self):
        try:
            path = filedialog.asksaveasfilename(
                title="Guardar gráfica",
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")],
                initialfile="curvas_9_2.png",
            )
            if not path: return
            self.fig.savefig(path, dpi=200, bbox_inches="tight")
            messagebox.showinfo("OK", f"Gráfica guardada en:\n{path}")
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))

# --------- Entrada por main() --------- #
def main():
    App().mainloop()

if __name__ == "__main__":
    main()
