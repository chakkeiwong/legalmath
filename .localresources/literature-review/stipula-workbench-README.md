# Stipula Full-Stack Project 
This project provides a full-stack environment for generating and analyzing Stipula legal contracts,
featuring a React frontend, a Node.js backend server, and a Python
analyzer.

Prerequisites To run this project, you must have the following
installed on your system: 
  - Node.js & npm 
  - Python 3.x 
  - Java Development Kit (JDK) 19 or later (required  for the Stipula Interpreter).

## Getting Start

Getting Started Follow these steps to set up and launch the entire
application stack.

### Step 1: Initial Setup and Installation (npm install)

Run the following command from the root directory to install all
necessary packages for the entire project (Node.js/npm dependencies).

``` bash
npm install
```

### Step 2: Launch the Application 
Run the launch command:

``` bash
npm start
```

## Stipula Workbench Tool

### How to Run the Editor
1. Enter a name for your contract at the top.  
2. Add assets, fields, and parties using the corresponding input boxes and **Add** buttons.  
3. Define agreements by selecting fields and parties, then click the plus icon to add them.
4. Define the initial status of the contract through the input box under the agreement panel.
5. To create a function, click **New Function** under an agreement, fill in states, parameters, assets, and guards, then click **Add Function**.
6. The contract code updates automatically in the output panel as you make changes. 

Alternatively:
- You can load an existing `.json` contract from your local machine using **Choose File** button.
- You can manually write or edit the contract code using the **Edit** button on the right. 

You can download the project with **Download All** (exports both `.json` and `.stipula`) or **Save Project** (exports only `.json`).

### How to Run the Reachability Analyzer
1. Click:
   1. **Unreachability** to check contract reachability.  
   2. **Unreachability (verbose)** to see a detailed report.  
2. Results will appear in the **Contract Code** panel below.  

### How to Run the Liquidity Analyzer
1. Find the **Liquidity** buttons above the contract code.
2. Choose the __maximum number of times__ a function (and its nested events) can appear within a single abstract computation via the input box next to the buttons.
3. Click:
   1. **Liquidity** to check contract liquidity.  
   2. **Liquidity (verbose)** for a detailed report.  
4. Results will appear in the **Contract Code** panel below.

### How to Run the Interpreter
1. Click Run button.
2. Enter the required data in the dedicated box under the Stipula Interpreter and click the Send button