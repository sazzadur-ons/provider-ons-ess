import click
import pandas as pd
import math
import re
from pathlib import Path


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("--output", default=Path("./output.csv"), type=click.Path(path_type=Path))
def wrangle(input: Path(), output: Path()) -> None:
    df = pd.read_excel(input)

    df = df.drop(columns=['AREANM', 'Geography', 'Variable Name', 'Lower Confidence Interval (95%)', 'Upper Confidence Interval (95%)', 'Observation Status', 'Polarity'])#, 'Notes'])

    #Area and Geography are unneeded, Geocode is enough
    #Variable name contains the name as indicator
    #Lower and Upper CI are all NA
    #Observation status are all normal
    #Polarity is all 1
    #Notes are all empty, can add any of these back if needed

    df = df.rename(columns= {'AREACD':'Area', 'Value':'Observation'})

    df['Area'] = df.apply(lambda x: re.search(r'[E](\w{8})\b', x['Notes']).group(0) if 'Obsolete' in str(x['Notes']) else x['Area'], axis = 1)

    #obsolete area codes have been replaced

    df = df[['Period', 'Area', 'Mission', 'Category', 'Indicator', 'Observation', 'Notes']]#, 'Measure', 'Unit']]

    #Not sure whether to keep in Indicator or Mission
    #Indicator seems to just be measure type but unsure if to be used to compare datasets
    #no idea what mission is used for but keeping it in regardless

    #Unsure whether to remove Indicator and include it as the measure in in the config
    
    df.to_csv(output, index=False)
    return


if __name__ == "__main__":

    wrangle()