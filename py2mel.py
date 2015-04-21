#!/usr/bin/env python
# Python to Mel converter
# Allows running of Python code by dragging into the Maya viewport

# Created 21/04/2015
# Jason Dixon
# jason.dixon.email@gmail.com
# internetimagery.com

# Usage
# cat <inputFile> | py2mel.py > <outputFile>

# OR
# py2mel.py -input <inputFile> -output <outputFile>

import argparse
import datetime
import sys

version = "v1.0.0"
parser = argparse.ArgumentParser(
    description="Convert Python file to Melscript (using python interpreter).",
    epilog="Use either standard in and out, the -input -output flags or a combination of both. ie: cat INPUTFILE | py2mel.py > OUTPUTFILE")
parser.add_argument("-i", "--input", help="Input file for processing.", type=argparse.FileType('r'))
parser.add_argument("-o", "--output", help="Output file for processing.", type=argparse.FileType('w'))
args = parser.parse_args()


def parse_python(data, version=False):
    output = "// py2mel.py %s, compiled %s\n\n" % (version, datetime.datetime.today()) if version else ""
    output += "python(\"%s\");" % data.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", r"\n")
    return output

inp = args.input if args.input else sys.stdin
out = args.output if args.output else sys.stdout
out.write(parse_python(inp.read(), version))
