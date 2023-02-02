import click
import pandas as pd
import math
from pathlib import Path


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("--output", default=Path("./output.csv"), type=click.Path(path_type=Path))
def wrangle(input: Path(), output: Path()) -> None:
    df = pd.read_csv(input)

    df = df.drop(columns=['AREANM', 'Geography', 'Variable Name', 'Lower Confidence Interval (95%)', 'Upper Confidence Interval (95%)', 'Observation Status', 'Polarity'])#, 'Notes'])

    #Area and Geography are unneeded, Geocode is enough
    #Variable name contains the name as indicator
    #Lower and Upper CI are all NA
    #Observation status are all normal
    #Polarity is all 1
    #Notes are all empty, can add any of these back if needed

    df = df.rename(columns= {'AREACD':'Area', 'Value':'Observation'})

    df = df[['Period', 'Area', 'Mission', 'Category', 'Indicator', 'Observation']]#, 'Measure', 'Unit']]

    #Not sure whether to keep in Indicator or Mission
    #Indicator seems to just be measure type but unsure if to be used to compare datasets
    #no idea what mission is used for but keeping it in regardless

    #Unsure whether to remove Indicator and include it as the measure in in the config

    indexNames = df[ df['Area'].str.contains('na')].index
    df.drop(indexNames, inplace = True)

    #There are multiple entries which have 'na' area codes, these are noted as 'Outside of England and unknown' 
    #I don't think we support this, if we do I can make changes

    df['Period'] = df.apply(lambda x: 'government-year/' + str(x['Period'])[:4] + '-20' +  str(x['Period'])[-2:], axis = 1)

    df = df.drop_duplicates()

    #for some reason there are 1to1 dupes   
    
    df.to_csv(output, index=False)
    return


if __name__ == "__main__":

    wrangle()