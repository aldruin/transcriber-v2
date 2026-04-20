"""
ui/widgets.py — Componentes de UI reutilizáveis usando customtkinter.

Contém:
- LevelMeter:      Barra de nível de áudio em tempo real com threshold visual
- ActionButton:    Botão estilizado com estado (normal/disabled/active)
- StatusLabel:     Label de status com cor dinâmica
- WaveformCanvas:  Visualizador de ondas de áudio em tempo real
"""

import tkinter as tk
import customtkinter as ctk

# ── Paleta de cores (Catppuccin Mocha adaptado) ──────────────────────────────
COLORS = {
    "bg":        "#1e1e2e",
    "panel":     "#181825",
    "surface":   "#313244",
    "fg":        "#cdd6f4",
    "subtext":   "#6c7086",
    "accent":    "#89b4fa",
    "green":     "#a6e3a1",
    "red":       "#f38ba8",
    "yellow":    "#f9e2af",
    "blue":      "#89dceb",
    "pink":      "#f5c2e7",
    "orange":    "#fab387",
}


class LevelMeter(ctk.CTkFrame):
    """
    Medidor de nível de áudio (barra horizontal colorida).
    """

    def __init__(
        self,
        parent,
        label: str,
        label_color: str,
        threshold: float,
        bar_max: float = 0.1,
        width: int = 300,
        **kwargs,
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._threshold = threshold
        self._bar_max   = bar_max
        self._width     = width

        # Label do canal
        self._lbl = ctk.CTkLabel(
            self,
            text=label,
            text_color=label_color,
            font=("Segoe UI", 12),
            width=100,
            anchor="w",
        )
        self._lbl.pack(side="left", padx=(0, 8))

        # Canvas da barra (usamos tk.Canvas pois ctk não tem um equivalente direto para desenho)
        self._canvas = tk.Canvas(
            self,
            width=width,
            height=12,
            bg=COLORS["surface"],
            highlightthickness=0,
            borderwidth=0
        )
        self._canvas.pack(side="left", padx=(0, 8))

        # Valor numérico
        self._rms_label = ctk.CTkLabel(
            self,
            text="0.0000",
            text_color=label_color,
            font=("Consolas", 12),
            width=60,
            anchor="w",
        )
        self._rms_label.pack(side="left")
        
        self._draw_static()

    def _draw_static(self):
        """Desenha elementos estáticos (threshold)."""
        self._canvas.delete("threshold")
        thresh_x = int(min(self._threshold / self._bar_max, 1.0) * self._width)
        self._canvas.create_line(
            thresh_x, 0, thresh_x, 12,
            fill=COLORS["yellow"],
            width=1,
            dash=(3, 2),
            tags="threshold",
        )

    def update_level(self, rms: float) -> None:
        """Atualiza a barra com o novo valor RMS."""
        pct   = min(rms / self._bar_max, 1.0)
        x     = int(pct * self._width)
        color = COLORS["green"] if rms >= self._threshold else COLORS["subtext"]

        self._canvas.delete("bar")
        if x > 0:
            self._canvas.create_rectangle(
                0, 0, x, 12,
                fill=color,
                outline="",
                tags="bar",
            )

        self._rms_label.configure(text=f"{rms:.4f}")

    def update_threshold(self, threshold: float):
        self._threshold = threshold
        self._draw_static()


class ActionButton(ctk.CTkButton):
    """
    Botão estilizado usando CTkButton.
    """

    def __init__(self, parent, text: str, color: str, fg: str = "#1e1e2e", **kwargs):
        # Remove height de kwargs se existir para evitar conflito no super().__init__
        h = kwargs.pop("height", 36)
        super().__init__(
            parent,
            text=text,
            fg_color=color,
            text_color=fg,
            hover_color=self._adjust_color(color, 0.8),
            font=("Segoe UI", 13, "bold"),
            height=h,
            **kwargs,
        )
        self._active_color = color

    def _adjust_color(self, hex_color, factor):
        """Escurece/clareia uma cor hex."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        new_rgb = tuple(max(0, min(255, int(c * factor))) for c in rgb)
        return '#%02x%02x%02x' % new_rgb

    def set_active(self, text: str | None = None, color: str | None = None) -> None:
        self.configure(state="normal")
        if text:
            self.configure(text=text)
        if color:
            self.configure(fg_color=color, hover_color=self._adjust_color(color, 0.8))

    def set_inactive(self, text: str | None = None) -> None:
        self.configure(state="disabled")
        if text:
            self.configure(text=text)


class StatusLabel(ctk.CTkLabel):
    """
    Label de status com ponto colorido.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            text="● Iniciando...",
            text_color=COLORS["yellow"],
            font=("Segoe UI", 13, "bold"),
            **kwargs,
        )

    def set(self, text: str, color: str = COLORS["yellow"]) -> None:
        self.configure(text=f"● {text}", text_color=color)

    def ready(self, text: str = "Pronto") -> None:
        self.set(text, COLORS["green"])

    def error(self, text: str = "Erro") -> None:
        self.set(text, COLORS["red"])

    def working(self, text: str = "Transcrevendo") -> None:
        self.set(text, COLORS["green"])


class WaveformCanvas(ctk.CTkFrame):
    """
    Visualizador de ondas de áudio em tempo real.
    (Preparação para Etapa 3)
    """

    def __init__(self, parent, width=400, height=50, **kwargs):
        super().__init__(parent, fg_color=COLORS["panel"], **kwargs)
        self._width = width
        self._height = height
        
        self._canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=COLORS["panel"],
            highlightthickness=0,
            borderwidth=0
        )
        self._canvas.pack(fill="both", expand=True, padx=2, pady=2)
        
        self._data = [0.0] * 50  # Histórico de amplitudes
        
    def push_data(self, value: float):
        """Adiciona um novo valor de amplitude (RMS)."""
        self._data.pop(0)
        self._data.append(value)
        self._render_waveform()
        
    def _render_waveform(self):
        self._canvas.delete("wave")
        w = self._width
        h = self._height
        n = len(self._data)
        dx = w / (n - 1)
        
        points = []
        for i, val in enumerate(self._data):
            # Normaliza val (0.0 a 0.1) para a altura do canvas
            # Usamos uma escala logarítmica ou multiplicador para visibilidade
            v = min(val * 10, 1.0) 
            y_offset = (h * v) / 2
            x = i * dx
            
            # Desenha barras verticais do centro
            self._canvas.create_line(
                x, h/2 - y_offset, x, h/2 + y_offset,
                fill=COLORS["accent"],
                width=3,
                tags="wave"
            )
