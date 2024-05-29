# schema for CSV file
# Middle layer Super Output Areas Code	Middle layer Super Output Areas	Sex (2 categories) Code	Sex (2 categories)	Observation


import csv
from dataclasses import dataclass


@dataclass
class MsoaPopulation:
    msoa_code: str
    total_population: int


def get_msoa_population(msoa_code, file_path):
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        next(reader)
        total_population = 0
        for row in reader:
            if row[0] == msoa_code:
                total_population += int(row[4])

    return MsoaPopulation(msoa_code, total_population)


def get_all_msoas(file_path):
    msoas = set()
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for row in reader:
            msoas.add(row[0])

    as_sorted_list = sorted(list(msoas))
    return as_sorted_list


def brighton_msoa_population():
    file_path = "./data/census/brighton_population.csv"
    unique_msoas = get_all_msoas(file_path)
    return [get_msoa_population(msoa, file_path) for msoa in unique_msoas]


if __name__ == "__main__":
    pop = brighton_msoa_population()
