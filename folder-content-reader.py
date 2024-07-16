import os
from typing import Iterator, Tuple, List, Optional
from collections import defaultdict

def get_dir_info(dir_path: str) -> Tuple[int, int]:
    """
    Get the total size and count of items in a directory.

    Args:
        dir_path (str): The path to the directory.

    Returns:
        Tuple[int, int]: The total size in bytes and the count of items.
    """
    total_size = 0
    item_count = 0
    for root, dirs, files in os.walk(dir_path):
        item_count += len(dirs) + len(files)
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    return total_size, item_count

def walk_directory(dir_path: str, script_name: str, output_file: str) -> Iterator[Tuple[str, os.DirEntry, bool, int, int]]:
    """
    Generator function to walk through the directory structure.

    Args:
        dir_path (str): The current directory path.
        script_name (str): The name of the script to exclude.
        output_file (str): The name of the output file to exclude.

    Yields:
        Tuple[str, os.DirEntry, bool, int, int]: A tuple containing the current path, 
                                                 the os.DirEntry object, a boolean 
                                                 indicating if it's the last entry,
                                                 the size of the file/folder,
                                                 and the count of items for directories.
    """
    entries = list(os.scandir(dir_path))
    entries = [e for e in entries if e.name not in {'.git', '.idea', '__pycache__', script_name, output_file}]

    # Pre-calculate sizes and item counts
    info_cache = {}
    for entry in entries:
        if entry.is_dir():
            info_cache[entry] = get_dir_info(entry.path)
        else:
            info_cache[entry] = (entry.stat().st_size, 0)

    # Sort entries
    sorted_entries = sorted(entries, key=lambda e: (-info_cache[e][1], -info_cache[e][0], e.name.lower()))

    for i, entry in enumerate(sorted_entries):
        is_last = (i == len(sorted_entries) - 1)
        size, count = info_cache[entry]
        yield dir_path, entry, is_last, size, count

        if entry.is_dir():
            yield from walk_directory(entry.path, script_name, output_file)

def get_tree_structure(start_path: str, script_name: str, output_file: str) -> str:
    """
    Generate a string representation of the directory tree structure.

    Args:
        start_path (str): The root directory to start the tree structure from.
        script_name (str): The name of the script to exclude from the tree.
        output_file (str): The name of the output file to exclude from the tree.

    Returns:
        str: A string representation of the directory tree structure.
    """
    lines = []
    prefix_map = defaultdict(lambda: "")

    for dir_path, entry, is_last, size, count in walk_directory(start_path, script_name, output_file):
        depth = dir_path.count(os.sep)
        prefix = prefix_map[dir_path]
        connector = '└── ' if is_last else '├── '
        name_with_indicator = f"{entry.name}{'/' if entry.is_dir() else ''}"
        size_info = f" ({size} bytes)" if entry.is_file() else f" ({count} items)"
        lines.append(f"{prefix}{connector}{name_with_indicator}{size_info}")

        if entry.is_dir():
            new_prefix = prefix + ('    ' if is_last else '│   ')
            prefix_map[entry.path] = new_prefix

    return '\n'.join(lines)

def get_file_contents(file_path: str) -> Optional[str]:
    """
    Read and return the contents of a file.

    Args:
        file_path (str): The path to the file to be read.

    Returns:
        Optional[str]: The contents of the file, or None if the file cannot be read.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def main() -> None:
    """
    Main function to generate the folder contents file.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = 'folder_contents.txt'
    script_name = os.path.basename(__file__)

    folder_name = os.path.basename(current_dir)

    file_info: List[Tuple[str, int, Optional[str]]] = []

    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write(f"### Folder structure:\n")
        out_file.write(f"{folder_name}/\n")
        tree_structure = get_tree_structure(current_dir, script_name, output_file)
        out_file.write(tree_structure)
        out_file.write("\n\n")

        # Collect file information during tree traversal
        for dir_path, entry, _, size, _ in walk_directory(current_dir, script_name, output_file):
            if entry.is_file():
                file_path = os.path.join(dir_path, entry.name)
                file_contents = get_file_contents(file_path)
                if file_contents is not None:
                    file_info.append((file_path, size, file_contents))

        # Sort files by size (descending)
        file_info.sort(key=lambda x: x[1], reverse=True)

        # Write sorted file contents
        for file_path, file_size, file_contents in file_info:
            relative_path = os.path.relpath(file_path, current_dir)
            out_file.write(f"### `{relative_path}` file ({file_size} bytes):\n\n```\n")
            out_file.write(file_contents)
            out_file.write("\n```\n\n")

    print(f"Output written to {output_file}")

if __name__ == "__main__":
    main()

# python folder-content-reader.py