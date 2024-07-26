import os
import re
from typing import Iterator, Tuple, List, Optional
from collections import defaultdict
import concurrent.futures

def get_dir_info(dir_path: str) -> Tuple[int, int]:
    total_size = 0
    item_count = 0
    for root, dirs, files in os.walk(dir_path):
        item_count += len(dirs) + len(files)
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)
    return total_size, item_count

def walk_directory(dir_path: str, script_name: str, output_file: str, excluded_formats: List[str]) -> Iterator[Tuple[str, os.DirEntry, bool, int, int]]:
    entries = list(os.scandir(dir_path))
    entries = [e for e in entries if e.name not in {'.git', '.idea', '__pycache__', script_name, output_file}]
    info_cache = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_entry = {executor.submit(get_dir_info, entry.path) if entry.is_dir() else executor.submit(lambda: (entry.stat().st_size, 0)): entry for entry in entries}
        for future in concurrent.futures.as_completed(future_to_entry):
            entry = future_to_entry[future]
            info_cache[entry] = future.result()
    sorted_entries = sorted(entries, key=lambda e: (-info_cache[e][1], -info_cache[e][0], e.name.lower()))
    for i, entry in enumerate(sorted_entries):
        is_last = (i == len(sorted_entries) - 1)
        size, count = info_cache[entry]
        yield dir_path, entry, is_last, size, count
        if entry.is_dir():
            yield from walk_directory(entry.path, script_name, output_file, excluded_formats)

def get_tree_structure(start_path: str, script_name: str, output_file: str, excluded_formats: List[str]) -> str:
    lines = []
    prefix_map = defaultdict(lambda: "")
    for dir_path, entry, is_last, _, _ in walk_directory(start_path, script_name, output_file, excluded_formats):
        depth = dir_path.count(os.sep)
        prefix = prefix_map[dir_path]
        connector = '└── ' if is_last else '├── '
        name_with_indicator = f"{entry.name}{'/' if entry.is_dir() else ''}"
        lines.append(f"{prefix}{connector}{name_with_indicator}")
        if entry.is_dir():
            new_prefix = prefix + ('    ' if is_last else '│   ')
            prefix_map[entry.path] = new_prefix
    return '\n'.join(lines)

def get_file_contents(file_path: str) -> Optional[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None

def process_file(file_info: Tuple[str, int, str], current_dir: str, excluded_formats: List[str]) -> Optional[str]:
    file_path, _, file_contents = file_info
    relative_path = os.path.relpath(file_path, current_dir)
    file_extension = os.path.splitext(file_path)[1][1:]  # Get the file extension without the dot
    if file_extension not in excluded_formats:
        return f"### `{relative_path}`:\n```{file_extension}\n{file_contents}\n```\n"
    return None

def process_output_file(file_path: str) -> None:
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    # Remove \r characters
    content = content.replace('\r', '')
    # Replace multiple newlines with a single newline
    content = re.sub(r'\n+', '\n', content)
    # Replace whitespace followed by multiple newlines with a single newline
    content = re.sub(r'\s+\n+', '\n', content)
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def main() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = 'prompt_template.md'
    script_name = os.path.basename(__file__)
    folder_name = os.path.basename(current_dir)
    excluded_formats = ["bat", "txt", "md", "csv", "map"] # exclude the listed formats
    file_info: List[Tuple[str, int, Optional[str]]] = []
    
    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write("# Context:\nCONTEXT_STATEMENT.\n")
        out_file.write("# Codebase:\n")
        out_file.write(f"## Folder Contents:\n")
        out_file.write(f"### Folder structure:\n")
        out_file.write(f"```\n{folder_name}/\n")
        tree_structure = get_tree_structure(current_dir, script_name, output_file, excluded_formats)
        out_file.write(tree_structure)
        out_file.write("\n```\n")
        out_file.write("## File Contents:\n")
        
        # Collect file information
        for dir_path, entry, _, size, _ in walk_directory(current_dir, script_name, output_file, excluded_formats):
            if entry.is_file():
                file_path = os.path.join(dir_path, entry.name)
                file_info.append((file_path, size))
        
        # Sort files by size in descending order
        file_info.sort(key=lambda x: x[1], reverse=True)
        
        # Read file contents concurrently and store results
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(get_file_contents, fi[0]): fi for fi in file_info}
            results = []
            for future in concurrent.futures.as_completed(future_to_file):
                file_path, size = future_to_file[future]
                file_contents = future.result()
                if file_contents is not None:
                    results.append((file_path, size, file_contents))
        
        # Sort results by file size in descending order and write to file
        results.sort(key=lambda x: x[1], reverse=True)
        for file_path, size, file_contents in results:
            processed_file = process_file((file_path, size, file_contents), current_dir, excluded_formats)
            if processed_file:
                out_file.write(processed_file)
        
        out_file.write("# Problem:\nPROBLEM_STATEMENT.\n")
        out_file.write("# Task:\nTASK_STATEMENT. Lets 1. understand task and mental contrast potential issues, 2. make detailed to-do list, 3. devise detailed plan to complete task. Then lets take deep breath, carry out plan, and do task step-by-step. Write full code but replace unchanged parts with comments\n")
        out_file.write("# Task:\nTASK_STATEMENT. Lets 1. understand problem and mental-contrast issues, 2. make detailed to-do list, 3. devise detailed plan to solve problem. Then lets take deep breath, carry out plan, and solve problem step-by-step. Write full code but replace unchanged parts with comments")
    
    # Process the output file
    process_output_file(output_file)
    print(f"Output written to {output_file}")

if __name__ == "__main__":
    main()