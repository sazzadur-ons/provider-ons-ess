import click
import pandas as pd
import math
from pathlib import Path


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("--output", default=Path("./gross-median-weekly-pay.csv"), type=click.Path(path_type=Path))
def wrangle(input: Path(), output: Path()) -> None:
    df = pd.read_excel(input)

    df = df.drop(columns=['AREANM', 'Geography', 'Variable Name', 'Observation Status', 'Polarity', 'Notes'])

    #Area and Geography are unneeded, Geocode is enough
    #Variable name contains the name as indicator
    #Observation status are all normal
    #Polarity is all 1
    #Notes are all empty, can add any of these back if needed

    df = df.rename(columns= {'AREACD':'Area', 'Value':'Observation'})

    # Add marker column as there are missing values in observation column
    df["Marker"] = ''
    
    df.loc[(df["Observation"].isnull()), "Marker"] = "N/A"

    df = df[['Period', 'Area', 'Mission', 'Category', 'Indicator', 'Observation', 'Marker', 'Lower Confidence Interval (95%)', 'Upper Confidence Interval (95%)']]

    #Not sure whether to keep in Indicator or Mission
    #Indicator seems to just be measure type but unsure if to be used to compare datasets
    #no idea what mission is used for but keeping it in regardless
    #Unsure whether to remove Indicator and include it as the measure in the config

    df.to_csv(output, index=False)
    return

if __name__ == "__main__":

    wrangle()