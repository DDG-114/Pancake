"""Matplotlib drawing primitives for grouped radial comparisons."""

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Mapping
from typing import Optional
import math

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Polygon, Rectangle
import numpy as np


PALETTE = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
           "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")
PALETTES = {
    "reference": ("#E64B35", "#4DBBD5", "#00A087", "#3C5488"),
    "reference_right": ("#7E2F8E", "#238EBA", "#00A087", "#D99A00"),
}


@dataclass(frozen=True)
class Style:
    """Geometry uses a fixed 1,000-unit drawing canvas; widths/fonts are points."""

    font_family: Optional[str] = None
    cjk_font: str = "Microsoft YaHei"
    font_weight: str = "normal"
    group_weight: str = "medium"
    label_size: float = 10
    bar_width: float = 4.6
    group_label_size: float = 14
    legend_size: float = 11
    root_radius: float = 65.5
    leaf_radius: float = 105
    max_bar_length: float = 230
    label_pad: float = 13
    star_pad: float = 14
    branch_alpha: float = 0.6
    start_angle: float = 90
    group_label_angle: float = 0.355
    star_color: str = "#F2CA69"


def _xy(radius, angle):
    angle = math.radians(angle)
    return np.array([radius * math.cos(angle), radius * math.sin(angle)])


def _font(text, style):
    has_cjk = any("\u3400" <= char <= "\u9fff" or "\u3040" <= char <= "\u30ff"
                  or "\uac00" <= char <= "\ud7af" for char in text)
    candidates = ([style.cjk_font, "Noto Sans CJK SC", "SimHei", "SimSun"] if has_cjk
                  else [style.font_family] if style.font_family is not None
                  else list(mpl.rcParams["font.family"]))
    for name in candidates:
        try:
            font_manager.findfont(font_manager.FontProperties(family=[name]), fallback_to_default=False)
            return name
        except ValueError:
            pass
    return "DejaVu Sans"


def _prepare(data, model_order=None, highlight=None):
    if not isinstance(data, Mapping) or len(data) < 2:
        raise ValueError("data must map at least two groups to model/value mappings")
    result, models = {}, []
    for group, entries in data.items():
        if not isinstance(group, str) or not group.strip():
            raise ValueError("group names must be nonempty strings")
        if not isinstance(entries, Mapping) or not entries:
            raise ValueError(f"group {group!r} must contain model/value pairs")
        result[group] = {}
        for model, value in entries.items():
            if not isinstance(model, str) or not model.strip():
                raise ValueError("model names must be nonempty strings")
            if model not in models:
                models.append(model)
            if value is not None:
                try:
                    numeric = float(value)
                except (TypeError, ValueError) as error:
                    raise ValueError(f"invalid value for {group}/{model}: {value!r}") from error
                if isinstance(value, bool) or not math.isfinite(numeric) or numeric < 0:
                    raise ValueError(f"value for {group}/{model} must be finite and nonnegative")
                value = numeric
            result[group][model] = value
    if not any(v is not None for row in result.values() for v in row.values()):
        raise ValueError("data contains no numeric values")
    if model_order is not None:
        if isinstance(model_order, str):
            raise ValueError("model_order must be a sequence of all model names")
        order = list(model_order)
        if len(order) != len(set(order)) or set(order) != set(models):
            raise ValueError("model_order must contain every model exactly once")
        models = order
    if highlight is not None and highlight not in models:
        raise ValueError(f"highlight model {highlight!r} is absent from data")
    return result, models


def _validate_style(style):
    for name in ("label_size", "bar_width", "group_label_size", "legend_size",
                 "root_radius", "leaf_radius", "max_bar_length"):
        value = getattr(style, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"Style.{name} must be positive and finite")
    if style.root_radius >= style.leaf_radius:
        raise ValueError("root_radius must be smaller than leaf_radius")
    if not 0 <= style.branch_alpha <= 1:
        raise ValueError("branch_alpha must be between zero and one")


def plot(data, *, highlight=None, lower_is_better=True, value_format=".3f",
         scale=None, colors="reference", model_order=None, background=None, title=None,
         style=None, ax=None, legend=True, highlight_label=None, best_label="Best"):
    """Draw one disk and return ``(figure, axes)``.

    ``data`` is ``{group: {model: nonnegative_value_or_None}}``. Insertion order
    determines clockwise group/model order. Missing models retain their slots.
    A single linear scale is used across the disk. Stars identify all exact ties
    for the best observed value within each group; the outline is independent.
    ``scale`` is drawing units per data unit, not per-group normalization.
    ``colors`` accepts a named palette (reference, reference_right, matplotlib),
    a group/color mapping, or a color sequence. None follows Matplotlib's cycle.
    """
    data, models = _prepare(data, model_order, highlight)
    style = Style() if style is None else style
    _validate_style(style)
    background = mpl.rcParams["figure.facecolor"] if background is None else background
    if scale is None:
        maximum = max(v for row in data.values() for v in row.values() if v is not None)
        scale = style.max_bar_length / maximum if maximum > 0 else 1.0
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be positive and finite")
    try:
        format(0.0, value_format)
    except (ValueError, TypeError) as error:
        raise ValueError("value_format must be a valid Python numeric format, e.g. '.3f'") from error
    groups = list(data)
    if colors is None or (isinstance(colors, str) and colors == "matplotlib"):
        cycle = mpl.rcParams["axes.prop_cycle"].by_key().get("color", PALETTE)
        palette = [cycle[i % len(cycle)] for i in range(len(groups))]
    elif isinstance(colors, str):
        if colors not in PALETTES:
            raise ValueError(f"unknown palette {colors!r}; choose reference, reference_right, or matplotlib")
        cycle = PALETTES[colors]
        palette = [cycle[i % len(cycle)] for i in range(len(groups))]
    elif isinstance(colors, Mapping):
        if any(group not in colors for group in groups):
            raise ValueError("colors must provide a color for each group")
        palette = [colors[group] for group in groups]
    else:
        palette = list(colors)
        if len(palette) != len(groups):
            raise ValueError("colors must contain one color per group")
    for color in palette:
        mpl.colors.to_rgba(color)
    if ax is None:
        fig, ax = plt.subplots(figsize=(6.15, 6.2), facecolor=background)
        fig.subplots_adjust(left=.07, right=.93, bottom=.04, top=.96)
    else:
        fig = ax.figure
    ax.set_facecolor(background)
    ax.set_aspect("equal")
    ax.set_xlim(-470, 510)
    ax.set_ylim(-490, 510)
    ax.axis("off")
    if title:
        ax.set_title(str(title), fontfamily=_font(str(title), style),
                     fontsize=style.group_label_size, fontweight=style.group_weight, pad=26)
    best_entries, model_texts, group_texts, legend_artists = [], [], [], []
    sector = 360 / len(groups)
    for index, (group, color) in enumerate(zip(groups, palette)):
        root = _xy(style.root_radius, style.start_angle - (index + .5) * sector)
        ax.plot([0, root[0]], [0, root[1]], color=color, lw=1.8,
                alpha=style.branch_alpha, zorder=0, solid_capstyle="round")
        available = [value for value in data[group].values() if value is not None]
        best = (min(available) if lower_is_better else max(available)) if available else None
        for position, model in enumerate(models):
            theta = style.start_angle - (index + (position + .5) / len(models)) * sector
            unit = _xy(1, theta)
            leaf = style.leaf_radius * unit
            value = data[group].get(model)
            radius = style.leaf_radius + (scale * value if value is not None else 0)
            tip = radius * unit
            if value is not None:
                path = MPath([root, root * 1.06, leaf * .87, leaf],
                             [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4])
                ax.add_patch(PathPatch(path, fill=False, edgecolor=color, lw=1.6,
                                      alpha=style.branch_alpha, zorder=1, capstyle="round"))
                bar, = ax.plot([leaf[0], tip[0]], [leaf[1], tip[1]], color=color,
                               lw=style.bar_width, zorder=2, solid_capstyle="butt")
                bar.set_gid(f"bar:{group}:{model}")
                ax.plot([leaf[0]], [leaf[1]], marker="o", markersize=style.bar_width,
                        markeredgewidth=0, color=color, zorder=2)
                if model == highlight:
                    # Convert point width to data units for a snug outline at any figure size.
                    fig.canvas.draw()
                    pixels_per_unit = np.linalg.norm(ax.transData.transform(unit) - ax.transData.transform([0, 0]))
                    half_width = (style.bar_width * fig.dpi / 72 / 2 + .6) / pixels_per_unit
                    normal = _xy(half_width, theta + 90)
                    outline = Polygon([leaf + normal, tip + normal, tip - normal, leaf - normal],
                                      fill=False, edgecolor=mpl.rcParams["text.color"], lw=.85, zorder=3)
                    outline.set_gid(f"highlight:{group}:{model}")
                    ax.add_patch(outline)
            numeric_label = format(value, value_format) if value is not None else "—"
            right = unit[0] >= -1e-12
            label = f"{model} {numeric_label}" if right else f"{numeric_label} {model}"
            text = ax.text(*((radius + style.label_pad) * unit), label,
                           rotation=theta if right else theta + 180, rotation_mode="anchor",
                           ha="left" if right else "right", va="center",
                           fontsize=style.label_size, color=color, fontweight=style.font_weight,
                           fontfamily=_font(label, style), clip_on=False, zorder=5)
            text.set_gid(f"label:{group}:{model}")
            model_texts.append(text)
            if value is not None and value == best:
                best_entries.append((group, model, unit, text))
        group_angle = style.start_angle - (index + 1 - style.group_label_angle) * sector
        text = ax.text(*_xy(437, group_angle), group, fontsize=style.group_label_size,
                       fontfamily=_font(group, style), color=mpl.rcParams["text.color"], fontweight=style.group_weight,
                       ha="center", va="center", clip_on=False)
        group_texts.append((text, group_angle))
    if legend:
        y = 482
        if highlight is not None:
            outline = Rectangle((-410, 467), 44, 31, facecolor="none", edgecolor=mpl.rcParams["text.color"], lw=1.1,
                                clip_on=False)
            ax.add_patch(outline)
            legend_artists.append(outline)
            label = highlight_label if highlight_label is not None else highlight
            text = ax.text(-360, y, label, fontfamily=_font(label, style), fontsize=style.legend_size,
                           color=mpl.rcParams["text.color"], fontweight=style.font_weight,
                           ha="left", va="center", clip_on=False)
            legend_artists.append(text)
            y -= 38
        star, = ax.plot([-388], [y], marker="*", markersize=math.sqrt(135),
                        color=style.star_color, markeredgewidth=0, linestyle="none", clip_on=False)
        text = ax.text(-360, y, best_label, fontfamily=_font(best_label, style), fontsize=style.legend_size,
                       color=mpl.rcParams["text.color"], fontweight=style.font_weight,
                       ha="left", va="center", clip_on=False)
        legend_artists.extend([star, text])
    # Keep stars beyond their labels, including long user-supplied model names.
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for group, model, unit, text in best_entries:
        bbox = text.get_window_extent(renderer)
        corners = np.array([[bbox.x0, bbox.y0], [bbox.x0, bbox.y1],
                            [bbox.x1, bbox.y0], [bbox.x1, bbox.y1]])
        far_radius = np.max(ax.transData.inverted().transform(corners) @ unit)
        star_radius = max(style.leaf_radius + style.max_bar_length + 30,
                          far_radius + style.star_pad)
        star = ax.scatter(*(star_radius * unit), s=128, marker="*", color=style.star_color,
                          edgecolors="none", zorder=7, clip_on=False)
        star.set_gid(f"best:{group}:{model}")
    # Similar-valued bars can fill the label ring. Move group names outward only
    # when their actual text boxes intersect the model labels.
    obstacles = [text.get_window_extent(renderer).expanded(1.03, 1.08) for text in model_texts]
    for text, angle in group_texts:
        radius = 437
        while any(text.get_window_extent(renderer).expanded(1.08, 1.1).overlaps(box)
                  for box in obstacles):
            radius += 12
            text.set_position(_xy(radius, angle))
        obstacles.append(text.get_window_extent(renderer))
    # Keep the reference's upper-left legend position unless a label occupies it.
    while legend_artists and any(artist.get_window_extent(renderer).expanded(1.03, 1.1).overlaps(box)
                                 for artist in legend_artists for box in obstacles):
        for artist in legend_artists:
            if isinstance(artist, Rectangle):
                artist.set_y(artist.get_y() + 15)
            elif isinstance(artist, mpl.text.Text):
                artist.set_y(artist.get_position()[1] + 15)
            else:
                artist.set_ydata(np.asarray(artist.get_ydata()) + 15)
    return fig, ax


def plot_panels(panels, *, ncols=2, share_scale=False, panel_colors=None, **kwargs):
    """Draw named disks in a grid, returning ``(figure, 2D_axes_array)``.

    ``share_scale=True`` gives all panels the same units-to-length conversion.
    Otherwise each panel automatically scales to its own maximum.
    ``panel_colors`` optionally maps panel names to palettes or custom colors.
    """
    if not isinstance(panels, Mapping) or not panels:
        raise ValueError("panels must be a nonempty title/data mapping")
    if not isinstance(ncols, int) or ncols < 1:
        raise ValueError("ncols must be a positive integer")
    if "ax" in kwargs:
        raise ValueError("plot_panels creates its own axes")
    if panel_colors is not None:
        if not isinstance(panel_colors, Mapping) or any(name not in panels for name in panel_colors):
            raise ValueError("panel_colors must map existing panel names to palettes or colors")
    ncols = min(ncols, len(panels))
    nrows = math.ceil(len(panels) / ncols)
    if share_scale and kwargs.get("scale") is None:
        style = kwargs.get("style") or Style()
        maximum = max(v for data in panels.values() for row in _prepare(data)[0].values()
                      for v in row.values() if v is not None)
        kwargs["scale"] = style.max_bar_length / maximum if maximum > 0 else 1
    fig, axes = plt.subplots(nrows, ncols, squeeze=False,
                             figsize=(6.15 * ncols, 6.2 * nrows),
                             facecolor=kwargs.get("background") or mpl.rcParams["figure.facecolor"])
    fig.subplots_adjust(left=.04, right=.96, bottom=.04, top=.91, wspace=.12, hspace=.3)
    for ax, (name, data) in zip(axes.flat, panels.items()):
        options = dict(kwargs)
        if panel_colors is not None and name in panel_colors:
            options["colors"] = panel_colors[name]
        options.setdefault("title", str(name))
        plot(data, ax=ax, **options)
    for ax in list(axes.flat)[len(panels):]:
        ax.set_visible(False)
    return fig, axes


def save(fig, path, *, formats=("png", "pdf", "svg"), dpi=300):
    """Export a figure prefix (or one suffixed filename), returning saved paths."""
    path = Path(path)
    if path.suffix.lower() in (".png", ".pdf", ".svg"):
        formats = (path.suffix[1:].lower(),)
        path = path.with_suffix("")
    if isinstance(formats, str):
        formats = (formats,)
    if not formats or any(fmt not in ("png", "pdf", "svg") for fmt in formats):
        raise ValueError("formats must contain png, pdf, or svg")
    path.parent.mkdir(parents=True, exist_ok=True)
    outputs = []
    with mpl.rc_context({"pdf.fonttype": 42, "svg.fonttype": "none"}):
        for fmt in formats:
            output = Path(str(path) + "." + fmt)
            fig.savefig(output, dpi=dpi, bbox_inches="tight", pad_inches=.06,
                        facecolor=fig.get_facecolor())
            outputs.append(output)
    return outputs
