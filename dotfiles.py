#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import date
from getpass import getuser
from json import dumps
from pathlib import Path
from pprint import pprint
from shutil import copy
from sys import exit
from termcolor import colored
from terminaltables import AsciiTable


""" Usage
./dotfiles.py                           # Prints the DB table by default
./dotfiles.py -j db.json                # Saves the DB to a db.json file
./dotfiles.py -e globals home           # Checks you globals and home folder and symlinks to those files
./dotfiles.py -e globals
"""


ERROR_PREFIX = colored('ERROR:', 'red')
WARNING_PREFIX = colored('WARNING:', 'cyan')
SUCCESS_PREFIX = colored('SUCCESS:', 'green')


def parse_arguments():
    description = "Symnlinks your system's dotfiles to your custom dotfiles"
    parser = ArgumentParser(description=description)

    parser.add_argument("--env", "-e", nargs='+', choices=["globals", "work", 'home'],
                        type=str, metavar="globals home", help="Choose your environment")
    parser.add_argument("--print", "-p", action='store_true', default=True,
                        help="To print the dotfiles DB")
    parser.add_argument("--json", "-j", nargs="?", const="db.json", type=str,
                        help="The DB will be saved in <filename.json> or db.json (Default)")
    args = parser.parse_args()
    return args


def get_exclusions():
    "Reads .gitignore and returns a list of files/dirs to be excluded from the Database"
    dotignore = ".dotignore"
    try:
        with open(dotignore) as f:
            exclusions = f.read().split("\n")
            # print(exclusions)
        return exclusions
    except FileNotFoundError as err:
        print(f"{ERROR_PREFIX} The file {dotignore} cannot be found in the current dir")
    except Exception as err:
        print(f"{ERROR_PREFIX} {err}")


def get_envs(exclusions):
    "Returns a list of Environments (Directories) NOT Excluded on the .dotignore file"
    all_dirs = [x.as_posix() for x in Path(".").iterdir() if x.is_dir()]
    # print(all_dirs)
    dirs_excluded = [dirs for dirs in exclusions if dirs.endswith("/")]
    dirs_excluded = [dir_name.strip("/") for dir_name in dirs_excluded]
    environments = list(set(all_dirs) - set(dirs_excluded))
    # print(environments)
    return environments


def get_files_locations(environment, exclusions):
    """Gets a list of folders in the current dir(environment) and returns a str with the files inside those 
    folders IF they are not excluded."""
    files_locations = []
    for dirs in environment:
        for fls in Path(dirs).rglob(".*"):
            if fls.name not in exclusions and not fls.is_dir():
                # print(fls.resolve().as_posix())
                files_locations.append(fls.resolve().as_posix())
    return files_locations


def get_files_targets(files_locations):
    """Gets a lists of files location. Search the first line on each file for a string
    containing TARGET=<path> I.E TARGET=~/.vimrc. If no TARGET= is present, by default 
    the target will be ~/.<dotfile_name>
    Returns a list with the targets defined for each file. """
    files_targets = []
    TARGET_ID = "TARGET="
    for files in files_locations:
        with open(files) as f:
            target_path = f.readline().strip("\n")
        if TARGET_ID in target_path:
            target_path = target_path.split()
            target_path = [path for path in target_path if TARGET_ID in path]
            target_path = target_path[0].replace(TARGET_ID, "")
            files_targets.append(target_path)
        else:
            file_name = Path(files)
            file_name = file_name.name
            file_path = "~/" + file_name
            files_targets.append(file_path)
    return files_targets


def get_files_envs(environment, exclusions):
    """Gets a list of folders in the current dir(environment) and returns a str with the files inside those 
    folders IF they are not excluded."""
    files_envs = []
    for dirs in environment:
        for fls in Path(dirs).rglob(".*"):
            if fls.name not in exclusions and not fls.is_dir():
                files_envs.append(dirs)
    # print(files_envs)
    return files_envs


def get_nonexistent_targets(files_locations, files_targets):
    """Check if the file targets exist and return a list with True 
    if target DOES NOT exists or False if the target exists"""
    targets_to_add = []
    dotfiles = (dict(zip(files_locations, files_targets)))
    for target in dotfiles.values():
        path_target = Path(target).expanduser()
        if path_target.exists():
            targets_to_add.append(False)
        else:
            targets_to_add.append(True)
    return targets_to_add


def create_targets(targets_to_add, files_targets, selected_env, files_envs):
    """ Check if file targets exists in the current OS and if not creates them"""
    print("\n1 - CHECKING IF TARGETS EXISTS IN THE OS")
    for index, file_to_add in enumerate(targets_to_add):
        if (file_to_add == True) and (files_envs[index] in selected_env):
            new_file = files_targets[index]
            try:
                Path(new_file).expanduser().touch()
                new_file = colored(new_file, "green")
                print(f"{colored(SUCCESS_PREFIX)} File: {new_file} ---> "
                      f"has been created")
            except PermissionError:
                error_file = colored(new_file, "red")
                username = colored(getuser(), "red")
                print(f'{ERROR_PREFIX} "{username}" is not allowed to create '
                      f'"{error_file}", try chmod xxx {new_file} or change TARGET=')

    print(f'{SUCCESS_PREFIX} All targets exist in the OS.')


def process_symlinks(files_locations, files_targets, files_envs, selected_env):
    """ Receives lists with locations, targets, available envs and a string which selects 
    the environment to filter the environments to be used.
    Creates -> erroneous_symlinks[] if any symlink needs to be created changed
    and calls fix_symlinks(erroneous_symlinks)
    Returns targets_to_source if any symlink is modified, if not, returns None.
    """
    # Prints the changes that need to be carried out to inform the user
    selected_env_str = " - ".join(selected_env).upper()
    print(f'\n2 - CHECKING ALL SYMLINKS ON THE ENVS: "{selected_env_str}"')
    env_indexes = []
    erroneous_symlinks = []
    for index, env in enumerate(files_envs):
        if env in selected_env:
            env_indexes.append(index)

    filtered_locations = [files_locations[index] for index in env_indexes]
    filtered_targets = [files_targets[index] for index in env_indexes]
    dotfiles = (dict(zip(filtered_locations, filtered_targets)))

    # Checking if symlinks are correctly linked, if not add them to erroneous_symlinks[]
    for location, target in dotfiles.items():
        path_target = Path(target).expanduser()
        path_target_str = path_target.resolve().as_posix()
        if path_target.is_symlink():
            if path_target_str == location:
                print(
                    f"{SUCCESS_PREFIX} {target} is linked to the correct location.")
            else:
                print(f"{WARNING_PREFIX} {target} is linked to the wrong location.")
                # f"\tSymlink points to --> {colored(path_target.resolve(), 'red')}\n"
                # f"\tExpected pointer  --> {colored(location, 'green')}\n")
                erroneous_symlinks.append([target, location, path_target_str])
        else:
            print(f"{WARNING_PREFIX} {target} has NOT got a symlink.")
            erroneous_symlinks.append([target, location, None])

    if erroneous_symlinks:
        targets_to_source = fix_symlinks(erroneous_symlinks)
        return targets_to_source
    else:
        return None


def fix_symlinks(erroneous_symlinks):
    """ Receives a list with erroneus symlinks [] and ask the use if he/she wants to
    modify the symlink. If any symlink is modified the original file is first backed up.
    Returns targets_to_source[]
    """
    print(f"\n\t2.1 - FIXING SYMLINKS: The following symlinks will be changed on the env")
    for entries in erroneous_symlinks:
        target = entries[0]
        expected_sym = entries[1]
        current_sym = entries[2]
        print(f"\tFile: {target}\n"
              f"\tFrom --> {colored(current_sym, 'red')}\n"
              f"\tTo   --> {colored(expected_sym, 'green')}\n")
    while True:
        proceed = input(
            "\tWould you like to proceed with these changes(y/n)? ").lower()
        print()
        if proceed == "y" or proceed == "yes":
            targets_to_source = []
            for entries in erroneous_symlinks:
                target = entries[0]
                expected_sym = entries[1]
                current_sym = entries[2]
                try:
                    original_file = Path(target).expanduser()
                    wrong_symlink = original_file.is_symlink()
                    if wrong_symlink:
                        # Candidate for a function backup_file()
                        backup_file(src=target)
                        update_symlink(dotfile=original_file,
                                       target=expected_sym)
                        targets_to_source.append(original_file)
                    else:
                        update_symlink(dotfile=original_file,
                                       target=expected_sym)
                        targets_to_source.append(original_file)
                    continue
                except Exception as err:
                    print(err)
            break
        elif proceed == "n" or proceed == "no":
            print(f"\t{colored(ERROR_PREFIX)} EXITING - The symlinks need to be fixed "
                  f"to continue.")
            exit(1)
        else:
            print('\tInvalid answer - press "y" or "n"\n')

    print(f"\t{colored(SUCCESS_PREFIX)} All files have been correctly symlink.")
    return targets_to_source


def backup_file(src):
    """Receives a string with the source such as ~/.vimrc and it creates a backup file like
    ~/.vimrc-10-10-2020."""
    src = Path(src).expanduser()
    today = date.today().strftime("%d-%m-%Y")
    today_suffix = f"-backup-{today}"
    backup_file = src.as_posix() + today_suffix
    try:
        copy(str(src), backup_file)

        print(
            f'\tThe file: "{src}" has been backed up at --> "{colored(backup_file, "cyan")}"')
    except Exception as err:
        print(err)


def update_symlink(dotfile, target):
    """Receives a dotfile[] and the target[] to symlink to. Returns None"""
    target = Path(target).expanduser()
    if target:
        dotfile.expanduser().unlink()
        dotfile.expanduser().symlink_to(target)
        # print(target)
    else:
        dotfile = dotfile.symlink_to(target)
    # dotfile = dotfile.expanduser().as_posix()
    print(f'\t{colored(SUCCESS_PREFIX)} The file: "{dotfile}" has been symlink --> "'
          f'{colored(target, "green")}"')


def print_source_message(targets_to_source):
    """Receives targets_to_source and instructions for the user to source them """
    print(f'\n3 - OPEN A NEW WINDOW FOR CHANGES TO TAKE EFFECT OR ISSUE THE FOLLOWING '
          f'COMMANDS:')
    for target in targets_to_source:
        print(f'source {colored(str(target), "green")}')
    print("")


def create_row_tables(files_locations, files_targets, files_envs):
    """ Receives files_locations[], files_targets[] and files_envs
    This return a list with all the rows (1 dictionary per row)
    I.E {"ID":1, "Environment": "home", "Location":"", "Target":""}
    Gets encasuplated in:
    table_data[["id", "name", "location", "target", "env"],
               ['row1 column1', 'row1 column2'] ]"""
    HEADERS = ["id", "name", "location", "target", "env"]
    table_data = []
    table_data.append(HEADERS)
    for id, location in enumerate(files_locations):
        name = files_targets[id].strip("~/")
        target = files_targets[id]
        env = files_envs[id]
        rows = [id, name, location, target, env]
        table_data.append(rows)
    return table_data


def print_table(table_data):
    """Gets a list with the following format
table_data = [
    ['Heading1', 'Heading2'],
    ['row1 column1', 'row1 column2'],
    ['row2 column1', 'row2 column2'],
    ['row3 column1', 'row3 column2']
]

+--------------+--------------+
| Heading1     | Heading2     |
+--------------+--------------+
| row1 column1 | row1 column2 |
| row2 column1 | row2 column2 |
| row3 column1 | row3 column2 |
+--------------+--------------+
    """
    HEADERS_C = None
    GLOBAL_C = "yellow"
    HOME_C = "green"
    WORK_C = "cyan"

    id = colored("ID", HEADERS_C, attrs=["bold", "underline"])
    name = colored("NAME", HEADERS_C, attrs=["bold", "underline"])
    location = colored("LOCATION", HEADERS_C, attrs=["bold", "underline"])
    target = colored("TARGET", HEADERS_C, attrs=["bold", "underline"])
    env = colored("ENV", HEADERS_C, attrs=["bold", "underline"])

    colored_headers = [id, name, location, target, env]
    colored_table_data = table_data.copy()
    colored_table_data[0] = colored_headers

    for index, row in enumerate(colored_table_data[1:], start=1):
        env = row[4]
        if env == "globals":
            color = GLOBAL_C
        elif env == "home":
            color = HOME_C
        elif env == "work":
            color = WORK_C

        row_id = colored(str(row[0]), color)
        row_name = colored(str(row[1]), color)
        row_loc = colored(str(row[2]), color)
        row_targ = colored(str(row[3]), color)
        row_env = colored(str(row[4]), color)
        colored_table_data[index] = [
            row_id, row_name, row_loc, row_targ, row_env]

    table = AsciiTable(colored_table_data)
    print(f'\nTABLE: ')
    print(table.table)


def table_to_json_file(table_data,  environments, filename=".db.json"):
    """ This function turns the table_data[headers,row1,row2,...] into JSON and copies it
    to the file defined by filename which is passed by the user via CLI. """
    # headers = ["id", "name","location", "target", "env"]
    # table_data[0] = headers
    headers = table_data[0]
    rows = table_data[1:]
    # table_data[0].append(1) # To test the error next
    if len(headers) != len(rows[0]):
        print(f"{ERROR_PREFIX} headers and rows' lengths are different.")
        exit(1)
    # print(rows)
    db_dict = {"version": 1, "envs": {}}
    for row in rows:
        row_dict = dict(zip(headers, row))
        env_name = row_dict["env"]
        if env_name in environments:
            row_dict.pop('env')
            if env_name in db_dict["envs"].keys():
                db_dict['envs'][env_name].append(row_dict)
                # print(db_dict)
            else:
                db_dict['envs'].update({env_name: [row_dict]})
                # print(db_dict)
    pprint(db_dict)
    db_json = dumps(db_dict, indent=4, sort_keys=True)

    try:
        with open(filename, "w") as f:
            f.write(db_json)
        # return db_json
        db_file = Path(filename).absolute()
        print(f'\n{SUCCESS_PREFIX} The json field has been written to "{db_file}"')
    except Exception as err:
        print(f"{ERROR_PREFIX} {err}")


def main(cli_args):
    # print(cli_args.env)
    selected_env = cli_args.env
    # print(cli_args)
    # input("Test")

    exclusions = get_exclusions()
    # print(f"EXCLUSIONS:\n {exclusions}\n")

    environments = get_envs(exclusions)
    # print(f"ENVS:\n {environments}\n")

    files_envs = get_files_envs(environments, exclusions)
    # print(f"FILE-ENVS:\n {files_envs}\n")

    files_locations = get_files_locations(environments, exclusions)
    # pprint(f"FILE-LOCATIONS:\n {files_locations}\n")

    files_targets = get_files_targets(files_locations)
    # print(f"FILE-TARGETS:\n {files_targets}\n")

    if not selected_env:
        table_data = create_row_tables(
            files_locations, files_targets, files_envs)
        print_table(table_data)

    # selected_env=["globals", "home"]
    if selected_env:
        targets_to_add = get_nonexistent_targets(
            files_locations, files_targets)

        if True in targets_to_add:
            create_targets(targets_to_add, files_targets,
                           selected_env, files_envs)
        else:
            print(f'\n1 - CHECKING IF TARGETS EXISTS IN THE OS\n'
                  f'{SUCCESS_PREFIX} All targets exist in the OS.')

        targets_to_source = process_symlinks(files_locations, files_targets,
                                             files_envs, selected_env)

        if targets_to_source:
            print_source_message(targets_to_source)

    # cli_args.json = "db.json"
    if cli_args.json:
        table_to_json_file(table_data, environments, filename=cli_args.json)


if __name__ == "__main__":
    cli_args = parse_arguments()
    main(cli_args)
