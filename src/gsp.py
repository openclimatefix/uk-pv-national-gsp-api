"""Get GSP boundary data from eso """
import geopandas as gpd
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_metadata_from_eso


def get_gsp_boundaries_from_eso_wgs84() -> gpd.GeoDataFrame:
    """Get GSP boundaries in lat/lon format (EPSG:4326)"""

    # get gsp boundaries
    boundaries = get_gsp_metadata_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    return boundaries
