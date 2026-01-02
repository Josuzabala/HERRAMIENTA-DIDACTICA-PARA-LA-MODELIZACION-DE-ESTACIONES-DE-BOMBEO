# -*- coding: utf-8 -*-
"""
MENU PRINCIPAL - SELECTOR DE PROBLEMAS
Diseño Premium con CustomTkinter
"""

import customtkinter as ctk
import os
import sys
import subprocess
from PIL import Image

# Configuración Global
ctk.set_appearance_mode("light")  # O "System"
ctk.set_default_color_theme("blue")

class ProblemCard(ctk.CTkFrame):
    """Tarjeta personalizada para cada problema"""
    def __init__(self, parent, title, subtitle, image_path, command, color_accent):
        super().__init__(parent, fg_color="white", corner_radius=15, border_width=1, border_color="#E0E0E0")
        
        self.command = command
        
        # Efecto hover
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # Layout: Grid 1x3 (Imagen, Texto, Boton)
        self.grid_columnconfigure(0, weight=1)
        # Fila 0: Imagen (fija)
        # Fila 1: Título (fijo)
        # Fila 2: Subtítulo (expandible)
        # Fila 3: Botón (fijo al fondo)
        self.grid_rowconfigure(2, weight=1) 
        
        # 1. Imagen Header
        try:
            pil_img = Image.open(image_path)
            # Mantener ratio
            self.card_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(300, 180)) # Tamaño fijo imagen
            
            self.img_label = ctk.CTkLabel(self, text="", image=self.card_img, corner_radius=15)
            self.img_label.grid(row=0, column=0, padx=10, pady=(10,5), sticky="ew")
            self.img_label.bind("<Button-1>", lambda e: command())
        except Exception as e:
            print(f"Error cargando imagen {image_path}: {e}")
            self.img_label = ctk.CTkLabel(self, text="[IMG ERROR]", height=150, fg_color="#EEE")
            self.img_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        # 2. Textos
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.grid(row=1, column=0, padx=15, pady=5, sticky="nsew")
        
        # Titulo centrado y sin saltos de linea innecesarios
        # Se amplia wraplength para aprovechar el ancho de la tarjeta (aprox 400px en ventana maximizada)
        self.lbl_title = ctk.CTkLabel(self.text_frame, text=title, font=("Segoe UI", 16, "bold"), text_color="#333", wraplength=380, justify="center")
        self.lbl_title.pack(anchor="center", pady=(5, 0), fill="x")
        
        # Subtítulo en su propia fila con peso para empujar el contenido
        self.sub_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.sub_frame.grid(row=2, column=0, padx=15, pady=0, sticky="nsew")
        
        # Texto alineado a la izquierda ("justificado" standard) para mejor lectura
        # Tkinter no soporta justificado completo (full justify) nativamente, izquierda es lo más profesional.
        self.lbl_sub = ctk.CTkLabel(self.sub_frame, text=subtitle, font=("Segoe UI", 13), text_color="#666", wraplength=380, justify="left")
        self.lbl_sub.pack(anchor="center", pady=(4, 10), fill="x")

        # 3. Botón de Acción
        self.btn = ctk.CTkButton(self, text="Abrir Problema", command=command, 
                                 font=("Segoe UI", 14, "bold"), 
                                 fg_color=color_accent, hover_color=self.darken(color_accent))
        self.btn.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")

    def on_enter(self, event):
        self.configure(border_color="#B0B0B0", border_width=2)
        
    def on_leave(self, event):
        self.configure(border_color="#E0E0E0", border_width=1)

    def darken(self, hex_color, factor=0.8):
        """Oscurece un color hex"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(int(c * factor) for c in rgb)
        return f'#{new_rgb[0]:02x}{new_rgb[1]:02x}{new_rgb[2]:02x}'


class MainMenuApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Menú principal")
        self.geometry("1400x900")
        self.minsize(1100, 750)
        
        # Maximizar ventana al inicio
        self.after(0, lambda: self.state('zoomed'))
        
        # Fondo
        self.bg_frame = ctk.CTkFrame(self, fg_color="#F3F3F3")
        self.bg_frame.pack(fill="both", expand=True)

        # --- HEADER ---
        self.header = ctk.CTkFrame(self.bg_frame, fg_color="white", height=100, corner_radius=0)
        self.header.pack(fill="x", side="top")
        
        # Títulos Izquierda
        title_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        title_frame.pack(side="left", padx=40, pady=20)
        
        ctk.CTkLabel(title_frame, text="MENU PRINCIPAL", font=("Segoe UI", 32, "bold"), text_color="#222").pack(anchor="w")
        ctk.CTkLabel(title_frame, text="Trabajo Fin de Grado", font=("Segoe UI", 20), text_color="#888").pack(anchor="w")

        # Logo Derecha
        try:
            logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo_ehu.png")
            if os.path.exists(logo_path):
                pil_logo = Image.open(logo_path)
                # Ajustar tamaño logo (por ejemplo 250px ancho)
                aspect = pil_logo.height / pil_logo.width
                target_w = 250
                target_h = int(target_w * aspect)
                self.logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(target_w, target_h))
                
                logo_label = ctk.CTkLabel(self.header, text="", image=self.logo_img)
                logo_label.pack(side="right", padx=40, pady=10)
        except Exception as e:
            print("No se pudo cargar logo:", e)

        # --- CONTENEDOR CENTRAL ---
        self.content_wrapper = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        self.content_wrapper.pack(fill="both", expand=True, padx=40, pady=(30, 10))
        
        # Grid para las tarjetas (1 fila, 3 columnas IGUALES)
        self.content_wrapper.grid_columnconfigure(0, weight=1, uniform="card") # uniform makes them equal width
        self.content_wrapper.grid_columnconfigure(1, weight=1, uniform="card")
        self.content_wrapper.grid_columnconfigure(2, weight=1, uniform="card")
        self.content_wrapper.grid_rowconfigure(0, weight=1)

        # Definir tarjetas
        self.create_cards()

        # --- FOOTER ---
        self.footer = ctk.CTkFrame(self.bg_frame, fg_color="#E0E0E0", height=120, corner_radius=0)
        self.footer.pack(fill="x", side="bottom")
        
        # Información centrada
        info_text = (
            "Autor: Zabala Muxika, Josu\n"
            "Tutora: Pellejero Salaverria, Idoya\n"
            "Departamento: Ingeniería Energética\n"
            "Curso Académico: 2025/2026"
        )
        ctk.CTkLabel(self.footer, text=info_text, font=("Segoe UI", 14), text_color="#444", justify="center").pack(pady=20)
        

    def create_cards(self):
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        
        # Tarjeta 1
        self.card1 = ProblemCard(
            self.content_wrapper,
            title="Problema nº1: Bombeo entre Depósitos",
            subtitle="Análisis de una instalación con depósitos a distinta cota, bomba centrífuga y válvula de regulación. Incluye cálculo de curvas y punto de funcionamiento.",
            image_path=os.path.join(assets_dir, "p1.png"),
            command=lambda: self.launch("Problema_9_1.py"),
            color_accent="#3B8ED0"
        )
        self.card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew") # nsew expands to fill grid cell
        
        # Tarjeta 2
        self.card2 = ProblemCard(
            self.content_wrapper,
            title="Problema nº2: Fuente de Chorro",
            subtitle="Diseño hidráulico de un chorro vertical. Selección óptima de rodete, cálculo preciso de pérdidas y análisis detallado de eficiencia energética.",
            image_path=os.path.join(assets_dir, "p2.png"),
            command=lambda: self.launch("Problema_9_2.py"),
            color_accent="#FF9800"
        )
        self.card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Tarjeta 3
        self.card3 = ProblemCard(
            self.content_wrapper,
            title="Problema nº3: Cavitación (NPSH)",
            subtitle="Estudio profundo del fenómeno de cavitación. Cálculo de altura de aspiración máxima (Z_D) y verificación operacional en dos fases.",
            image_path=os.path.join(assets_dir, "p3.png"),
            command=lambda: self.launch("Problema_9_4.py"),
            color_accent="#D32F2F"
        )
        self.card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

    def launch(self, script_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(base_dir, script_name)
        if not os.path.exists(script_path):
            print(f"Error: No se encuentra {script_path}")
            return
        
        subprocess.Popen([sys.executable, script_path], cwd=base_dir)

if __name__ == "__main__":
    app = MainMenuApp()
    app.mainloop()
