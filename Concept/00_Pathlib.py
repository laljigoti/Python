from pathlib import Path


print(Path.cwd())  # Current working directory


for p in Path().iterdir():
    print(p)  # List all files and directories in the current working directory



phome = Path.home()  # Get the home directory
print(phome)
for p in phome.iterdir():
    print(p)  # List all files and directories in the home directory


Ptest = Path("~/dotfiles").expanduser()  # Expand the ~ to the home directory
print(f"Expanded path: {Ptest}")


P = Path.home() / "dotfiles"  # Join paths using the / operator
print(f"Joined path: {P}")

for p in phome.rglob("*.txt"):  # Recursively search for all .txt files in the dotfiles directory
    print(p)