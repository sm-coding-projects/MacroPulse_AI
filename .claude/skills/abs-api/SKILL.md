---
name: abs-api
description: Reference documentation for the Australian Bureau of Statistics (ABS) Indicator API. Use this skill when writing code that fetches, parses, or transforms ABS Capital Expenditure data. Contains endpoint details, SDMX-JSON response format, series ID mappings, and parsing strategies.
---

# ABS Indicator API Reference for CapEx Data

## API Overview

The ABS Indicator API provides macroeconomic data in SDMX-JSON format. MacroPulse AI uses the Private New Capital Expenditure and Expected Expenditure dataset (Catalogue No. 5625.0).

## Endpoint

```
GET https://indicator.data.abs.gov.au/dataflows
```

To get the CapEx dataflow metadata:
```
GET https://indicator.data.abs.gov.au/dataflow/ABS/CAPEX
```

To fetch actual data:
```
GET https://indicator.data.abs.gov.au/data/ABS,CAPEX/{series_key}?detail=full
```

Example fetching all CapEx data:
```
GET https://indicator.data.abs.gov.au/data/ABS,CAPEX/all
```

Or with specific dimensions:
```
GET https://indicator.data.abs.gov.au/data/ABS,CAPEX/{frequency}.{measure}.{industry}.{asset_type}.{region}
```

## SDMX-JSON Response Structure

The response is structured as follows:

```json
{
  "header": {
    "id": "...",
    "prepared": "2024-12-15T00:00:00"
  },
  "dataSets": [
    {
      "action": "Information",
      "observations": {
        "0:0:0:0:0:0": [42567.8, 0, null],
        "0:0:0:0:0:1": [41234.1, 0, null],
        ...
      }
    }
  ],
  "structure": {
    "dimensions": {
      "observation": [
        {
          "id": "TIME_PERIOD",
          "values": [
            {"id": "2024-Q3", "name": "Sep 2024"},
            {"id": "2024-Q2", "name": "Jun 2024"},
            ...
          ]
        }
      ],
      "series": [
        {
          "id": "FREQUENCY",
          "values": [{"id": "Q", "name": "Quarterly"}]
        },
        {
          "id": "MEASURE",
          "values": [
            {"id": "CAPEX_ACT", "name": "Actual"},
            {"id": "CAPEX_EXP", "name": "Expected"}
          ]
        },
        {
          "id": "INDUSTRY",
          "values": [
            {"id": "TOT", "name": "Total"},
            {"id": "MIN", "name": "Mining"},
            {"id": "MFG", "name": "Manufacturing"},
            {"id": "OTH", "name": "Other Selected Industries"}
          ]
        },
        {
          "id": "ASSET_TYPE",
          "values": [
            {"id": "TOT", "name": "Total"},
            {"id": "BS", "name": "Buildings & Structures"},
            {"id": "EPM", "name": "Equipment, Plant & Machinery"}
          ]
        },
        {
          "id": "REGION",
          "values": [{"id": "AUS", "name": "Australia"}]
        }
      ]
    }
  }
}
```

## Parsing Strategy

The observation keys (e.g., `"0:0:0:0:0:0"`) are colon-separated indices into the series dimensions, with the last index being the time period.

To parse:
1. Get dimension `values` arrays from `structure.dimensions.series` and `structure.dimensions.observation`
2. For each observation key, split by `:` to get dimension indices
3. Map each index to the corresponding dimension value
4. The first element of the observation array is the data value

### Python Parsing Example

```python
def parse_sdmx_observations(response: dict) -> list[dict]:
    """Parse SDMX-JSON observations into flat records."""
    dataset = response["dataSets"][0]
    observations = dataset.get("observations", {})
    
    # If data is series-based rather than flat observations
    if not observations and "series" in dataset:
        return parse_series_based(dataset, response["structure"])
    
    structure = response["structure"]
    series_dims = structure["dimensions"].get("series", [])
    obs_dims = structure["dimensions"].get("observation", [])
    
    records = []
    for key, values in observations.items():
        indices = key.split(":")
        record = {}
        
        # Map series dimension indices
        for i, dim in enumerate(series_dims):
            dim_idx = int(indices[i])
            if dim_idx < len(dim["values"]):
                record[dim["id"]] = dim["values"][dim_idx]["id"]
        
        # Map observation dimension indices (usually TIME_PERIOD)
        obs_start = len(series_dims)
        for i, dim in enumerate(obs_dims):
            dim_idx = int(indices[obs_start + i])
            if dim_idx < len(dim["values"]):
                record[dim["id"]] = dim["values"][dim_idx]["id"]
        
        record["value"] = values[0] if values else None
        records.append(record)
    
    return records
```

### Series-Based Response Variant

Some ABS endpoints return data in a series-based format instead of flat observations:

```json
{
  "dataSets": [{
    "series": {
      "0:0:0:0": {
        "observations": {
          "0": [42567.8],
          "1": [41234.1]
        }
      }
    }
  }]
}
```

In this case, the series key maps to series dimensions, and the observation key maps to the time period dimension.

## Rate Limiting

- No documented rate limits, but be courteous
- Implement a minimum 2-second delay between requests
- Respect HTTP 429 responses with exponential backoff (2s, 4s, 8s, max 32s)
- Set a User-Agent header: `MacroPulse-AI/1.0`

## Common Pitfalls

1. **Null values:** Some observations may be null (not yet released). Filter these out.
2. **Estimate numbers:** The ABS revises CapEx estimates multiple times. The estimate number is in the metadata — include it in analysis context.
3. **Seasonal adjustment:** Data may be original, seasonally adjusted, or trend. Filter for the type you need (usually seasonally adjusted).
4. **Response size:** Fetching `all` can return a large response. Consider filtering by specific dimensions in the URL.
5. **HTTPS required:** The API requires HTTPS. HTTP requests will be redirected.

## Fallback Strategy

If the ABS API is unavailable:
1. Return cached data with a warning
2. If no cache exists, return a clear error message
3. Never silently fail — always inform the user
