from __future__ import annotations

import math


def osgb36_to_wgs84(easting: int | float, northing: int | float) -> tuple[float, float]:
    """Convert British National Grid coordinates to WGS84 latitude/longitude."""
    a, b, f0 = 6377563.396, 6356256.909, 0.9996012717
    lat0, lon0 = math.radians(49), math.radians(-2)
    n0, e0 = -100000.0, 400000.0
    e2 = 1 - (b * b) / (a * a)
    n = (a - b) / (a + b)

    lat = lat0
    meridional = 0.0
    while northing - n0 - meridional >= 0.00001:
        lat = (northing - n0 - meridional) / (a * f0) + lat
        ma = (1 + n + 5 / 4 * n**2 + 5 / 4 * n**3) * (lat - lat0)
        mb = (3 * n + 3 * n**2 + 21 / 8 * n**3) * math.sin(lat - lat0) * math.cos(lat + lat0)
        mc = (15 / 8 * n**2 + 15 / 8 * n**3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
        md = 35 / 24 * n**3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0))
        meridional = b * f0 * (ma - mb + mc - md)

    sin_lat, cos_lat, tan_lat = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * f0 / math.sqrt(1 - e2 * sin_lat**2)
    rho = a * f0 * (1 - e2) / (1 - e2 * sin_lat**2) ** 1.5
    eta2 = nu / rho - 1
    vii = tan_lat / (2 * rho * nu)
    viii = tan_lat / (24 * rho * nu**3) * (5 + 3 * tan_lat**2 + eta2 - 9 * tan_lat**2 * eta2)
    ix = tan_lat / (720 * rho * nu**5) * (61 + 90 * tan_lat**2 + 45 * tan_lat**4)
    x = 1 / (cos_lat * nu)
    xi = 1 / (cos_lat * 6 * nu**3) * (nu / rho + 2 * tan_lat**2)
    xii = 1 / (cos_lat * 120 * nu**5) * (5 + 28 * tan_lat**2 + 24 * tan_lat**4)
    xiia = 1 / (cos_lat * 5040 * nu**7) * (61 + 662 * tan_lat**2 + 1320 * tan_lat**4 + 720 * tan_lat**6)
    de = float(easting) - e0
    lat = lat - vii * de**2 + viii * de**4 - ix * de**6
    lon = lon0 + x * de - xi * de**3 + xii * de**5 - xiia * de**7

    height = 0.0
    nu_airy = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    x1 = (nu_airy + height) * math.cos(lat) * math.cos(lon)
    y1 = (nu_airy + height) * math.cos(lat) * math.sin(lon)
    z1 = ((1 - e2) * nu_airy + height) * math.sin(lat)

    tx, ty, tz = 446.448, -125.157, 542.060
    scale = 1 + 20.4894e-6
    rx, ry, rz = (math.radians(value / 3600) for value in (0.1502, 0.2470, 0.8421))
    x2 = tx + scale * x1 - rz * y1 + ry * z1
    y2 = ty + rz * x1 + scale * y1 - rx * z1
    z2 = tz - ry * x1 + rx * y1 + scale * z1

    a2, b2 = 6378137.0, 6356752.3141
    e22 = 1 - (b2 * b2) / (a2 * a2)
    p = math.sqrt(x2 * x2 + y2 * y2)
    lat2 = math.atan2(z2, p * (1 - e22))
    while True:
        nu2 = a2 / math.sqrt(1 - e22 * math.sin(lat2) ** 2)
        next_lat = math.atan2(z2 + e22 * nu2 * math.sin(lat2), p)
        if abs(next_lat - lat2) < 1e-12:
            lat2 = next_lat
            break
        lat2 = next_lat
    lon2 = math.atan2(y2, x2)
    return round(math.degrees(lat2), 6), round(math.degrees(lon2), 6)
