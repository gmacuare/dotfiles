#!/usr/bin/env python3
from argparse import ArgumentParser
from datetime import date
from getpass import getuser
from json import dumps
from pathlib import Path
from pprint import pprint
from random import choice
from shutil import copy
from sys import exit
from termcolor import colored
from terminaltables import AsciiTable
import logging

"""
Logging Structure
[14/02/20]-[14:01:0555]-[root]-[__Main__]-Message 
Define a function to setup logging to DEBUG when passed a parameter form the CLI
"""



""" Usage
./dotfiles.py                           # Prints the DB table by default
./dotfiles.py -j db.json                # Saves the DB to a db.json file
./dotfiles.py -e globals home           # Checks you globals and home folder and symlinks to those files
./dotfiles.py -e globals
"""


ERROR_PREFIX = colored('ERROR:', 'red')
WARNING_PREFIX = colored('WARNING:', 'cyan')
SUCCESS_PREFIX = colored('SUCCESS:', 'green')
HEADERS = ["ID", "NAME", "LOCATION", "TARGET", "ENV"]


def parse_arguments():
    """ Parse all the arguments from the CLI.

    Returns:
        args (argsparse.Namespace): args object. To access values I.E: args.debug"""

    description = "Symnlinks your system's dotfiles to your custom dotfiles"
    parser = ArgumentParser(description=description)

    parser.add_argument("--env", "-e", nargs='+', choices=["globals", "work", 'home'],
                        type=str, metavar="globals home", help="Choose your environment")
    parser.add_argument("--print", "-p", action='store_true', default=True,
                        help="To print the dotfiles DB")
    parser.add_argument("--json", "-j", nargs="?", const="db.json", type=str,
                        help="The DB will be saved in <filename.json> or db.json (Default)")
    parser.add_argument("--debug", "-d", action='store_true', default=False,
                        help="This option enables debug mode")
    args = parser.parse_args()
    return args


def conf_logging(debug):
    """Configures the logger and expects --debug to be passed to override the default
    warning level.
    
    Args:
        debug (bool): To define the debug level, if false (warning), if True(debug)

    Returns:
        logger (logging.Logger): The logger object"""

    log_sev = 'WARNING'
    if debug is True:
        log_sev = 'DEBUG'
    print(debug)
    log_format = '[%(name)s]-[%(levelname)s]-%(asctime)s-[%(funcName)s]-%(message)s'
    datefmt='[%d/%m/%y]-[%H:%M:%S]'
    file='dotfiles.log'

    # File Handler
    logging.basicConfig(format=log_format, datefmt=datefmt, filename=file, level=log_sev,
        filemode="w")
    logger = logging.getLogger(__name__)
    return logger


def get_exclusions():
    """ Reads the .gitignore file and returns a list of files/dirs to be excluded
    
    Returns:
        exclusions (list): With all the file/folders to be excluded in this script"""

    dotignore = ".dotignore"
    try:
        with open(dotignore) as f:
            exclusions = f.read().strip('\n').split("\n")
            logging.debug(f"Exclusions: {exclusions}")
        return exclusions
    except FileNotFoundError as err:
        print(f"{ERROR_PREFIX} The file {dotignore} cannot be found in the current dir")
        logging.exception(
            f"{ERROR_PREFIX} The file {dotignore} cannot be found in the current dir")
        exit(1)
    except Exception as err:
        print(f"{ERROR_PREFIX} General exception {err}")
        logging.exception(f"{ERROR_PREFIX} {err}")
        exit(1)


def get_envs(exclusions):
    """ Creates a list of environments not excluded and return it.

    Args:
        exclusions (list): A list of exclusions defined on the .dotignore file

    Returns:
        environments (list): Environments(dirs not excluded)"""

    all_dirs = [x.as_posix() for x in Path(".").iterdir() if x.is_dir()]
    dirs_excluded = [dirs for dirs in exclusions if dirs.endswith("/")]
    dirs_excluded = [dir_name.strip("/") for dir_name in dirs_excluded]
    logging.debug(f"All Dirs: {all_dirs}")
    logging.debug(f"Excluded dirs: {dirs_excluded}")
    environments = list(set(all_dirs) - set(dirs_excluded))
    logging.debug(f"Environments not excluded: {environments}")
    return environments


def get_files_envs(environment, exclusions):
    """Creates a list of environments associated to each dotfile if the env is not 
    excluded
    
    Args:
        environments (list): Environments(dirs not excluded)
        exclusions (list): A list of exclusions defined on the .dotignore file

    Returns:
        files_envs (list): Included environments associated to each dotfile
    """
    files_envs = []
    for dirs in environment:
        for fls in Path(dirs).rglob(".*"):
            if fls.name not in exclusions and not fls.is_dir():
                files_envs.append(dirs)
    logging.debug(f"files_envs: {files_envs}")
    logging.debug(f"Total elements of files_envs: {len(files_envs)}")
    return files_envs


def get_files_locations(environment, exclusions):
    """Parse the current files locations of each environment and file that is not
        excluded in the .dotignore file

    Args:
        environment (list): All of the environemnts not excluded
        exclusions (list): Files and envs to be excluded

    Returns:
        files_locations(list): Current files' location, excluding files in .dotignore"""

    files_locations = []
    for dirs in environment:
        files_counter = 0
        for fls in (Path(dirs).rglob(".*")):
            if fls.name not in exclusions and not fls.is_dir():
                logging.debug(f"Adding to files_locations: {fls.resolve().as_posix()}")
                files_locations.append(fls.resolve().as_posix())
                files_counter += 1
        logging.debug(f"{files_counter} files were added to files_locations for the"
            f' "{dirs.upper()}/" environment')
    logging.debug(f"Total elements of files_locations: {len(files_locations)}")
    return files_locations


def get_files_targets(files_locations):
    """Gets a lists of files targets. 
    
    Search the first line on each file for a string containing TARGET=<path> I.E 
    TARGET=~/.vimrc. If no TARGET= is present, by default the target will be 
    ~/.<dotfile_name>
    
    Args:
        files_locations(list): Current files' location, excluding files in .dotignore 
        
    Return:
        files_targets (list): Targets where files will be symlinked to on each env"""
    
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
            logging.debug(
                f"File: {files} Custom Target: {target_path} added to files_targets")
        else:
            file_name = Path(files)
            file_name = file_name.name
            file_path = "~/" + file_name
            files_targets.append(file_path)
            logging.debug(
                f"File: {files} Default Target: {file_path} added to files_targets")
    logging.debug(f"files_targets: {files_targets}")
    return files_targets


def get_nonexistent_targets(files_locations, files_targets):
    """Check if the file's target exist and return a list with True if target DOES NOT
    exists or False if the target exists
    
    Args:
        files_locations(list): Current files' location, excluding files in .dotignore 
        files_targets (list): Targets where files will be symlinked to on each env

    Returns:
        targets_to_add (list): Non-existent files in the current OS to be created."""

    targets_to_add = []
    dotfiles = (dict(zip(files_locations, files_targets)))
    logging.debug(f"File Location: Target {dotfiles}")
    for target in dotfiles.values():
        path_target = Path(target).expanduser()
        if path_target.exists():
            targets_to_add.append(False)
        else:
            targets_to_add.append(True)
            logging.debug(f'File: "{target}" will be created on create_targets()')
    logging.debug(f"targets_to_add: {targets_to_add}")
    logging.debug(f"Total elements of targets_to_add: {len(targets_to_add)}")
    return targets_to_add


def create_targets(targets_to_add, files_targets, selected_env, files_envs,
    files_locations):
    """ Creates non-existent files/symlinks only for environments selected via the CLI
    
    Args:
        targets_to_add (list): Non-existent files in the current OS to be created.
        files_targets (list): Targets where files will be symlinked to on each env
        selected_env (list): Environments selected by the user via the CLI
        files_envs (list): Included environments associated to each dotfile
        files_locations(list): Current files' location, excluding files in .dotignore

    Returns:
        None"""

    print("\n1 - CHECKING IF TARGETS EXISTS IN THE OS")
    for index, file_to_add in enumerate(targets_to_add):
        if (file_to_add is True) and (files_envs[index] in selected_env):
            new_file = files_targets[index]
            try:
                Path(new_file).expanduser().touch()
                logging.debug(f"File/Symlink target has been created: {new_file}")
                new_file = colored(new_file, "green")
                print(f"{colored(SUCCESS_PREFIX)} File: {new_file} ---> "
                      f"has been created")
            except PermissionError:
                error_file = colored(new_file, "red")
                username = colored(getuser(), "red")
                error_source = colored(files_locations[index], "red")
                print(f'{ERROR_PREFIX} "{username}" is not allowed to create '
                      f'"{error_file}", try chmod xxx {new_file} or change TARGET= on '
                      f'{error_source}')
                logging.exception(
                    f'{ERROR_PREFIX} "{username}" is not allowed to create '
                    f'"{error_file}", try chmod xxx {new_file} or change TARGET= on '
                    f'{error_source}')   
                exit(1)
            except Exception as err:
                print(f"{ERROR_PREFIX} General exception {err}")
                logging.exception(f"{ERROR_PREFIX} {err}")
                exit(1)

    print(f'{SUCCESS_PREFIX} All targets exist in the OS.')


def filter_dotfiles(files_locations, files_targets, files_envs, selected_env):
    """ 
    Filters all the files depending on the selected env I.E: --env home

    Args:
        files_locations(list): Current files' location, excluding files in .dotignore
        files_targets (list): Targets where files will be symlinked to on each env
        files_envs (list): Included environments associated to each dotfile
        selected_env (list): Environments selected by the user via the CLI

    Returns:
        filtered_dotfiles (dict): {filtered_locations: filtered targets}"""

    selected_env_str = " - ".join(selected_env).upper()
    print(f'\n2 - CHECKING ALL SYMLINKS ON THE ENVS: "{selected_env_str}"')
    env_indexes = []
    
    for index, env in enumerate(files_envs):
        if env in selected_env:
            env_indexes.append(index)

    filtered_locations = [files_locations[index] for index in env_indexes]
    logging.debug(f"filtered_locations: {filtered_locations}")
    logging.debug(f"Total elements of filtered_locations: {len(filtered_locations)}")

    filtered_targets = [files_targets[index] for index in env_indexes]
    logging.debug(f"filtered_targets: {filtered_targets}")
    logging.debug(f"Total elements of filtered_targets: {len(filtered_targets)}")

    filtered_dotfiles = (dict(zip(filtered_locations, filtered_targets)))
    logging.debug(f"filtered_dotfiles: {filtered_dotfiles}")
    logging.debug(f"Total elements of filtered_dotfiles: {len(filtered_dotfiles)}")
    
    return filtered_dotfiles


def check_symlinks(filtered_dotfiles):
    """ Checks if the filtered_targets are correctly symlinked to the filtered_locations

    Args:
        filtered_dotfiles (dict)

    Returns:
        erroneous_symlinks (list) = dotfiles with no symlinks or with erroneous symlinks
        [[target, location, None], [target, location, path_target_str]
"""
    erroneous_symlinks = []
    # Checking if symlinks are correctly linked, if not add them to erroneous_symlinks[]
    for location, target in filtered_dotfiles.items():
        path_target = Path(target).expanduser()
        path_target_str = path_target.resolve().as_posix()
        if path_target.is_symlink():
            if path_target_str == location:
                print(
                    f"{SUCCESS_PREFIX} {target} is linked to the correct location.")
            else:
                print(f"{WARNING_PREFIX} {target} is linked to the wrong location.")
                erroneous_symlinks.append([target, location, path_target_str])
        else:
            print(f"{WARNING_PREFIX} {target} has NOT got a symlink.")
            erroneous_symlinks.append([target, location, None])
    
    logging.debug(f"erroneous_symlinks: {erroneous_symlinks}")
    logging.debug(f"Total elements of erroneous_symlinks: {len(erroneous_symlinks)}")
    return erroneous_symlinks


def print_syml_changes(erroneous_symlinks):
    """ Prints the changes that will be performed (Creating or modifying a symlink)

    Args:
        erroneous_symlinks (list) = dotfiles with no symlinks or with erroneous symlinks
        [[target, location, None], [target, location, path_target_str]
   
    Returns:
        None"""
    
    print(f"\n\t2.1 - FIXING SYMLINKS: The following symlinks will be changed on the env")
    for entries in erroneous_symlinks:
        target = entries[0]
        expected_sym = entries[1]
        current_sym = entries[2]
        print(f"\tFile: {target}\n"
              f"\tFrom --> {colored(current_sym, 'red')}\n"
              f"\tTo   --> {colored(expected_sym, 'green')}\n")
    return None


def fix_symlinks(erroneous_symlinks):
    """ Receives a list with erroneus symlinks [] and ask the use if he/she wants to
    modify the symlink. If any symlink is modified, the original file is first backed up.

    Args:
        erroneous_symlinks (list) = dotfiles with no symlinks or with erroneous symlinks
        [[target, location, None], [target, location, path_target_str]
   
    Returns:
        targets_to_source (list): A list of symlinks targets to be changed. If there are 
        no changes, this function will return None."""

    while True:
        proceed = input(
            "\tWould you like to proceed with these changes(y/n)? ").lower()
        print()
        if proceed == "y" or proceed == "yes":
            targets_to_source = []
            for entries in erroneous_symlinks:
                target = entries[0]
                expected_sym = entries[1]
                path_target_str = entries[2]
                symlink_exists =  False if path_target_str is None else True

                try:
                    original_file = Path(target).expanduser()
                    if symlink_exists:
                        backup_file(src=target)
                        update_symlink(dotfile=original_file, target=expected_sym)
                        targets_to_source.append(str(original_file))
                        logging.debug(f"File: {original_file} added to targets_to_source"
                        )
                    else:
                        update_symlink(dotfile=original_file, target=expected_sym)
                        targets_to_source.append(str(original_file))
                        logging.debug(f"File: {original_file} added to targets_to_source"
                        )
                    continue
                except Exception as err:
                    print(err)
                    logging.exception(f"{ERROR_PREFIX} When creating symlink {err}")
                    exit(1)
            break
        elif proceed == "n" or proceed == "no":
            print(f"\t{colored(ERROR_PREFIX)} EXITING - The symlinks need to be fixed "
                  f"to continue.")
            exit(1)
        else:
            print('\tInvalid answer - press "y" or "n"\n')

    print(f"\t{colored(SUCCESS_PREFIX)} All files have been correctly symlink.")
    logging.debug(f"targets_to_source: {targets_to_source}")
    return targets_to_source


def backup_file(src):
    """Receives a string like ~/.vimrc and creates a backup file like ~/.vimrc-10-10-2020

    Args:
        src (str): I.E ~/.vimrc

    Returns:
        None"""

    src = Path(src).expanduser()
    today = date.today().strftime("%d-%m-%Y")
    today_suffix = f"-backup-{today}"
    backup_file = src.as_posix() + today_suffix
    try:
        copy(str(src), backup_file)
        print(
            f'\tThe file: "{src}" has been backed up at --> "'
            f'{colored(backup_file, "cyan")}"')
        logging.debug(f"File: {src} has been backed up at {backup_file}")
    except Exception as err:
        print(err)
        logging.exception(f"{ERROR_PREFIX} When creating symlink {err}")
        exit(1)


def update_symlink(dotfile, target):
    """ Updates the current symlink to the correct target.
    Args:
        dotfile (str): This is the original file to be updated
        target (str): This is the target to which the dotfile will be symlinnked to

    Returns:
        None"""

    target = Path(target).expanduser()
    if target:
        dotfile.expanduser().unlink()
        dotfile.expanduser().symlink_to(target)

    else:
        dotfile = dotfile.symlink_to(target)

    print(f'\t{colored(SUCCESS_PREFIX)} The file: "{dotfile}" has been symlink --> "'
          f'{colored(target, "green")}"')
    logging.debug(f"File: {dotfile} has been symlinked to: {target}")


def print_source_message(targets_to_source):
    """Prints message advising the user to source the files that have been changed.
    
    Args:
        targets_to_source (list): A list of symlinks targets to be sourced. 

    Returns:
        None

    """
    print(f'\n3 - OPEN A NEW WINDOW FOR CHANGES TO TAKE EFFECT OR ISSUE THE FOLLOWING '
          f'COMMANDS:')
    for target in targets_to_source:
        print(f'source {colored(str(target), "green")}')
    print("")


def create_row_tables(files_locations, files_targets, files_envs):
    """Formats the table rows to be the printed by print_table() 
    
    Args:
        files_locations(list): Current files' location, excluding files in .dotignore
        files_targets (list): Targets where files will be symlinked to on each env
        files_envs (list): Included environments associated to each dotfile

    Returns:
        table_data (List of dicts): Returns a list of dictionaries. Each dict is a row"""

    # HEADERS = ["id", "name", "location", "target", "env"]
    table_data = []
    # table_data.append(HEADERS)
    for id, location in enumerate(files_locations):
        name = files_targets[id].strip("~/")
        target = files_targets[id]
        env = files_envs[id]
        rows = [id, name, location, target, env]
        table_data.append(rows)
    logging.debug(f"table_data: {table_data}")
    return table_data


def print_table(table_data):
    """Prints the dotfiles table

    Args:
        table_data (List of dicts): Returns a list of dictionaries. Each dict is a row
    
    Returns:
        None"""

# THIS NEEDS TO BE DYNAMIC
    HEADERS_C = None
    GLOBAL_C = "yellow"
    HOME_C = "green"
    WORK_C = "cyan"

    # colors = ["yellow", "red", "green", "cyan", "blue", "magenta", "white"]
    # GLOBAL_C = choice(colors)
    # HOME_C = choice(colors)
    # WORK_C = choice(colors)

    # id = colored("ID", HEADERS_C, attrs=["bold", "underline"])
    # name = colored("NAME", HEADERS_C, attrs=["bold", "underline"])
    # location = colored("LOCATION", HEADERS_C, attrs=["bold", "underline"])
    # target = colored("TARGET", HEADERS_C, attrs=["bold", "underline"])
    # env = colored("ENV", HEADERS_C, attrs=["bold", "underline"])

    id = colored(HEADERS[0], HEADERS_C, attrs=["bold", "underline"])
    name = colored(HEADERS[1], HEADERS_C, attrs=["bold", "underline"])
    location = colored(HEADERS[2], HEADERS_C, attrs=["bold", "underline"])
    target = colored(HEADERS[3], HEADERS_C, attrs=["bold", "underline"])
    env = colored(HEADERS[4], HEADERS_C, attrs=["bold", "underline"])
    colored_headers = [id, name, location, target, env]

    colored_table_data = table_data.copy()
    colored_table_data.insert(0, colored_headers)

# THIS NEEDS TO BE DYNAMIC
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
    to the file defined by filename which is passed by the user via CLI. 
    
    Args:
        table_data (List of dicts): Returns a list of dictionaries. Each dict is a row
        environments (list): Environments(dirs not excluded)
        filename (str): The filename to write the table to (JSON serialised).

    Returns:
        None"""


    # headers = table_data[0]
    rows = table_data[1:]
    logging.debug(f"Table Headers: {HEADERS}")
    logging.debug(f"Table rows: {rows}")

    if len(HEADERS) != len(rows[0]):
        print(f"{ERROR_PREFIX} headers and rows' lengths are different.")
        logging.exception(f"{ERROR_PREFIX} headers and rows' lengths are different")
        exit(1)
    
    header_lowcase = [header.lower() for header in HEADERS]
    db_dict = {"version": 1, "envs": {}}
    for row in rows:
        row_dict = dict(zip(header_lowcase, row))
        env_name = row_dict["env"]
        if env_name in environments:
            row_dict.pop('env')
            if env_name in db_dict["envs"].keys():
                db_dict['envs'][env_name].append(row_dict)
                logging.debug(f"Adding: {row_dict} to db_dict")
            else:
                db_dict['envs'].update({env_name: [row_dict]})
                logging.debug(f'Updating Env: "{env_name.upper()}" on db_dict')
    pprint(db_dict)
    db_json = dumps(db_dict, indent=4, sort_keys=True)

    try:
        with open(filename, "w") as f:
            f.write(db_json)
        # return db_json
        db_file = Path(filename).absolute()
        print(f'\n{SUCCESS_PREFIX} The json file has been written to "{db_file}"')
        logging.debug(f'The json file has been written to "{db_file}"')
    except Exception as err:
        print(f"{ERROR_PREFIX} {err}")
        logging.exception(f"{ERROR_PREFIX} {err}")


def main():

    cli_args = parse_arguments()

    conf_logging(debug=cli_args.debug)
    logging.debug(f"CLI ARGS: {cli_args}")
    
    selected_env = cli_args.env

    exclusions = get_exclusions()

    environments = get_envs(exclusions)

    files_envs = get_files_envs(environments, exclusions)

    files_locations = get_files_locations(environments, exclusions)

    files_targets = get_files_targets(files_locations)

    if not selected_env:
        table_data = create_row_tables(
            files_locations, files_targets, files_envs)
        print_table(table_data)

    # selected_env=["globals", "home"]
    if selected_env:
        targets_to_add = get_nonexistent_targets(
            files_locations, files_targets)

        if True in targets_to_add:
            create_targets(
                targets_to_add, files_targets, selected_env, files_envs, files_locations)
        else:
            print(f'\n1 - CHECKING IF TARGETS EXISTS IN THE OS\n'
                  f'{SUCCESS_PREFIX} All targets exist in the OS.')

        filtered_dotfiles = filter_dotfiles(
            files_locations, files_targets,files_envs, selected_env)

        erroneous_symlinks = check_symlinks(filtered_dotfiles)

        if erroneous_symlinks:
            print_syml_changes(erroneous_symlinks)
            targets_to_source = fix_symlinks(erroneous_symlinks)
            print_source_message(targets_to_source)

    # cli_args.json = "db.json"
    if cli_args.json:
        table_to_json_file(table_data, environments, filename=cli_args.json)


if __name__ == "__main__":
    main()