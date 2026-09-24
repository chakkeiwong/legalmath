# **Liquidity Analyzer**

## Installation

### Linux
1. Install Python, you can use:
   - Your distro package manager
   - The Python site (https://www.python.org/downloads/)
2. Install Antlr4, you can use:
   - Your distro package manager
   - Open a terminal in the repository directory and run 


    python3 -m pip install -r requirements.txt`

### Windows
1. Install python from the site (https://www.python.org/downloads/)
2. Install Antlr4, open a terminal in the repository directory and run


    python -m pip install -r requirements.txt`

### MacOS
1. Install Python, brew package manager is recommended:
   1. Follow the installation instruction on the brew site (https://brew.sh/)
   2. Open a terminal and run `brew install python@3.11`
2. Install Antlr4, open a terminal in the repository directory and run


    python3.11 -m pip install -r requirements.txt`

## Run

To run an example, open a terminal in the repository directory and run
(use `python3.11` on MacOS or `python` on Windows)

`python3 main.py FILE [-v | --verbose]`

`FILE`: path to your stipula contract to analyze or the path to your contracts folder to analyze all of them.

`-v | --verbose`: option to have a verbose result.

## Stipula-Workbench

It's possible to use the analyzer from the stipula-workbench project with a user-friendly interface and the possibility of creating your own stipula contracts.
(https://github.com/stipula-language/stipula-workbench)

## License
This project is licensed under the GNU General Public License v3.0.
