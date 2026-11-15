from pathlib import Path


#print(Path.cwd())  # Current working directory


#for p in Path().iterdir():
    #print(p)  # List all files and directories in the current working directory



phome = Path.home()  # Get the home directory
#print(phome)
#for p in phome.iterdir():
    #print(p)  # List all files and directories in the home directory


Ptest = Path("~/dotfiles").expanduser()  # Expand the ~ to the home directory
#print(f"Expanded path: {Ptest}")


P = Path.home() / "dotfiles"  # Join paths using the / operator
#print(f"Joined path: {P}")

#for p in phome.rglob("*.txt"):  # Recursively search for all .txt files in the dotfiles directory
  ##  print(p)


#-----------------------------------------------------------------------------------------------------------

# Define the root directory to start searching from and the target string
root_dir = Path(".")  # Current directory, or specify an absolute path e.g., Path("/path/to/search")
givenPath = Path("D:\\IMA\\26_06_2026\\IsOnePLC")  # Example absolute path
search_string = "Edging"  # The string to search for in folder names
filetype = ".TcGVL"  # The file type to filter for

# Search recursively for any path containing the string in its name and filter for directories
matching_folders = [
    path for path in givenPath.rglob(f"*{search_string}*") 
    if path.is_dir()
]

matching_files = [
    path for path in givenPath.rglob(f"*{filetype}") 
    if path.is_file()
]

# Print the resulting folder paths
for folder in matching_folders:
    print(folder)

# Print the resulting file paths
for file in matching_files:
    print(file)

# with open(matching_files[0], "r") as f:
#     content = f.read()
#     print(content)


search_string = "Magazine"

# Open the file and filter lines containing the search string
matching_lines = []
with  open(matching_files[0], "r") as file:
    matching_lines = [line.strip() for line in file if search_string in line]
    lineWithString = [line for line in matching_lines if not line.startswith("//")]

# Print the results

for line in lineWithString:
    print(f"Magazine unit: {line}")
    fountMagazineUnit = line.split(':')[1].split('(')[0].strip()  # Extract the part after ':' and before '('
    print(f"Magazine unit Name: {fountMagazineUnit}")  # Print the extracted magazine unit name
    # print(f"Magazine unit Name: {line.split(':')[1]}")  # Print the part before the '='
    # print(f"Magazine unit Name: {line.split('(')[0]}")  # Print the part before the '='