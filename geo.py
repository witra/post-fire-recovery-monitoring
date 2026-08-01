import os
import logging
from datetime import datetime, timedelta

import numpy as np
import planetary_computer as pc
import pystac_client
import rasterio as rio
import rioxarray as rioxr
import utm
import xarray as xr
import geopandas as gpd
from odc.stac import stac_load
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

logger = logging.getLogger(__name__)

def get_bbox(lon, lat, half_size_m):
    easting, northing, zone_number, zone_letter = utm.from_latlon(lat,lon)
    xmin = easting - half_size_m
    xmax = easting + half_size_m
    ymin = northing - half_size_m
    ymax = northing + half_size_m
    min_lat, min_lon = utm.to_latlon(xmin, ymin, zone_number, zone_letter) 
    max_lat, max_lon = utm.to_latlon(xmax, ymax, zone_number, zone_letter)
    return [min_lon.item(), min_lat.item(), max_lon.item(), max_lat.item()]
    
def bbox_to_epsg(min_lon, min_lat, max_lon, max_lat):
    crs_list = query_utm_crs_info(
        datum_name="WGS 84",
        area_of_interest=AreaOfInterest(
            west_lon_degree=min_lon,
            south_lat_degree=min_lat,
            east_lon_degree=max_lon,
            north_lat_degree=max_lat,
        ),
    )
    return crs_list[0].code if crs_list else None

def buffer_date(date: str, buffer:int, mode='center'):
    date = datetime.strptime(date, "%d-%m-%Y")
    if mode == "left":
        start = date - timedelta(days=buffer)
        end = date
    elif mode == "right":
        start = date
        end = date + timedelta(days=buffer)
    elif mode == "center":
        left = buffer // 2
        right = buffer - left 
        start = date - timedelta(days=left)
        end = date + timedelta(days=right)
    else:
        raise ValueError("mode must be 'left', 'right', or 'center'")
    return (
        f"{start.strftime('%Y-%m-%d')}/"
        f"{end.strftime('%Y-%m-%d')}"
        )

@retry(stop=stop_after_attempt(3), 
       wait=wait_exponential(multiplier=1, min=5, max=20),
       before_sleep=before_sleep_log(logger, logging.WARNING))
def get_s2(bbox, datetime, save_dir, filename, 
           max_cloud_cover=20, max_item=10, resolution=10, bands=None):
    if not bands:
        bands = [
                "B12", "B11", "B09", "B8A", 
                "B08", "B07", "B06", "B05", 
                "B04", "B03", "B02", "B01"
                ]
    proj_epsg =  bbox_to_epsg(*bbox)

    kwargs_search_s2 = dict(
            bbox=bbox,
            datetime=datetime,
            query={"eo:cloud_cover": {"lte": max_cloud_cover}},
            max_items=max_item
            )       
    kwargs_load_s2 = dict(
        bbox=bbox,
        bands=bands,
        chunks={"x": 256, "y": 256, "time": 1},
        resolution=resolution,
        dtype="uint16",
        crs=f"epsg:{proj_epsg}",
        nodata=0)
    
    catalog="https://planetarycomputer.microsoft.com/api/stac/v1"
    catalog_pystac = pystac_client.Client.open(catalog)
    search = catalog_pystac.search(collections=["sentinel-2-l2a"], **kwargs_search_s2)
    items = search.item_collection()
    logger.info(f"number of S2 scenes found for {filename}: {len(items)}")
    if len(items)==0:
        logger.warning(f"No S2 scenes found for {filename}")
        return 0
    os.makedirs(save_dir, exist_ok=True)
    df = gpd.GeoDataFrame.from_features(items.to_dict(), crs=f"epsg:{proj_epsg}")
    df.to_csv(f'{save_dir}/{filename}.csv')
    signed_items = [pc.sign(item) for item in items]
    ds_saved = stac_load(signed_items, groupby='id', **kwargs_load_s2)
    ds_saved = ds_saved.rio.write_crs(f"epsg:{proj_epsg}", inplace=True)
    ds_saved.to_zarr(f'{save_dir}/{filename}.zarr', mode="w", consolidated=True, zarr_format=2)
    return f'{save_dir}/{filename}.zarr'

def preprocessing(ds, mask_class=[0, 1, 3, 8, 9, 10, 11]):
    mask = ds['SCL'].isin(mask_class)
    ds_cloudless = ds.where(~mask)
    ds_cloudless = ds_cloudless.drop_vars("SCL")
    ds_median = ds_cloudless.median(dim='time', skipna=True)
    ds_scaled = ds_median/10_000
    return ds_scaled

def cal_ndvi_s2(ds):
    denom = ds['B08'] + ds['B04']
    ds['NDVI'] = xr.where(denom!=0, (ds['B08'] - ds['B04'])/denom, float("nan"))
    return ds

def cal_nbr_s2(ds):
    denom = ds['B08'] + ds['B12']
    ds['NBR'] = xr.where(denom!=0, (ds['B08'] - ds['B12'])/denom, float("nan"))
    return ds

def cal_dnbr(ds_pre, ds_post):
    da = (ds_pre['NBR']- ds_post['NBR']).rename("dNBR")
    return da

def cal_rndvi(ds_pre, ds_post, ds_t):
    denom = ds_pre["NDVI"] - ds_post["NDVI"]
    da = xr.where(denom > 0,(ds_t["NDVI"]-ds_post["NDVI"])/denom, 1).rename("rNDVI")
    da = xr.where(da>1, 1, da)
    return da

def cal_mean_zone(da_xarray, da_numpy, geom):
    mask = rio.features.geometry_mask(
           [geom],
           out_shape=da_xarray.shape,
           transform=da_xarray.rio.transform(),
           invert=True)
    values = da_numpy[mask]
    mean_val = np.nanmean(values)
    return mean_val

def classify_priority(priority_score, top, bottom):
    if priority_score > top:
        return "High"
    elif priority_score >= bottom:
        return "Medium"
    else:
        return "Low"

def action(priority_score, top, bottom):
    if priority_score > top:
        return "Immediate inspection"
    elif priority_score >= bottom:
        return "Monitor"
    else:
        return "No intervention"