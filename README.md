# Post-Fire Ecosystem Recovery Prioritization Using Multi-Temporal Sentinel-2 Satellite Imagery

## Overview

This project demonstrates an end-to-end Earth Observation (EO) workflow to assess post-fire conditions and support restoration prioritization using Sentinel-2 satellite imagery.

The notebook combines:

- **dNBR (Differenced Normalized Burn Ratio)** to quantify burn severity and identify areas affected by fire.
- **NDVI recovery rate** to monitor vegetation regeneration after the fire event.

The combination of these two indicators provides complementary information:
- dNBR describes the **initial impact and severity of the wildfire**.
- NDVI recovery describes the **ecosystem response after the disturbance**.

The final output transforms pixel-level satellite observations into a **polygon-level decision-support product**, classifying burned areas into:

- **Immediate inspection**: high severity and limited vegetation recovery.
- **Monitor**: partial recovery requiring continued observation.
- **No intervention**: areas showing sufficient natural recovery.

---

## Project Workflow

The notebook implements the following pipeline:

1. **Satellite data acquisition**
   - Sentinel-2 Level-2A surface reflectance imagery.
   - Multiple acquisitions before and after the wildfire event.
   - Cloud masking and temporal compositing applied to improve data quality.

2. **Spectral index calculation**
   - Normalized Burn Ratio (NBR)
   - Differenced Normalized Burn Ratio (dNBR)
   - Normalized Difference Vegetation Index (NDVI)

3. **Post-fire recovery assessment**

    Vegetation recovery is calculated as:

    \[
    Recovery_t =
    \frac{NDVI_t - NDVI_{post}}
    {NDVI_{pre} - NDVI_{post}}
    \]

    where:

    - \(NDVI_{pre}\): vegetation condition before the wildfire
    - \(NDVI_{post}\): immediate post-fire vegetation condition
    - \(NDVI_t\): vegetation condition during monitoring periods

    A value close to:
    - **0** indicates limited recovery,
    - **1** indicates vegetation conditions approaching the pre-fire baseline.

4. **Decision intelligence layer**

   Pixel-level metrics are aggregated to burned-area polygons.

   Each polygon receives:
   - mean burn severity,
   - mean vegetation recovery,
   - restoration priority class.
   - recommended action or decision

---

##  Miscleaneous

To make the notebook fully reproducible and avoid repeated satellite data requests, the processed Sentinel-2 imagery used in this analysis is provided separately. Please put the pre-downloaded S2 under the `./data/temp`. In addition to that, the deliveravle products is also provided in the following links and please put it under `./data/deliverables`.

Pre-downloaded Sentinel-2 data: 
Deliveravle products: 

---