#!/usr/bin/python

import argparse,sys

def usage():
    print("""

    Usage: annotator.py --input input.csv [--output output.csv]

    Annotates genes using the fastANNI algorithm
    
    Takes as input csv file of genes and adds more columns containing annotation information
    """)

    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description = """
            Annotates genes using the FastANNI algorithm
            Takes as input a csv file of genes.
            Generates a new csv file containing annotation information in a new column
            """
    )
    parser.add_argument("--input", nargs=1)
    parser.add_argument("--output", nargs=1)
    args = parser.parse_args()
    print("Input = " + str(args.input))
    print("Output = " + str(args.output))

if __name__ == "__main__":
    main()
