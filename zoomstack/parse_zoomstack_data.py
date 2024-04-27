import json
from rasterio.warp import transform_geom
import os
import random
import time
from typing import List, Tuple
import fiona.model
from fiona.crs import from_epsg
import geopandas as gpd
import fiona
import pyproj
import requests
from shapely.geometry import Polygon, MultiPolygon

ZOOMSTACK_FOLDER = "zoomstack"


# Provide the path to your GeoPackage file
geopackage_path = ZOOMSTACK_FOLDER + "/OS_Open_Zoomstack.gpkg"


def fetch_brighton_shape(msoa_id: str):
    api_url_start = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/MSOA_Dec_2001_Boundaries_EW_BFC_2022/FeatureServer/0/query?where=MSOA01CD%20%3D%20'"
    api_url_end = "'&outFields=*&outSR=4326&f=json"

    # api_url_start = "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/MOSA_2021_EW_BFC_V6/FeatureServer/0/query?where=MSOA21NM%20%3D%20'BRIGHTON%20AND%20HOVE%20"
    # api_url_end = "'&outFields=*&outSR=4326&f=json"
    api_url = api_url_start + msoa_id + api_url_end
    response = requests.get(api_url)
    json_data = response.json()
    features = json_data["features"]
    keys = features[0].keys()
    geometry = features[0]["geometry"]
    rings = geometry["rings"]
    return rings[0]


# the id is the numerical three digit string suffix on
# https://geoportal.statistics.gov.uk/datasets/5ea68106e08146d1be20c3e690d68b4d_0/explore?location=52.448095%2C-2.489845%2C6.64&showTable=true


# This is the full shape including green space
def fetch_brighton_shape_cached(msoa_id: str):
    brighton_file = ZOOMSTACK_FOLDER + "/brighton_{msoa}.json".format(msoa=msoa_id)
    if not os.path.exists(brighton_file):
        msoa_lat_long = fetch_brighton_shape(msoa_id)
        with open(brighton_file, "w") as file:
            json.dump(msoa_lat_long, file)

    else:
        with open(brighton_file, "r") as file:
            msoa_lat_long = json.load(file)

    # Define the BNG and WGS84 coordinate systems
    # bng = pyproj.Proj(init="epsg:27700")  # British National Grid
    # wgs84 = pyproj.Proj(init="epsg:4326")  # WGS84 (latitude and longitude)

    # Convert the coordinates from WGS84 to BNG
    # cache msoa_bng to a file as it takes time to convert
    bng_path = ZOOMSTACK_FOLDER + "/msoa_{msoa}_bng.json".format(msoa=msoa_id)
    transformer = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:27700")
    if not os.path.exists(bng_path):
        msoa_bng = [transformer.transform(lon, lat) for lon, lat in msoa_lat_long]
        with open(bng_path, "w") as file:
            json.dump(msoa_bng, file)
    else:
        with open(bng_path, "r") as file:
            msoa_bng = json.load(file)

    return msoa_bng


def get_msoa_bounding_box(msoa_id: str):
    msoa_bng = fetch_brighton_shape_cached(msoa_id)

    # Calculate the bounding box of the MSOA geometry
    bbox = Polygon(msoa_bng).bounds  # (minx, miny, maxx, maxy)
    return bbox


def buildings_for_msoa(
    msoa_coordinates: List[Tuple], msoa_bounding_box
) -> List[fiona.model.Feature]:
    with fiona.open(
        ZOOMSTACK_FOLDER + "/OS_Open_Zoomstack.gpkg", layer="local_buildings"
    ) as layer:
        count = 0

        buildings: List[fiona.model.Feature] = []
        msoa_shape = Polygon(msoa_coordinates)

        # Process only the feature records intersecting a box.
        for feature in layer.filter(bbox=msoa_bounding_box):
            # Get the coordinates of the feature
            feature_coords = feature["geometry"].coordinates[0]
            if Polygon(feature_coords).within(msoa_shape):
                count += 1
                buildings.append(feature)

    return buildings


# def greenspace_area_for_msoa(msoa_coordinates: List[Tuple], msoa_bounding_box) -> float:
#     msoa_shape = Polygon(msoa_coordinates)
#     total_area = 0
#     for layer_name in ["national_parks", "greenspace", "woodland"]:
#         with fiona.open(
#             "data/zoomstack/OS_Open_Zoomstack.gpkg", layer=layer_name
#         ) as layer:
#             for feature in layer.filter(bbox=msoa_bounding_box):
#                 feature_coords = feature["geometry"].coordinates[0]
#                 intersection = msoa_shape.intersection(Polygon(feature_coords))
#                 if intersection.is_empty:
#                     continue
#                 if intersection.area > 0:
#                     total_area += intersection.area

#     return total_area


# def greenspace_for_msoa(
#     msoa_coordinates: List[Tuple], msoa_bounding_box
# ) -> List[fiona.model.Feature]:

#     for layer_name in ["national_parks"]:

#         with fiona.open(
#             "data/zoomstack/OS_Open_Zoomstack.gpkg", layer=layer_name
#         ) as layer:
#             print("checking greenspace now")

#             greenspace: List[fiona.model.Feature] = []
#             # Process only the feature records intersecting a box.
#             for feature in layer.filter(bbox=msoa_bounding_box):
#                 # Get the coordinates of the feature
#                 feature_coords = feature["geometry"].coordinates[0]
#                 msoa_shape = Polygon(msoa_coordinates)
#                 intersection = msoa_shape.intersection(Polygon(feature_coords))
#                 if intersection.is_empty:
#                     continue
#                 if intersection.area > 0:
#                     # Replace the geometry of the feature with the geometry of the intersection
#                     new_feature = feature
#                     new_feature["geometry"] = intersection.__geo_interface__
#                     greenspace.append(new_feature)

#     return greenspace


# Define the input coordinate reference system (CRS)
INPUT_CRS = from_epsg(27700)
# Define the output CRS (WGS84)
OUTPUT_CRS = from_epsg(4326)


def write_geojson_for_buildings(msoa_code: str, buildings: List[fiona.model.Feature]):
    # # Define the input coordinate reference system (CRS)
    # input_crs = from_epsg(27700)
    # # Define the output CRS (WGS84)
    # output_crs = from_epsg(4326)
    # Get the schema from the appropriate layer
    with fiona.open(geopackage_path, layer="local_buildings") as src:
        # Get the schema from the input data source
        schema = src.schema

    # Create a GeoJSON file
    with fiona.open(
        "buildings_{msoa}.geojson".format(msoa=msoa_code),
        "w",
        driver="GeoJSON",
        crs=OUTPUT_CRS.to_wkt(),
        # schema={"geometry": "Polygon", "properties": {}},
        schema=schema,
    ) as output:
        for feature in buildings:
            # Reproject the geometry to WGS84
            reprojected_geom = transform_geom(
                INPUT_CRS, OUTPUT_CRS, feature["geometry"]
            )

            # Create a new feature with the reprojected geometry
            reprojected_feature = {
                "type": "Feature",
                "geometry": reprojected_geom,
                "properties": feature["properties"],
            }

            output.write(reprojected_feature)


# def write_geojson_for_greenspaces(
#     msoa_code: str, greenspaces: List[fiona.model.Feature]
# ):
#     for layer_name in ["national_parks"]:
#         with fiona.open(geopackage_path, layer=layer_name) as src:
#             schema = src.schema

#         # Create a GeoJSON file
#         with fiona.open(
#             "{layer_name}_{msoa}.geojson".format(layer_name=layer_name, msoa=msoa_code),
#             "w",
#             driver="GeoJSON",
#             crs=OUTPUT_CRS.to_wkt(),
#             schema=schema,
#         ) as output:
#             for feature in greenspaces:
#                 # Reproject the geometry to WGS84
#                 reprojected_geom = transform_geom(
#                     INPUT_CRS, OUTPUT_CRS, feature["geometry"]
#                 )

#                 # Create a new feature with the reprojected geometry
#                 reprojected_feature = {
#                     "type": "Feature",
#                     "geometry": reprojected_geom,
#                     "properties": feature["properties"],
#                 }

#                 output.write(reprojected_feature)


# TODO: Consider only including buildings in the usable area.
# Some buildings will be in greenspace so shouldn't count towards the density.
def total_area_for_buildings(buildings: List[fiona.model.Feature]):
    total_area_for_buildings = 0
    for building in buildings:
        # Calculate the area of the building
        area = Polygon(building["geometry"]["coordinates"][0]).area
        total_area_for_buildings += area

    return total_area_for_buildings


def usable_shape_for_msoa(msoa_id, msoa_bounding_box) -> Polygon:
    shape = fetch_brighton_shape_cached(msoa_id)
    polygon = Polygon(shape)

    # Remove any of the greenspaces from the MSOA shape
    for layer_name in ["national_parks", "greenspace", "woodland"]:
        with fiona.open(
            ZOOMSTACK_FOLDER + "/OS_Open_Zoomstack.gpkg", layer=layer_name
        ) as layer:
            for feature in layer.filter(bbox=msoa_bounding_box):
                feature_coords = feature["geometry"].coordinates[0]
                polygon = polygon.difference(Polygon(feature_coords))

    return polygon


import json
from shapely.geometry import mapping

from shapely.geometry import GeometryCollection, MultiPolygon, Polygon


def extract_multipolygon(geometry):
    """
    Extracts a MultiPolygon from a Shapely geometry, containing only the polygonal components.
    If the input geometry is not a GeometryCollection or does not contain any polygonal components,
    it returns the original geometry.
    """
    if isinstance(geometry, GeometryCollection):
        polygons = []
        for geom in geometry.geoms:
            if isinstance(geom, Polygon):
                polygons.append(geom)
            elif isinstance(geom, MultiPolygon):
                polygons.extend(geom.geoms)
        if polygons:
            return MultiPolygon(polygons)
        else:
            return geometry
    elif isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    else:
        return geometry


def geometries_to_geojson(geometries):
    # Don't want the Lines, etc, if we had a GeometryCollection
    geometries = [extract_multipolygon(geom) for geom in geometries]
    features = []

    for polygon in geometries:
        # transformed_polygon = transform_geom_func(polygon)
        reprojected_geom = transform_geom(INPUT_CRS, OUTPUT_CRS, polygon)

        # reprojected_geometry is either a Polygon or a MultiPolygon

        # geojson_geometry = mapping(reprojected_geom)
        # geojson_geometry["crs"] = OUTPUT_CRS.to_dict()
        features.append(
            {"type": "Feature", "geometry": reprojected_geom, "properties": {}}
        )
    return features


def geojson_for_msoa(msoa_id):
    shape = usable_shape_for_msoa(msoa_id, get_msoa_bounding_box(msoa_id))
    geojson_features = geometries_to_geojson([shape])
    return {"type": "FeatureCollection", "features": geojson_features}


def write_geojson_for_msoas(msoa_ids):
    shapes = [
        usable_shape_for_msoa(msoa_id, get_msoa_bounding_box(msoa_id))
        for msoa_id in msoa_ids
    ]
    geojson_features = geometries_to_geojson(shapes)
    geojson_data = {"type": "FeatureCollection", "features": geojson_features}
    with open("usable_area_all.geojson", "w") as file:
        json.dump(geojson_data, file)

    return


def urban_area_for_msoa(msoa_id) -> float:
    # shape = fetch_brighton_shape_cached(msoa_id)
    # polygon = Polygon(shape)
    # total_area = polygon.area
    # return total_area
    shape: MultiPolygon = usable_shape_for_msoa(msoa_id, get_msoa_bounding_box(msoa_id))
    return shape.area


def building_area_for_msoa(msoa_id):
    buildings = buildings_for_msoa(
        fetch_brighton_shape_cached(msoa_id),
        get_msoa_bounding_box(msoa_id),
    )
    return total_area_for_buildings(buildings)


def main_function():
    msoa_id = "E02003523"
    # msoa_id = "E02000028"
    # msoa_shape = fetch_brighton_shape_cached(msoa_id)
    # msoa_bbox = get_msoa_bounding_box(msoa_id)

    # file_path = "./data/census/brighton_dwelling_types_counts.csv"
    # unique_msoas = get_all_msoas(file_path)
    # write_geojson_for_msoas(unique_msoas)

    # buildings = buildings_for_msoa(msoa_shape, msoa_bbox)
    # write_geojson_for_buildings(msoa_id, buildings)

    # greenspaces = greenspace_for_msoa(msoa_shape, msoa_bbox)
    # write_geojson_for_greenspaces(msoa_id, greenspaces)

    # buildings_area = total_area_for_buildings(buildings)
    # msoa_area = total_area_for_msoa(msoa_id=msoa_id)
    # fraction = buildings_area / msoa_area
    # print(f"Fraction of the MSOA area covered by buildings: {fraction:.4f}")
    return


if __name__ == "__main__":
    start_time = time.time()
    main_function()
    end_time = time.time()
    print("Time taken in seconds: ", end_time - start_time)
