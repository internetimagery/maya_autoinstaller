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

parser = argparse.ArgumentParser(
    description="Convert Python file to Melscript (using python interpreter).",
    epilog="Use either standard in and out, the -input -output flags or a combination of both. ie: cat INPUTFILE | py2mel.py > OUTPUTFILE")
parser.add_argument("-i", "--input", help="Input file for processing.", type=argparse.FileType('r'))
parser.add_argument("-o", "--output", help="Output file for processing.", type=argparse.FileType('w'))
parser.add_argument("-s", "--shelf", help="Optional! Name to give to shelf icon if dropping causes shelf icon.", type=str)
args = parser.parse_args()


def stringify(data):
    return data.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", r"\n")


def version():
    version = "v1.0.1"
    return "py2mel.py %s, compiled %s\n\n" % (version, datetime.datetime.today())


def python_interpret(data):
    output = "// %s" % version()
    output += "python(\"%s\");" % stringify(data)
    return output


def python_shelf(data, name):
    code = "# %s" % version()
    code += data
    return "shelfButton -l \"%s\" -c \"%s\" -stp \"python\" -i \"daisyLarge.png\" -p `tabLayout -query -selectTab $gShelfTopLevel`;" % (name, stringify(code))

inp = args.input if args.input else sys.stdin
out = args.output if args.output else sys.stdout
data = python_shelf(inp.read(), args.shelf) if args.shelf else python_interpret(inp.read())
out.write(data)
