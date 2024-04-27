import csv
from dataclasses import dataclass

# csv format:
# Middle layer Super Output Areas Code	Middle layer Super Output Areas	Accommodation by type of dwelling (9 categories) Code	Accommodation by type of dwelling (9 categories)	Observation

# For column
# Accommodation by type of dwelling (9 categories) Code
DETACHED_OR_SEMI_LABELS = [1, 2]
DATA_FOLDER = "./census"


@dataclass
class MsoaDwellings:
    msoa_code: str
    total_dwellings: int
    detached_or_semi: int


# Sum the total number of dwellings and the number of detached or semi-detached dwellings for an MSOA
def get_msoa_dwellings(msoa_code, file_path):
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        next(reader)
        total_dwellings = 0
        detached_or_semi = 0
        for row in reader:
            if row[0] == msoa_code:
                total_dwellings += int(row[4])
                if int(row[2]) in DETACHED_OR_SEMI_LABELS:
                    detached_or_semi += int(row[4])

    return MsoaDwellings(msoa_code, total_dwellings, detached_or_semi)


def get_all_msoas(file_path):
    msoas = set()
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        for row in reader:
            msoas.add(row[0])

    as_sorted_list = sorted(list(msoas))
    return as_sorted_list


def brighton_msoa_dwellings():
    file_path = DATA_FOLDER + "/brighton_dwelling_types_counts.csv"
    unique_msoas = get_all_msoas(file_path)
    return [get_msoa_dwellings(msoa, file_path) for msoa in unique_msoas]


if __name__ == "__main__":
    brighton_msoa_dwellings()
