You need to download the OS Open Zoomstack file (GeoPackage format) from https://osdatahub.os.uk/downloads/open/OpenZoomstack and place it in the zoomstack folder. 

The code is a bit fragmented (sorry about that). The code analyses each census area (the areas are called Medium Super Output Areas, or MSOAs). For each MSOAs, we fetch:

The geographic shape of the MSOA from a goverment open data APIgoverment open data API.
Calculate the built-upon area of the MSOAbuilt-upon area of the MSOA (by excluding greenspaces) from the OS Open Zoomstack mapping data.
Calculate the number of dwellings and population for the MSOA from the 2021 census data.
Calculate what percent of the built-upon area is covered with buildings.
Calculate the number and type of dwellings (detached, semi-detached, etc) and population for the MSOA from the 2021 census data.
Then, by applying Russell's formula from the article, it explores the potential to densify different areas of Brighton, and calculates the resulting number of potential homes.

