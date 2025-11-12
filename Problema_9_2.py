# -*- coding: utf-8 -*-
"""
TFG – Problema 9.2 (GUI) con customtkinter + chorro con cota dinámica
a) CCI analítica
b) Caudal mínimo para h>=8 m y selección de curva de bomba (IBS: rodete 256 mm aprox.)
c) Punto de funcionamiento (Q, H), rendimiento, potencia y coste energético
d) Válvula para bajar la altura del chorro a h_obj (por defecto 5 m): hf_val y K_equiv

Interfaz:
- Sliders+Entry sincronizados a la izquierda; gráfica (curvas Q–H + chorro) y resultados en dos columnas.
- Debounce (150 ms) y “flash” en resultados que cambian.
- Panel derecho extra: dibujo del chorro con cota h y línea objetivo h_obj.
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
            return float(y0 + t*(y1 - y1 + y1 - y0))  # evita warning por inline
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

# ----------- Curva de bomba (IBS 9.2, rodete 256 mm aprox.) ----------- #
Qb_ls = np.array([40, 50, 60, 70, 80, 90], dtype=float)  # l/s
Hb_m  = np.array([22, 22, 22, 21.8, 21.0, 19.7], dtype=float)  # m
eta_p = np.array([0.72, 0.76, 0.79, 0.78, 0.76, 0.72], dtype=float) * 100.0  # %

def H_bomba(Ql):   return interp_xy(Qb_ls, Hb_m, Ql)
def eta_bomba(Ql): return interp_xy(Qb_ls, eta_p, Ql) / 100.0

# ============================ GUI ============================ #
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Problema 9.2 – Fuente de chorro vertical (GUI)")
        self.geometry("1200x850")
        self.minsize(1100, 780)

        self.Q_plot = np.linspace(0.0, 100.0, 400)  # l/s
        self._update_job = None

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

        # Lado izquierdo: controles
        controls = ctk.CTkScrollableFrame(root, width=420)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 10))

        # Variables (por defecto del enunciado)
        self.s_var     = ctk.StringVar(value="1.0")
        self.z_var     = ctk.StringVar(value="3.0")
        self.Dp_var    = ctk.StringVar(value="175")   # mm tubería
        self.Le_var    = ctk.StringVar(value="75")    # m longitud equivalente
        self.eps_var   = ctk.StringVar(value="0.015") # cm
        self.Dc_var    = ctk.StringVar(value="80")    # mm boquilla
        self.kc_var    = ctk.StringVar(value="0.8")
        self.h8_var    = ctk.StringVar(value="8.0")   # m
        self.hobj_var  = ctk.StringVar(value="8.0")   # m
        self.precio_var= ctk.StringVar(value="0.11")  # €/kWh

        ctk.CTkLabel(controls, text="Parámetros", font=self.font_h1).pack(anchor="w", padx=8, pady=(8, 6))

        # Helper: slider + entry sincronizados
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

            # slider -> entry
            def on_slide(val):
                var.set(fmt.format(val))
                self._schedule_recalc()
            slider.configure(command=on_slide)

            # entry -> slider
            def on_entry_change(*_):
                txt = str(var.get()).replace(",", ".").strip()
                try:
                    x = float(txt)
                except ValueError:
                    return
                x = min(max(x, vmin), vmax)
                slider.set(x)
                self._schedule_recalc()
            var.trace_add("write", on_entry_change)

            def on_focus_out(_):
                txt = str(var.get()).replace(",", ".").strip()
                try:
                    x = float(txt)
                except ValueError:
                    x = slider.get()
                x = min(max(x, vmin), vmax)
                var.set(fmt.format(x)); slider.set(x)
            ent.bind("<FocusOut>", on_focus_out)
            ent.bind("<Return>", lambda e: on_focus_out(e))

            return ent, slider

        # Sliders
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

        # Botones
        btns = ctk.CTkFrame(controls); btns.pack(fill="x", padx=6, pady=(4,6))
        ctk.CTkButton(btns, text="Calcular a) b) c) d)", command=self.calcular).pack(fill="x", pady=2)
        ctk.CTkButton(btns, text="Limpiar", command=self.limpiar).pack(fill="x", pady=2)

        # Exportación
        ex = ctk.CTkFrame(controls); ex.pack(fill="x", padx=6, pady=8)
        ctk.CTkButton(ex, text="Guardar gráfica", command=self.guardar_grafica).pack(fill="x", pady=2)

        # Lado derecho: gráfica + resultados
        right = ctk.CTkFrame(root)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_rowconfigure(0, weight=4)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # Gráfica: dos subplots, curvas y chorro
        g = ctk.CTkFrame(right); g.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4,2))
        self.fig = plt.Figure(figsize=(6.9, 4.8))
        gs = self.fig.add_gridspec(1, 2, width_ratios=[2.0, 1.0])
        self.ax  = self.fig.add_subplot(gs[0, 0])    # Q-H
        self.ax_jet = self.fig.add_subplot(gs[0, 1]) # chorro
        self.canvas = FigureCanvasTkAgg(self.fig, master=g)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Resultados (dos columnas)
        res = ctk.CTkFrame(right); res.grid(row=1, column=0, sticky="nsew", padx=4, pady=(2,4))
        res.grid_columnconfigure(0, weight=1); res.grid_columnconfigure(1, weight=1)
        left = ctk.CTkFrame(res);  left.grid(row=0, column=0, sticky="nsew", padx=(6,3), pady=6)
        rightc= ctk.CTkFrame(res); rightc.grid(row=0, column=1, sticky="nsew", padx=(3,6), pady=6)

        ctk.CTkLabel(left, text="Resultados a, b, c", font=self.font_h1).pack(anchor="w", padx=8, pady=(4,2))
        self.txt_a = ctk.CTkTextbox(left, height=96, font=self.font_body); self.txt_a.pack(fill="x", padx=8, pady=4)
        self.txt_b = ctk.CTkTextbox(left, height=72, font=self.font_body); self.txt_b.pack(fill="x", padx=8, pady=4)
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
            "• b) Para h≥8 m, basta con V_c^2/2g≥8 → Q≥sqrt(8/k_v2g).\n"
            "• d) Para h=h_obj: se calcula Q_obj y se añade hf_válvula para que la CCI pase por "
            "(Q_obj, H_bomba(Q_obj)).\n"
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

        # Chorro
        ax.plot([0, 0], [0, h_jet_m], linewidth=6, alpha=0.6)

        # Cota del chorro
        ax.annotate("",
            xy=(0.35, h_jet_m), xytext=(0.35, 0),
            arrowprops=dict(arrowstyle="<->", lw=1.8))
        ax.text(0.38, h_jet_m/2, f"h = {h_jet_m:.2f} m", va="center", rotation=90)

        # Objetivo
        if h_obj_m is not None:
            ax.axhline(h_obj_m, linestyle="--", linewidth=1)
            ax.text(-0.55, h_obj_m, f"h_obj = {h_obj_m:.2f} m", va="center")

        # Si la potencia del chorro no alcanza la altura objetivo
        if h_obj_m is not None and h_jet_m < h_obj_m:
            ax.text(0, ymax*0.9, "⚠ Potencia del chorro insuficiente",
                    color="red", ha="center", va="top", fontsize=11, weight="bold")

        # Si se corta el eje
        if h_jet_m >= ymax*0.999:
            ax.text(0, ymax*0.98, "cortado", ha="center", va="top")

    # -------------------- Dibujo base -------------------- #
    def _draw_static(self):
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características – 9.2")
        self.ax.plot(Qb_ls, Hb_m, "o-", linewidth=2, label="Curva de la bomba")
        self.ax.set_xlim(0, 100)
        self.ax.set_ylim(0, max(Hb_m)*1.25)
        self.ax.legend()

        # Panel chorro vacío
        self.ax_jet.cla()
        self.ax_jet.set_title("Chorro")
        self.ax_jet.set_ylabel("Altura (m)")
        self.ax_jet.set_xticks([])
        self.ax_jet.set_ylim(0, 10)
        self.ax_jet.plot([-0.5, 0.5], [0, 0], linewidth=2)
        self.ax_jet.add_patch(plt.Rectangle((-0.1, 0.0), 0.2, 0.12, fill=True))

        self.canvas.draw_idle()

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
        kv2g = (1e-6) / (2*9.81*(A**2))  # V^2/2g = kv2g * Q^2  (Q en l/s)
        return kv2g

    def H_inst(self, Q_lps, z, J_lps, L, kv2g, kc, Kv_add=0.0):
        return z + (1.0 + kc + Kv_add) * kv2g * (Q_lps**2) + (J_lps*L) * (Q_lps**1.852)

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

        # c) punto de funcionamiento
        def equilibrio(q):
            return H_bomba(q) - self.H_inst(q, z, J_lps, Le, kv2g, kc, Kv_add=0.0)
        Qpf = bisect_root(equilibrio, 0.0, 100.0, tol=1e-8)
        if Qpf is None:
            messagebox.showwarning("Sin intersección", "No hay corte entre CCI y la curva de bomba en [0,100] l/s.")
            return
        Hpf  = H_bomba(Qpf)
        etapf = eta_bomba(Qpf)
        gamma = 9800.0 * s
        Pabs_kW = gamma * (Qpf/1000.0) * Hpf / max(etapf,1e-9) / 1000.0
        coste_eur_m3 = (Pabs_kW / (Qpf*3.6)) * precio  # €/m3

        # d) válvula para h_obj
        Qobj = np.sqrt(hobj / kv2g)
        H_inst_base = self.H_inst(Qobj, z, J_lps, Le, kv2g, kc, Kv_add=0.0)
        H_bomb_obj  = H_bomba(Qobj)
        hf_val = H_bomb_obj - H_inst_base
        if hf_val < 0:
            Kv_add = 0.0
            estado_d = "La bomba aporta menos altura que la CCI a Q_obj; no se alcanza h_obj solo con válvula."
        else:
            Kv_add = hf_val / (kv2g * Qobj**2)
            estado_d = "Se añade pérdida en válvula para que la CCI pase por (Q_obj, H_bomba(Q_obj))."

        # ----- Texto largo ----- #
        self.text_res.configure(state="normal"); self.text_res.delete("1.0", "end")
        self.text_res.insert("end", "[a] Curva característica (CCI):\n")
        self.text_res.insert("end", f"    Hmi(Q) = {z:.2f} + {(1+kc)*kv2g:.6e}·Q^2 + {Jtot:.6e}·Q^1.852   (Q en l/s, H en m)\n")
        self.text_res.insert("end", f"    (C_HW≈{C_HW:.0f}, J_ℓ={J_lps:.6e}/m; Dp={Dp_m*1000:.0f} mm, Le={Le:.0f} m, Dc={Dc_m*1000:.0f} mm, kc={kc:.2f})\n\n")
        self.text_res.insert("end", f"[b] h≥{h8:.1f} m → Q_min≈{Q_min8:.2f} l/s; Hmi(Q_min)≈{Hmin8:.2f} m\n\n")
        self.text_res.insert("end", f"[c] Q≈{Qpf:.2f} l/s, H≈{Hpf:.2f} m, η≈{etapf*100:.1f} %, P_abs≈{Pabs_kW:.2f} kW, coste≈{coste_eur_m3:.4f} €/m³ (precio={precio:.2f} €/kWh)\n\n")
        self.text_res.insert("end", f"[d] h_obj={hobj:.1f} m → Q_obj≈{Qobj:.2f} l/s; H_bomba≈{H_bomb_obj:.2f} m, Hmi_base≈{H_inst_base:.2f} m\n")
        if hf_val >= 0:
            self.text_res.insert("end", f"    hf_val≈{hf_val:.2f} m  (K_equiv≈{Kv_add:.2f})\n")
        else:
            self.text_res.insert("end", f"    {estado_d}\n")
        self.text_res.configure(state="disabled")

        # ----- Resultados cortos ----- #
        self._set_text(self.txt_a, f"[a] Hmi(Q)={z:.2f}+{(1+kc)*kv2g:.6e}·Q²+{Jtot:.6e}·Q^1.852  (C_HW≈{C_HW:.0f}, J_ℓ={J_lps:.6e}/m)\n")
        self._set_text(self.txt_b, f"[b] Q_min≈{Q_min8:.2f} l/s; Hmi(Q_min)≈{Hmin8:.2f} m\n")
        self._set_text(self.txt_c, f"[c] Q≈{Qpf:.2f} l/s, H≈{Hpf:.2f} m, η≈{etapf*100:.1f} %, P_abs≈{Pabs_kW:.2f} kW, coste≈{coste_eur_m3:.4f} €/m³\n")
        if hf_val >= 0:
            self._set_text(self.txt_d, f"[d] Q_obj≈{Qobj:.2f} l/s → hf_val≈{hf_val:.2f} m  (K_equiv≈{Kv_add:.2f})\n")
        else:
            self._set_text(self.txt_d, f"[d] {estado_d}\n")

        # ----- Gráfica Q-H ----- #
        self.ax.cla()
        self.ax.grid(True)
        self.ax.set_xlabel("Q (l/s)")
        self.ax.set_ylabel("H (m)")
        self.ax.set_title("Curvas características – 9.2")

        Hcci = [self.H_inst(q, z, J_lps, Le, kv2g, kc, Kv_add=0.0) for q in self.Q_plot]
        self.ax.plot(self.Q_plot, Hcci, label="CCI instalación", linewidth=2)
        self.ax.plot(Qb_ls, Hb_m, "o-", label="Curva de la bomba", linewidth=2)
        self.ax.plot([Qpf], [Hpf], "s", markersize=8, label="Punto de funcionamiento")

        # Marcadores objetivo d)
        self.ax.axvline(Qobj, linestyle="--", linewidth=1)
        self.ax.plot([Qobj], [H_bomb_obj], "D", markersize=7, label="Bomba @ Q_obj")
        self.ax.plot([Qobj], [H_inst_base], "^", markersize=7, label="CCI base @ Q_obj")

        self.ax.set_xlim(0, 100)
        ymax = max(max(Hb_m), max(Hcci), H_bomb_obj, Hpf) * 1.15
        self.ax.set_ylim(0, max(25.0, ymax))
        self.ax.legend(loc="best")

        # ----- Chorro dinámico ----- #
        h_pf = kv2g * (Qpf**2)  # altura real del chorro en el punto de funcionamiento
        self._draw_jet(h_pf, hobj)

        self.canvas.draw_idle()

    # -------------------- Acciones varias -------------------- #
    def limpiar(self):
        self._draw_static()
        for tb in (self.txt_a, self.txt_b, self.txt_c, self.txt_d):
            tb.configure(state="normal")
            tb.delete("1.0", "end")
            tb.insert("end", "Pendiente de cálculo…\n")
            tb.configure(state="disabled")
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

# --------- Entrada por main() (para selector) --------- #
def main():
    App().mainloop()

if __name__ == "__main__":
    main()
