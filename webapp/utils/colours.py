from webapp.config import (
    ALL_MODES,
    ISOCHRONE_OPACITY,
    ISOCHRONE_TIERS,
    PERSONAL_MODES,
    PTV_MODES,
    PTV_OPACITY,
)

# Give all modes of transport, either personal or public transport, a unique hue in the HSV color space.
# This allows us to easily distinguish between them on the map.
float_hue_offset = 0.1
HUE_FOR_MODE = {
    mode: (i / len(ALL_MODES) + float_hue_offset) % 1.0 for i, mode in enumerate(ALL_MODES)
}


def hsv_to_rgb(h: float, s: float, v: float, a: float) -> tuple[float, float, float, float]:
    if s:
        if h == 1.0:
            h = 0.0
        i = int(h * 6.0)
        f = h * 6.0 - i

        w = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            return (v, t, w, a)
        if i == 1:
            return (q, v, w, a)
        if i == 2:
            return (w, v, t, a)
        if i == 3:
            return (w, q, v, a)
        if i == 4:
            return (t, w, v, a)
        if i == 5:
            return (v, w, q, a)
    else:
        return (v, v, v, a)

    return (0.0, 0.0, 0.0, a)


def rgba_float_to_255(rgba: tuple[float, float, float, float]) -> list[int]:
    """Convert a tuple of floats in range [0.0, 1.0] to a list of ints in range [0, 255]."""
    return [int(255 * c) for c in rgba[:3]] + [int(255 * rgba[3])]


def isochrone_colours():
    isochrone_colors = {}
    [f"{mode}-{tier}" for mode in PERSONAL_MODES for tier in ISOCHRONE_TIERS]
    for m, mode in enumerate(PERSONAL_MODES):
        float_hue = HUE_FOR_MODE[mode]
        for t, tier in enumerate(ISOCHRONE_TIERS):
            float_saturation = 0.5 + (0.1 * t)  # Saturation increases with tier
            isochrone_colors[f"{mode}-{tier}"] = rgba_float_to_255(
                hsv_to_rgb(float_hue, float_saturation, 0.8, ISOCHRONE_OPACITY)
            )
    return isochrone_colors


def ptv_colour_mapping():
    return {
        m: rgba_float_to_255(hsv_to_rgb(HUE_FOR_MODE[m], 0.8, 0.8, PTV_OPACITY)) for m in PTV_MODES
    }
