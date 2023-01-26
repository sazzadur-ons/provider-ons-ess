import click
import pandas as pd
import math
from pathlib import Path


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("--output", default=Path("./output.csv"), type=click.Path(path_type=Path))
def wrangle(input: Path(), output: Path()) -> None:
    df = pd.read_csv(input)
    
    df = df.replace({'Period' :{201821 : '2018-2021',
                                201719 : '2017-2019', 
                                201820 : '2018-2020', 
                                201920 : '2019-2020',
                                202021 : '2020-2021',
                                202122 : '2021-2022'}})

    df['Marker'] = ''

    df['Marker'] = df.apply(lambda x: 'not-available' if math.isnan(x['Value']) else '', axis = 1)
    df['MAD'] = df.apply(lambda x: '' if pd.isnull(x['MAD']) else x['MAD'], axis = 1)
    
    df.to_csv(output, index=False)
    return


if __name__ == "__main__":
    wrangle()