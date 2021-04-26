#!/usr/bin/env python3

'''
Reverse Engineering Helper -
This script is used to create a database of C function signatures as follows:

function_name,arg_count,return_type, is_variadic,
Arg #0 Array Count,Arg #0 Modifiers,Arg #0 Pointer Count,Arg #0 Type,...
- For all N arguments
Notes:
Arg #N Array Count: Indicates if this arg is an N-dimensional array
Arg #N Pointer Count: Similar to the above 
    - indicates how many levels of pointer redirection for this arg

Simply provide any number of C files as arguments
(includes preprocessed files - this is best) and a .csv will be produced that
can be analyzed in your favorite spreadsheet program (hint: use a pivot table)

Suggested use/motivation: use with Ghidra when Ghidra can't identify a function
'''

import copy
import os
import pprint
import sys
import re
import subprocess
import logging
import pandas as pd

from collections import defaultdict
from datetime import datetime

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.ERROR)
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
max_args = 0
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
original_c_primitives = set([
    "int",
    "float",
    "double",
    "bool",
    "char",
    "short",
    "void",
    "struct",
    "enum",
    "union",
    "FILE",
])

# C modifiers, cannot be by themselves, but must preceed a primitive
c_modifiers = [
   "signed",
   "unsigned",
   "short",
   "long"
]

c_scopes = [
    'static',
    'volatile'
]

include_directories = []

def show_nearest_neighbors(list1,  all_lists, display_limit):
    print(f"Comparing to function:\n{list1}")
    scores = defaultdict(list)
    for list2 in all_lists:
        if list1 != list2:
            score = edit_distance(list1.split(',')[1:], list2.split(',')[1:])
            scores[score].append(list2)

    display_count = 0
    for score in sorted(scores.keys()):
        if display_count >= display_limit:
            break
        print(f"Edit Distance: {score}".center(80,"="))
        for list2 in scores[score]:
            display_count += 1
            print(list2.strip())

                            

def edit_distance(list1, list2):
    # To compute the Levenshtein distance between two entries, 
    # say entries 92 and 94, 
    # try this in interactive mode after running this script:
    # edit_distance(results_list[92].split(',')[1:], results_list[94].split(',')[1:])

    """Ref: https://bit.ly/2Pf4a6Z"""
    #print(f"Comparing:\n{list1}{list2}")

    if len(list1) > len(list2):
        difference = len(list1) - len(list2)
        list1[:difference]

    elif len(list2) > len(list1):
        difference = len(list2) - len(list1)
        list2[:difference]

    else:
        difference = 0

    for i in range(len(list1)):
        try:
            if list1[i] != list2[i]:
                difference += 1
        except IndexError:
            break

    return difference

def analyzeFile(filename: str):
    
    results = defaultdict(int)
    #files_succeeded
    c_primitives = copy.deepcopy(original_c_primitives)
    max_args = 0
    these_results = []
    prev_line = ""
    all_lines = []

    print(" " * columns, end='\r')
    #print(f"\rAnalyzing {filename}", end="\n")
    if files_processed_int == total_files_present -1:
        percent_done = 1
    else:
        percent_done = float(files_processed_int / total_files_present)
    percent_done_str = f"{100*percent_done:.1f}%"
    col_count = columns - 2 - len(percent_done_str)
    progress_bar = percent_done_str +"="*round(percent_done*col_count)
    progress_bar += ">"+round(col_count-percent_done*col_count)*" "+"|"
    #print(progress_bar, end="\r")
    #if percent_done == 1:
    #    print()

    with open(filename, "r", errors='replace') as this_file:
        file_contents = this_file.readlines()
        file_contents = " ".join(file_contents)
        file_contents = file_contents.replace(",\n", ", ")
        file_contents = re.sub(r"\s*\(", "(", file_contents)
        file_contents = file_contents.split("\n")
        append_line = False
        prepend = ""
        for line in file_contents:
            line = comment_remover(line)
            line = line.strip()

            if append_line:
                line = prepend + line
            if line.endswith(','):
                prepend += line
                append_line = True
                continue
            else:
                append_line = False
            all_lines.append(line)

            if line.startswith("typedef") and line.endswith(";"):
                new_type = line.split()[-1].strip(';')
                logger.debug(f"Adding {new_type}")
                c_primitives.add(new_type)
                continue         
            if re.match("}\s*\w+\s*;", line):
                new_type = line.lstrip('}').strip(';').strip()
                logger.debug(f"Adding struct {new_type}")
                c_primitives.add(new_type)
            if '(' not in line:
                continue
            line = rex.sub(" ", line)
            try:
                args = line[line.find("(") + 1 : line.find(")")]
            except IndexError as e:
                err_msg = f"in file {filename} {e} getting trying "
                err_msg += f"to get args on line: {line}"
                logger.error(err_msg)
                sys.exit(1)
                continue
            try:
                function_name = line[:line.find("(")].split()[-1].strip()
                logger.debug(function_name)
                if function_name in c_keywords:
                    continue
                if function_name.strip("_").isupper():
                    logger.info(f"Skipping likely macro function: {function_name}")
                    continue
                if not re.match("\*?[a-zA-Z_]\w*", function_name):
                    print(f"{function_name} is not a valid function name.  Skipping")
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
            #return_type = line.split(function_name)[0].strip()
            
            return_type = re.split(f"{function_name.strip('*')}\s*\(", line)[0].strip()
            return_type = [x for x in return_type.split() if x in c_primitives or ( x != "__extern__" and not x.startswith("__") and x != "extern")]
            return_type = " ".join(return_type).strip()
            if not return_type:
                logger.info(f"No type for {function_name}")
                return_type = re.split(f"{function_name.strip('*')}\s*\(", all_lines[-2])[0].strip()
                logger.info(f"No type for {function_name} #2: {return_type}: {all_lines[-1]}")
                return_type = [x for x in return_type.split() if x in c_primitives or ( x != "__extern__" and not x.startswith("__") and x != "extern")]
                return_type = " ".join(return_type).strip()
            logger.debug(f"Args: {args}")
            logger.info("-"*80)
            logger.info(f"From function {function_name}{*args,}")
            logger.info(f"line: {line}")                
            logger.info(f"Return type: {return_type}")
            this_row = {}
            this_row["function_name"] = function_name
            this_row["return_type"] = return_type.lstrip("extern ")
            this_row["is_variadic"] = "False"
            for arg_index, arg in enumerate(args):
                if arg_index > max_args:
                    max_args = arg_index
                ptr = ""
                ptr_count = 0

                    
                if "*" in arg:
                    try:
                        _ = arg.split("*")[1]
                    except IndexError as e:
                        logger.debug(f"Exception on arg split 1: {e}")
                    ptr_count = arg.count("*")
                    ptr = "ptr_" * ptr_count
                    
                else:
                    try:
                        _ = arg.split()[-1]
                    except IndexError as e:
                        logger.debug(f"Exception on arg split 2: {e}")

                # Is this arg an array?  An N-Dimensional array?
                array_count = 0
                this_row[f"Arg #{arg_index} Array Count"] = array_count

                if "[" in arg:
                    array_count = arg.count("[")
                    this_row[f"Arg #{arg_index} Array Count"] = array_count

                    if array_count > 1:
                        array_count = str(array_count) +"D_array_" 
                    else:
                        array_count = "array_"
                else:
                    this_row[f"Arg #{arg_index} Array Count"] = 0


                #arg_type = arg.split()
                modifiers = ""
                for arg_type in arg.split():
                    if arg_type in c_primitives:
                        break
                    
                    else:
                        modifiers += arg_type.replace("_","") + "_"
                if '...' in arg_type:
                    logger.info("This is a variadic function.")
                    this_row["is_variadic"] = "True"
                    continue                      
                elif arg_type not in c_primitives:
                    logger.debug(f"Argtype: {arg_type} not in primitives.")
                    continue
                this_row[f"Arg #{arg_index} Type"] = arg_type

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
                    #print(f"From function {function_name}{*args,}:
                    #print(f"line: {line}\nAdding BAD {dict_entry} to dictionary")

                if not re.match("^([a-zA-Z0-9_])*$", dict_entry):
                    #print(f"Skipping non-valid arg: {dict_entry}\nFrom line {line}")
                    continue

                logger.info(f"Adding arg #{arg_index}: {dict_entry} to dictionary")
                this_row[f"Arg #{arg_index} Pointer Count"] = ptr_count
                this_row[f"Arg #{arg_index} Modifiers"] = modifiers


                results[dict_entry] += 1
            this_row['arg_count'] =  str(arg_index+1)
            logger.info("Done with row")
            #pprint.pprint(this_row)
            these_results.append(this_row)
        #files_succeeded += 1
    return these_results, max_args

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
    max_args = 0
    total_files = 0
    path_index = 1
    global include_directories
    file_directories = []
    all_files = []
    double_nested_list = []

    for dir in argv[1:]:
        if os.path.isfile(dir):
            all_files.append(dir)
        elif not os.path.isdir(dir):
            print(f"Header directory: {dir} is not a valid directory. Skipping.")
        else:
            file_directories.append(dir)

    global total_files_present 
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
        these_results, this_max_arg = analyzeFile(file)
        double_nested_list.append(these_results)
        max_args = max(max_args, this_max_arg)

    all_results = set()
    header = "function_name,arg_count,return_type, is_variadic"
    for i in range(max_args+1):
        header += f",Arg #{i} Array Count"
        header += f",Arg #{i} Modifiers"
        header += f",Arg #{i} Pointer Count"
        header += f",Arg #{i} Type"
    header += '\n'
    col_count = header.count(',')-1    
    for l1 in double_nested_list:
        for l2 in l1:
            #row = str(index)
            row = l2.pop('function_name')
            row += ","+l2.pop('arg_count')
            row += ","+l2.pop('return_type')
            row += ","+l2.pop('is_variadic')
            for k in sorted(l2.keys()):
                row += ',' + str(l2[k])
            row += ',' * (col_count - row.count(','))
            row = row.replace("\n","")
            all_results.add(row+"\n")

    #all_results = {k:v for x in dict_list for k,v in x.items()}
    """
    for dir in file_directories:
        if dir != ".git":
            dirWalk(dir)
    """
    print(f"Processed {files_processed_int} files.")

    time = datetime.now().strftime('%Y-%m-%d%H:%M:%S')
    file_name = "arg_parser_aggregated_types_" + time +".csv"
    with open(file_name, "w") as f:
        #f.write(f"Files Succeeded: {files_succeeded}")
        #f.write(f"Total Files: {files_processed_int}")
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

    file_name = "arg_parser_results_" + time +".csv"
    #pp.pprint(results)
    #pp.pprint(all_results)
    all_results = sorted(all_results)
    with open(file_name, "w") as w:
        w.write(header)
        for entry_index, entry in enumerate(all_results):
            print(f"{entry_index} {entry.strip()}")
            w.write(entry)

    print(f"Max arg count: {max_args+1}")
    return list(all_results)

if __name__ == "__main__":
    results_list = main(sys.argv)
    
