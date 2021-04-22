#!/usr/bin/env python3

import os
import pprint
import sys
import re
import subprocess
import logging

from collections import defaultdict
from datetime import datetime

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.WARNING)
logger = logging.getLogger()

rows, columns = os.popen('stty size', 'r').read().split()
rows = int(rows)
columns = int(columns)

files_processed_set = set()
results = defaultdict(int)
pp = pprint.PrettyPrinter(indent=4)

files_succeeded = 0
files_processed_int = 0
total_files_present = 0
# Define a whitepace stripper
rex = re.compile(r"\s+")

# A list of c reserved words I care about
c_reserved_words = [
    "int",
    "long",
    "double",
    "float",
    "bool",
    "char",
    "short",
    "void",
    "signed",
    "unsigned",
    "struct",
    "enum",
    "union",
    "FILE",
    "const",
]

c_keywords = [
    "for", "else", "if", "switch", "while", "sizeof"
]

# A list of c primitive types
c_primitives = [
    "int",
    "float",
    "bool",
    "char",
    "short",
    "void",
    "struct",
    "enum",
    "union",
    "FILE",
]

# C modifiers, cannot be by themselves, but must preceed a primitive
c_modifiers = [
   "signed",
   "unsigned",
   "short",
   "long"
]

include_directories = []


def analyzeFile(filename: str):
    
    global files_processed_int
    global results
    global files_succeeded

    print(" " * columns, end='\r')
    #print(f"\rAnalyzing {filename}", end="\n")
    if files_processed_int == total_files_present -1:
        percent_done = 1
    else:
        percent_done = float(files_processed_int / total_files_present)
    percent_done_str = f"{100*percent_done:.1f}%"
    col_count = columns - 2 - len(percent_done_str)
    progress_bar = percent_done_str +"="*round(percent_done*col_count)+">"+round(col_count-percent_done*col_count)*" "+"|"
    print(progress_bar, end="\r")
    if percent_done == 1:
        print()

    with open(filename, "r", errors='replace') as this_file:
        file_contents = this_file.readlines()
        file_contents = " ".join(file_contents)
        file_contents = file_contents.replace(",\n", ", ")
        file_contents = re.sub(r"\s*\(", "(", file_contents)
        file_contents = file_contents.split("\n")
        for line in file_contents:
            line = comment_remover(line)
            if '(' not in line:
                continue
            line = rex.sub(" ", line)
            try:
                args = line[line.find("(") + 1 : line.find(")")]
            except IndexError as e:
                logger.error(f"in file {filename} {e} getting trying to get args on line: {line}")
                sys.exit(1)
                continue
            try:
                function_name = line[:line.find("(")].split()[-1]
                logger.debug(function_name)
                if function_name in c_keywords:
                    continue
                if function_name.strip("_").isupper():
                    logger.info(f"Skipping liekly macro function: {function_name}")
                    continue
            except IndexError as e:
                logger.debug(f"in file {filename} {e} getting trying to get function name on line: {line}")
                #sys.exit(1)
                continue

            if not args:
                continue

            try:
                match = re.match(r"\s*.*\b", args)[0].strip()
            except TypeError as e:
                logger.debug(f"Type Error getting match{e}")
                continue

            if (not match) or (match.split()[0] not in c_reserved_words):
                logger.debug("Not match or match not in reserved words.")
                continue

            args = [arg.strip() for arg in args.split(",")]
            logger.debug(f"Args: {args}")
            for arg in args:
                ptr = ""
                    
                if "*" in arg:
                    try:
                        arg_name = arg.split("*")[1]
                    except IndexError as e:
                        logger.debug(f"Exception on arg split 1: {e}")
                    ptr = "ptr_" * arg.count("*")
                else:
                    try:
                        arg_name = arg.split()[-1]
                    except IndexError as e:
                        logger.debug(f"Exception on arg split 2: {e}")

                # Is this arg an array?  An N-Dimensional array?
                array_count = 0
                if "[" in arg:
                    array_count = arg.count("[")
                    if array_count > 1:
                        array_count = str(array_count) +"D_array_" 
                    else:
                        array_count = "array_"

                #arg_type = arg.split()
                modifiers = ""
                for arg_type in arg.split():
                    if arg_type in c_primitives:
                        break
                    else:
                        modifiers += arg_type.replace("_","") + "_"
               
                if arg_type not in c_primitives:
                    logger.debug(f"Argtype: {arg_type} not in primitives.")
                    continue
                arg_type += "_"
                if array_count:
                    dict_entry = f"{array_count}{modifiers}{arg_type}{ptr}".strip("_")
                else:
                    dict_entry = f"{modifiers}{arg_type}{ptr}".strip("_")
                if "__" in dict_entry:# or not dict_entry.isalnum():
                    print(f"On line {line} got bad dict entry: {dict_entry}")
                if "alwaysunused" in dict_entry:
                    #print(f"Skipping unused arg: {dict_entry}")
                    continue
                if "(" in dict_entry:
                    continue
                    #print(f"From function {function_name}{*args,}:\nline: {line}\nAdding BAD {dict_entry} to dictionary")
                if not re.match("^([a-zA-Z0-9_])*$", dict_entry):
                    #print(f"Skipping non-valid arg: {dict_entry}\nFrom line {line}")
                    continue
                logger.info(f"From function {function_name}{*args,}\nline: {line}\nAdding {dict_entry} to dictionary")

                results[dict_entry] += 1
        files_succeeded += 1
    return

def comment_remover(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)

def dirWalk(path):
    global files_processed_set
    global files_processed_int
    print(f"Entered dirWalk() with path: {path}")
    # traverse root directory, and list directories as dirs and files as files
    for root, _, files in os.walk(path):
        path = root.split(os.sep)
        for file in files:
            #print(file)
            if not file.lower().endswith((".c",".h",".cpp",".h")):
                continue
            if file[:file.rfind(".")] in files_processed_set:
                continue
            files_processed_int += 1
            files_processed_set.add(file[:file.rfind(".")])
            analyzeFile(os.path.join(root, file))


def getAllFiles(dir_name):
    # Get the list of all files in directory tree at given path
    all_files = []
    for (dirpath, dirnames, filenames) in os.walk(dir_name):
        all_files += [os.path.join(dirpath, file) \
            for file in filenames if file.lower().endswith((".c",".h",".cpp",".hpp"))]
    return all_files

def usage(argv):
    print(f"Usage: {argv[0]} [-I <include dir>,] <dir> [<dir>,]")
    sys.exit(1)


def main(argv):
    if (len(argv)) == 1:
        usage(argv)

    total_files = 0
    path_index = 1
    global include_directories
    file_directories = []

    for dir in argv[1:]:
        if not os.path.isdir(dir):
            print(f"Header directory: {dir} is not a valid directory. Skipping.")
        else:
            file_directories.append(dir)

    global total_files_present 
    all_files = []
    for dir in file_directories:
        all_files += getAllFiles(dir)
    total_files_present = len(all_files)

    if not total_files_present:
        print("No files found!")
        sys.exit(1)

    print(f"Found {total_files_present} files")
    global files_processed_int
    files_skipped = 0
    for file in all_files:
        files_processed_int += 1

        if file[:file.rfind(".")] in files_processed_set:
            files_skipped += 1
            continue
        files_processed_set.add(file[:file.rfind(".")])
        analyzeFile(file)
    """
    for dir in file_directories:
        if dir != ".git":
            dirWalk(dir)
    """
    print(f"Processed {files_processed_int} files.")

    time = datetime.now().strftime('%Y-%m-%d%H:%M:%S')
    file_name = "arg_parser_results_" + time +".csv"
    with open(file_name, "w") as f:
        f.write(f"Files Succeeded: {files_succeeded}")
        f.write(f"Total Files: {files_processed_int}")
        if total_files:
            f.write(f"Percent Success: {round(100*float(files_succeeded / total_files))}%")        
        for k, v in results.items():
            f.write(f"{k},{v}")
    print(f"Files Succeeded: {files_succeeded}")
    print(f"Files Skipped: {files_skipped}")
    print(f"Files Failed: {total_files_present - files_succeeded - files_skipped}")
    print(f"Total Files: {total_files_present}")
    if total_files:
        print(f"Percent Success: {round(100*float(files_succeeded / total_files))}%")

    pp.pprint(results)


if __name__ == "__main__":
    main(sys.argv)
