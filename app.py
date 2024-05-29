from typing import List
from flask import Flask, render_template
import folium
from folium.features import GeoJson, GeoJsonPopup
from dataclasses import asdict

from density import MsoaDensityData, get_msoa_data_cached, get_msoa_data

app = Flask(__name__)


@app.route("/")
def index():
    # Get your MsoaDensityData objects
    msoa_data_list: List[MsoaDensityData] = (
        get_msoa_data_cached()
    )  # Assuming you have a function that returns a list of MsoaDensityData objects

    map = folium.Map(location=[50.8225, -0.1372], zoom_start=12)

    for msoa_data in msoa_data_list:
        geojson_data = msoa_data.to_geojson_feature()
        geojson = folium.GeoJson(
            geojson_data,
            name="MSOA Data",
            popup=folium.GeoJsonPopup(
                fields=[
                    "msoa_code",
                    "msoa_name",
                    "population",
                    # "urban_area",
                    # "building_coverage_area",
                    "area",
                    "building_coverage",
                    "dwellings",
                    "detached_or_semi_percent",
                    "population_density",
                    "occupation",
                    "dwelling_density",
                    "target_density",
                    "new_homes",
                ],
                aliases=[
                    "MSOA Code",
                    "Area name",
                    "Population",
                    # "Urban Area",
                    # "Building Coverage Area",
                    "Built Up Area",
                    "Building Coverage (%)",
                    "Number of Dwellings",
                    "Of which Detached or Semi-Detached (%)",
                    "Population Density",
                    "Occupation",
                    "Dwelling Density",
                    "Possible Density",
                    "New Homes Produced",
                ],
            ),
        )
        geojson.add_to(map)

    map_html = map._repr_html_()
    return render_template("index.html", map_html=map_html)


if __name__ == "__main__":
    app.run(debug=True)
