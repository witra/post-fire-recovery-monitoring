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

## Installation and prerequisites

Before running the workflow, install the required Python dependencies:

```bash
pip install -r requirements.txt
 ```
The project provides two execution modes:

Jupyter notebook workflow: requires the dependencies for data processing, satellite imagery analysis, and visualization.
Agentic AI workflow: additionally requires a local LLM runtime through Ollama.

For the Agentic AI workflow, [install Ollama](https://docs.ollama.com/quickstart) and download the implemented language model:

```bash
ollama pull qwen2.5:7b
```

The agent has been tested with qwen2.5:7b, which is used as the default local LLM for interpreting user instructions and generating tool arguments. Ensure that the Ollama service is running before executing the agent workflow:

```bash
ollama serve
 ```
---
## How to use it
There are two ways to explore this project:

1. **Run the Jupyter notebook**

   Open `post_fire_recovery_monitoring.ipynb` and execute the cells sequentially. This is the recommended approach for understanding the complete workflow, including data acquisition, spectral index computation, vegetation recovery analysis, and restoration prioritization. Each step is documented to explain the underlying methodology and intermediate outputs.

2. **Run the Agentic AI workflow**

   Execute:

   `python test_agent.py`

   The AI agent accepts natural language instructions and automatically executes the post-fire assessment workflow. Currently, the agent supports the wildfire assessment pipeline, which performs the following tasks:

   - downloads pre- and post-fire Sentinel-2 imagery,
   - computes the Normalized Burn Ratio (NBR),
   - estimates burn severity,
   - and exports the final results as GeoJSON files.

   The workflow is initiated through a natural language prompt. The following example shows the user instruction provided to the agent in `test_agent.py`

   ```python
   response = await agent.ainvoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content":
                        """
                        Assess wildfire impact at Girande, France as the following details:
                        latitude: 44.57616
                        longitude: -1.18168

                        use:
                        pre-fire date: 2022-07-10
                        post-fire date: 2022-08-01
                        buffer day: 2 weeks
                         
                        please save to a folder called "data_test". Then give your opinion on its result.

                        """
                    }
                ]
            }
        )
   ```

   Based on this instruction, the LLM interprets the request and generates the required arguments for the wildfire assessment tool. An example of the generated tool arguments is shown below:
   ```text
   INFO | __main__ | TOOL CALLS: 

      [{'name': 'assess_fire_event',
        'args': {'filename': 'fire_assessment', 
                'lat': 44.57616, 
                'lon': -1.18168, 
                'pre_date': '10-07-2022', 
                'post_date': '01-08-2022', 
                'buffer_days': 14, 
                'save_dir': 'data_test'
                }, 
        'id': 'c23c0e21-9c6f-4410-8320-9278ba473ca3', 
        'type': 'tool_call'}
        ]
   ```

   After executing the workflow, the agent returns the final assessment outputs, including the generated geospatial products. An example of the final results is shown below:
   ```markdown
   | INFO | __main__ | FINAL RESPONSE: 
   The wildfire impact assessment for the area around Girande, France has been successfully completed. Here are the key findings:

   - **Total Impacted Area**: 2286.15 hectares.
   - **Severity Distribution**:
   - Low Severity: 38.98%
   - Moderate Severity: 60.79%
   - High Severity: 0.23%

   The results are saved in the "data_test" folder, specifically at the file path `data_test/data_via_llm/fire_assessment.geojson`.

   Based on these findings, it appears that most of the affected area (60.79%) experienced moderate burn severity, while only a small portion (0.23%) was classified as high severity. This suggests that recovery efforts should focus primarily on areas with moderate damage to ensure effective and efficient resource allocation.

   Would you like me to provide any further analysis or assistance based on these results? 
   ```
----
##  Miscellaneous

To make the notebook fully reproducible and avoid repeated satellite data requests, the processed Sentinel-2 imagery used in this analysis is provided separately. Please put the pre-downloaded S2 under the `./data/temp`. In addition to that, the deliveravle products is also provided in the following links and please put it under `./data/deliverables`.

Pre-downloaded Sentinel-2 data: https://huggingface.co/datasets/wtr001/post-fire-recovery-monitoring/resolve/main/pre-downloaded-s2.zip

Deliverable products: https://huggingface.co/datasets/wtr001/post-fire-recovery-monitoring/resolve/main/deliverabels.zip

---