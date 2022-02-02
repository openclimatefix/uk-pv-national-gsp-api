"""Get GSP boundary data from eso """
import geopandas as gpd
from nowcasting_dataset.data_sources.gsp.eso import get_gsp_shape_from_eso


def get_latitude_longitude_gsp_boundaries_from_eso() -> gpd.GeoDataFrame:
    """Get GSP boundaries"""

    # get gsp boundaries
    boundaries = get_gsp_shape_from_eso()

    # change to lat/lon - https://epsg.io/4326
    boundaries = boundaries.to_crs(4326)

    return boundaries
