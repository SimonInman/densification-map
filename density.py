from dataclasses import asdict, dataclass
import json
import pickle
import time
from typing import List
from census.population import get_msoa_population
from zoomstack.parse_zoomstack_data import (
    building_area_for_msoa,
    geojson_for_msoa,
    urban_area_for_msoa,
    write_geojson_for_msoas,
)
from census.collate_dwelling_types import (
    MsoaDwellings,
    brighton_msoa_dwellings,
    get_all_msoas,
)

DATA_FOLDER = "./census"


@dataclass
class MsoaDensityData:
    msoa_code: str
    msoa_name: str
    geojson: str
    dwelling_info: MsoaDwellings
    urban_area: float
    building_coverage_area: float
    population: int

    def target_density(self) -> float:
        existing_density = self.dwelling_info.total_dwellings / (
            self.urban_area / 10_000
        )
        detached_or_semi_percent = (
            self.dwelling_info.detached_or_semi / self.dwelling_info.total_dwellings
        )
        if detached_or_semi_percent > 0.4:
            new_density = existing_density * 1.5
        elif detached_or_semi_percent < 0.1:
            new_density = existing_density * 1.1
        else:
            new_density = existing_density * 1.25

        coverage_percent = self.building_coverage_area / self.urban_area
        if coverage_percent < 0.2:
            new_density *= 1.4

        return new_density

    def derived_properties(self) -> dict:
        properties = {}
        ## Area: 60.13 ha
        ## Building Coverage: 29.09%
        ## Dwellings: 4,470, of which detached and semi-detached houses: 220 (4.91%)
        ## Population Density: 138 people / hectare
        ## Occupation: 1.85 people / dwelling
        ## Dwelling Density: 74 dwellings / hectare
        area_in_hectares = self.urban_area / 10_000
        properties["area"] = f"{area_in_hectares:.2f} ha"
        properties["building_coverage"] = (
            f"{self.building_coverage_area / self.urban_area * 100:.2f}%"
        )
        properties["dwellings"] = self.dwelling_info.total_dwellings
        properties["detached_or_semi_percent"] = (
            f"{self.dwelling_info.detached_or_semi / self.dwelling_info.total_dwellings * 100:.2f}%"
        )
        properties["population_density"] = (
            f"{self.population / area_in_hectares:.2f} people / hectare"
        )
        properties["occupation"] = (
            f"{self.population / self.dwelling_info.total_dwellings:.2f} people / dwelling"
        )
        properties["dwelling_density"] = (
            f"{self.dwelling_info.total_dwellings / area_in_hectares:.2f} dwellings / hectare"
        )
        target = self.target_density()
        properties["target_density"] = f"{target:.2f} dwellings / hectare"
        new_homes = target * area_in_hectares - self.dwelling_info.total_dwellings
        properties["new_homes"] = f"{new_homes:.0f} new homes"
        return properties

    def to_geojson_feature(self):
        properties = asdict(self)

        del properties["geojson"]  # Remove the geojson field

        # feature_collection = json.loads(self.geojson)
        feature_collection = self.geojson

        for feature in feature_collection["features"]:
            feature["properties"].update(properties)

        additional_properties = self.derived_properties()
        for feature in feature_collection["features"]:
            feature["properties"].update(additional_properties)

        return feature_collection


def get_msoa_name(msoa_code: str, file_path: str) -> str:
    # Read the csv file line by line. If column 0 matches the msoa_code, return column 3
    with open(file_path, "r") as file:
        for line in file:
            row = line.strip().split(",")
            if row[0] == msoa_code:
                return row[3]

    assert False, f"MSOA code {msoa_code} not found in file {file_path}"


def density_data_for_msoa(msoa_code: str):
    all_msoa_dwellings = brighton_msoa_dwellings()
    this_msoa_dwellings = [d for d in all_msoa_dwellings if d.msoa_code == msoa_code][0]

    urban_area = urban_area_for_msoa(msoa_code)
    building_coverage = building_area_for_msoa(msoa_code)
    building_coverage = building_area_for_msoa(msoa_code)
    population = get_msoa_population(
        msoa_code, DATA_FOLDER + "/brighton_population.csv"
    )
    geojson = geojson_for_msoa(msoa_code)

    name = get_msoa_name(msoa_code, DATA_FOLDER + "/msoa_names.csv")

    out = MsoaDensityData(
        msoa_code=msoa_code,
        msoa_name=name,
        geojson=geojson,
        dwelling_info=this_msoa_dwellings,
        urban_area=urban_area,
        building_coverage_area=building_coverage,
        population=population.total_population,
    )
    return out


# Print the data in the following format:
# Area: 60.13 ha
# Building Coverage: 29.09%
# Dwellings: 4,470, of which detached and semi-detached houses: 220 (4.91%)
# Population Density: 138 people / hectare
# Occupation: 1.85 people / dwelling
# Dwelling Density: 74 dwellings / hectare
def print_density_data(density_data: MsoaDensityData):
    urban_area_in_hectares = density_data.urban_area / 10_000
    print(f"Area: {urban_area_in_hectares:.2f} ha")
    coverage_percent = (
        density_data.building_coverage_area / density_data.urban_area * 100
    )
    print(f"Building Coverage: {coverage_percent:.2f}%")
    print(
        f"Dwellings: {density_data.dwelling_info.total_dwellings}, of which detached and semi-detached houses: {density_data.dwelling_info.detached_or_semi} ({density_data.dwelling_info.detached_or_semi / density_data.dwelling_info.total_dwellings * 100:.2f}%)"
    )
    print(
        f"Population Density: {density_data.population / urban_area_in_hectares:.2f} people / hectare"
    )
    print(
        f"Occupation: {density_data.population / density_data.dwelling_info.total_dwellings:.2f} people / dwelling"
    )
    print(
        f"Dwelling Density: {density_data.dwelling_info.total_dwellings / urban_area_in_hectares:.2f} dwellings / hectare"
    )


def get_msoa_data_cached() -> List[MsoaDensityData]:
    # get the data from this dumped file:
    # with open(DATA_FOLDER + "/brighton_full_density_data.json", "w") as file:
    #    json.dump([asdict(d) for d in out], file)

    with open(DATA_FOLDER + "/brighton_full_density_data.json", "rb") as file:
        data = pickle.load(file)
        print("Loaded data from cache")
        print(data[0])
        return data


def get_msoa_data() -> List[MsoaDensityData]:
    start = time.time()
    all_brighton_msoas = get_all_msoas(
        DATA_FOLDER + "/brighton_dwelling_types_counts.csv"
    )

    out = [density_data_for_msoa(msoa_id) for msoa_id in all_brighton_msoas]
    end = time.time()
    print("Time taken to get all MSOAs: ", end - start)

    # Dump the data to a json file
    with open(DATA_FOLDER + "/brighton_full_density_data.json", "wb") as file:
        pickle.dump(out, file)

    total_new_homes = sum(
        [
            d.target_density() * (d.urban_area / 10_000)
            - d.dwelling_info.total_dwellings
            for d in out
        ]
    )
    print("Total new homes: ", total_new_homes)
    return out


def main():
    get_msoa_data()
    # msoa_id = "E02003491"
    all_brighton_msoas = get_all_msoas(
        DATA_FOLDER + "/brighton_dwelling_types_counts.csv"
    )

    # write_geojson_for_msoas(all_brighton_msoas)

    # msoa_id = "E02003512"
    for msoa_id in all_brighton_msoas:

        start_time = time.time()
        density_data = density_data_for_msoa(msoa_id)
        end_time = time.time()

        # print("********")
        # print("MSOA ID: ", msoa_id)
        # print("time taken: ", end_time - start_time)
        # print("********")

        print_density_data(density_data)


if __name__ == "__main__":
    # import cProfile
    # cProfile.run("main()", filename="density_2.prof")
    main()
