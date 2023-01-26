import click
import pandas as pd
import math
from pathlib import Path


@click.command()
@click.argument("input", type=click.Path(exists=True, path_type=Path))
@click.option("--output", default=Path("./output.csv"), type=click.Path(path_type=Path))
def wrangle(input: Path(), output: Path()) -> None:
    df = pd.read_csv(input)
    
    
    
    df.to_csv(output, index=False)
    return


if __name__ == "__main__":
    wrangle()