import geo
import os
import logging
import xarray as xr
import geopandas as gpd
from pyproj import CRS
from rasterio.features import shapes
from shapely.geometry import shape
from fastmcp import FastMCP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

mcp = FastMCP("geo")

@mcp.tool
def assess_fire_event(lat:float, 
                     lon:float, 
                     pre_date:str, 
                     post_date:str, 
                     buffer_days:int=7, 
                     half_size_m:int=2500, 
                     save_dir:str=".", 
                     filename:str="fire_assessment", 
                     ):
    """
    Assess wildfire impact using Sentinel-2 satellite imagery.

    The tool:
    - downloads Sentinel-2 imagery before and after a fire event
    - calculates NDVI, NBR and dNBR
    - classifies burn severity into low, moderate and high classes
    - creates a GeoJSON severity map
    - returns burned area statistics

    Use this tool when the user asks:
    - where wildfire damage occurred
    - burn severity assessment
    - recovery prioritization
    - wildfire impact assessment
    - burn severity mapping
    - post-fire recovery analysis.

    Do not use this tool for:
    - weather forecast
    - fire detection in real time
    - fire prediction

    Inputs:
    lat/lon:
        Fire location coordinates.
    pre_date:
        Date before fire event in "dd-mm-yyyy" format. Please adjust user prompt to the format "dd-mm-yyyy" if necessary.
    post_date:
        Date after fire event in "dd-mm-yyyy" format. Please adjust user prompt to the format "dd-mm-yyyy" if necessary.
    buffer_days (optional):
        number of days to buffer the given date. The unit is in days. Adjust the user input to day unit if necessary. Default is 7 days. 
    half_size_m (optional):
        Half size of the bounding box in meters. The bounding box will be a square with side length of 2 * half_size_m. Default is 2500 meters.
    save_dir (optional):
        Directory to save the output GeoJSON file. Default is current directory. 
    filename (optional):
        Name of the output GeoJSON file. Default is "fire_assessment".     
    Returns:
        JSON summary containing:
        - total impacted area
        - percentage by severity class
        - output GeoJSON location
    """
    try: 
        bbox = geo.get_bbox(lon, lat, half_size_m)
        pre_daterange = geo.buffer_date(pre_date, buffer_days, 'left')
        post_daterange = geo.buffer_date(post_date, buffer_days, 'right')
        bands = ["B04", "B03", "B02", "B08", "B12", "SCL"]
        max_cloud_cover=20
        resolution=10
        max_item=10

        TEMP_DIR = f"{save_dir}/data_via_llm"
        os.makedirs(TEMP_DIR, exist_ok=True)

        logger.info(f"Downloading pre and post fire event Sentinel-2 datasets to {TEMP_DIR} ...")
        path_s2_pre = geo.get_s2(bbox, pre_daterange, TEMP_DIR, 'pre_event', bands=bands, max_cloud_cover=max_cloud_cover, max_item=max_item, resolution=resolution)
        path_s2_post = geo.get_s2(bbox, post_daterange, TEMP_DIR, 'post_event', bands=bands, max_cloud_cover=max_cloud_cover, max_item=max_item, resolution=resolution)
        s2_paths = [path_s2_pre, path_s2_post]

        if path_s2_pre == 0 or path_s2_post == 0:
            return {"status": "stop",
                    "message": "one or both of the pre-event and post-event Sentinel-2 datasets are empty. Please check the input parameters and try again."}
        logger.info(f"finished downloading to {TEMP_DIR}")
        logger.info(f"calculate burn severity using pre and post fire event Sentinel-2 datasets")
        mask_class=[0, 1, 3, 8, 9, 10, 11]
        ds = xr.open_zarr(s2_paths[0])
        crs = CRS.from_wkt(ds['spatial_ref'].attrs['spatial_ref']).to_epsg()
        ds_list = [geo.preprocessing(xr.open_zarr(path), mask_class) for path in s2_paths]
        ds_list = [ds.rio.write_crs(f"epsg:{crs}", inplace=True) for ds in ds_list] # apply crs
        ds_list = [geo.cal_ndvi_s2(ds) for ds in ds_list]
        ds_list = [geo.cal_nbr_s2(ds) for ds in ds_list]
        ndbr_base = geo.cal_dnbr(ds_list[0], ds_list[1])
        
        severity_cls = { 1:'low', 2:'moderate', 3:'high'}
        severity_class = xr.zeros_like(ndbr_base, dtype="uint8")
        severity_class = xr.where((ndbr_base >= 0.10) & (ndbr_base < 0.27), 1, severity_class)
        severity_class = xr.where((ndbr_base >= 0.27) & (ndbr_base < 0.66), 2, severity_class)
        severity_class = xr.where(ndbr_base >= 0.66, 3, severity_class)
        
        geoms = [
                {'geometry': shape(geom),
                'severity': severity_cls[value]
                } for geom, value in shapes(severity_class.data, mask=severity_class.astype(bool), transform=severity_class.rio.transform())
                ]

        gdf = gpd.GeoDataFrame(geoms, crs=crs)
        gdf['area_ha'] = gdf.geometry.area/10_000 # in ha
        gdf.to_file(f"{TEMP_DIR}/{filename}.geojson", driver="GeoJSON")

        area_by_class = (gdf.groupby("severity")["area_ha"].sum().reset_index(name="total_area_ha"))
        area_dict = dict(zip(area_by_class["severity"], area_by_class["total_area_ha"]))
        total_area = area_by_class['total_area_ha'].sum()
        percentage_by_class = {k: (v/total_area)*100 for k, v in area_dict.items()}
        return {
                "status": "success",
                "total_area": f"{float(total_area)} ha",
                "severity": {
                    "low": f"{percentage_by_class.get('low', 0):.2f}%",
                    "moderate": f"{percentage_by_class.get('moderate', 0):.2f}%",
                    "high": f"{percentage_by_class.get('high', 0):.2f}%"
                },
                "output_file": f"{TEMP_DIR}/{filename}.geojson"
                }
    except Exception as e:
        logger.exception("Fire assessment failed")

        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")