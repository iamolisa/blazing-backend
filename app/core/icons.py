"""
Small inline SVG icon set (stroke-based, 24x24) so the site doesn't
depend on an external icon font or JS icon library. Registered as the
`icon_svg()` Jinja global in app/__init__.py.
"""

_WRAP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>'

ICONS = {
    "sun": _WRAP.format('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    "clipboard": _WRAP.format('<rect x="6" y="4" width="12" height="17" rx="2"/><path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1M9 11h6M9 15h6"/>'),
    "grid": _WRAP.format('<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
    "cpu": _WRAP.format('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 22v-4M15 22v-4M2 9h4M2 15h4M22 9h-4M22 15h-4"/>'),
    "battery": _WRAP.format('<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 10v4M6 10v4M10 10v4"/>'),
    "tool": _WRAP.format('<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L2 19l3 3 7.3-7.3a4 4 0 0 0 5.4-5.4l-2.8 2.8-2-2z"/>'),
    "chart": _WRAP.format('<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>'),
    "headset": _WRAP.format('<path d="M3 13a9 9 0 0 1 18 0"/><path d="M21 13v4a2 2 0 0 1-2 2h-1v-6h3zM3 13v4a2 2 0 0 0 2 2h1v-6H3z"/>'),
    "shield": _WRAP.format('<path d="M12 2l8 4v6c0 5-3.4 8.4-8 10-4.6-1.6-8-5-8-10V6z"/><path d="M9 12l2 2 4-4"/>'),
    "bolt": _WRAP.format('<path d="M13 2 3 14h7l-1 8 10-12h-7l1-8z"/>'),
}

_FALLBACK = ICONS["bolt"]


def icon_svg(name):
    return ICONS.get(name, _FALLBACK)
