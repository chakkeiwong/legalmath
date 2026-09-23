# eFLINT

Haskell implementation of the eFLINT language, providing an interpreter for exploring normative behaviour, testing normative models and interacting with a normative model for runtime verification and simulation.

Cite as: 
L. Thomas van Binsbergen, Christopher A. Esterhuyse, Tim Müller, _Reflections on the design, applications and implementations of eFLINT, a domain-specific language for legal compliance reasoning_, Journal of Computer Languages, 2026, ISSN 2590-1184, https://doi.org/10.1016/j.cola.2026.101411

## Documentation

#### notebooks
[Jupyter notebooks](https://gitlab.com/eflint/jupyter/-/tree/master/notebooks) are available that explain the features and constructs of the eFLINT language. Note that these are not fully up-to-date with the latest version of the language, eFLINT-4.

#### papers
The following papers describe the design of eFLINT and one or more extensions. Preprints available on [https://ltvanbinsbergen.nl](https://ltvanbinsbergen.nl/publications).

_2026/August_: **Reflections on the design, applications and implementations of eFLINT, a domain-specific language for legal compliance reasoning.** Journal of Computer Languages. L. Thomas van Binsbergen. [[[DOI]]](https://doi.org/10.1016/j.cola.2026.101411)

_2025/July_: **A Stable Model Semantics for eFLINT Norm Specifications and Model Checking Scenarios.** Proceedings of GPCE '25. Christopher A. Esterhuyse, Tim Müller, L. Thomas van Binsbergen. [[[DOI]]](https://doi.org/10.1145/3742876.3742882)  

_2022/January_: **Dynamic generation of access control policies from social policies.** Procedia Computer Science special issue on The 11th International Conference on Current and Future Trends of Information and Communication Technologies in Healthcare (ICTH 2021). L. Thomas van Binsbergen, Milen G. Kebede, Joshua Baugh, Tom van Engers, Dannis G. van Vuurden. [[[DOI]]](https://doi.org/10.1016/j.procs.2021.12.221)

_2020/November_: **eFLINT: a Domain-Specific Language for Executable Norm Specifications.** Proceedings of GPCE '20. L. Thomas van Binsbergen, Lu-Chi Liu, Robert van Doesburg, and Tom van Engers. [[[DOI]]](https://doi.org/10.1145/3425898.3426958) [[[Video]]](https://youtu.be/lQnmTjx9SVg)

_relevant to eFLINT's REPL and its support for "exploratory programming"_:

_2022/December_: **A Language-Parametric Approach to Exploratory Programming Environments.** Proceedings of SLE' 22. L. Thomas van Binsbergen, Damian Frölich, Mauricio Verano Merino, Joey Lai, Pierre Jeanjean, Tijs van der Storm, Benoit Combemale, Olivier Barais. [[[DOI]]](http://doi.org/10.1145/3567512.3567527)  

_2021/August_: **A generic back-end for exploratory programming.** Paper at the International Conference on Trends in Functional Programming (TFP2021). Damian Frölich and L. Thomas van Binsbergen. [[[DOI]]](https://doi.org/10.1007/978-3-030-83978-9_2)  

_2020/October_: **A principled approach to REPL interpreters.** Proceedings of Onward! '20. L. Thomas van Binsbergen, Mauricio Verano Merino, Pierre Jeanjean, Tijs van der Storm, Benoit Combemale, and Olivier Barais. [[[DOI]]](https://doi.org/10.1145/3426428.3426917) [[[Video]]](https://www.youtube.com/watch?v=xP4I2DJKHVQ)

#### implementations

* [Haskell reference implementation](https://gitlab.com/eflint/haskell-implementation)
* [Jupyter kernel](https://gitlab.com/eflint/jupyter)
* [Examples](https://gitlab.com/eflint/eflint-examples)
* [Other open source projects related to eFLINT](https://gitlab.com/eflint)

## Installation

Requires GHC, the glorius Glasgow Haskell Compiler, and Cabal, Haskell's old skool package manager.

We recommend using [ghcup](https://www.haskell.org/ghcup/) to install the appropriate compiler version. As per their website:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://get-ghcup.haskell.org | sh
```
You can proceed with the defaults, or any setting you prefer to change.

When installed (don't forget to restart your terminal to add the binaries to your PATH), run:
```bash
ghcup tui
```
and install the latest GHC 9.2 version. You can do this by navigating down to the GHC tab with the arrow keys, then going down to the latest 9.2 version (9.2.8 at the time of writing) and install it by pressing `i`.

Once the installation completes, you can close the interface (press `q`) and then configure, build and install the project:
```bash
cabal update
cabal configure
cabal build
cabal install
```

When using an older version of cabal (based on build version 1), use `cabal v1-configure` and `cabal v1-build` and `cabal v1-install` instead.

Upon successful installation:

* the executables `eflint-repl` and `eflint-server` are available
* the script `examples/run_tests.sh` should run successfully and produce no output.


### Docker
There is also a Docker version available in case you do not want to install GHC or are running an incompatible version. Using a Docker container is slightly more advanced, though, so this is generally only recommended if you are more experienced with terminals and Docker.

To build the image, run in the root of the repository:
```bash
docker build --tag eflint:latest --file ./Dockerfile .
```
Then, after the command completes, run:
```bash
docker run -it --rm eflint repl
```
to launch the REPL, or
```bash
docker run -it --rm eflint server
```
to launch the server.

Any commands that you want to pass, you can just give after the end of the end of the command above (e.g., `docker run -it --rm eflint repl --debug` will work).

Note, however, that using this method means that, by default, the REPL cannot reach your files. To access them, you have to use a [_Docker Volume_](https://docs.docker.com/storage/volumes/), which maps a certain path in your container to a certain path on your machine. For example, you can do the following:
```bash
docker run -it --rm --volume ./some_local_folder:/container_folder eflint repl 
```
Here, `./some_local_folder` points to a folder on your machine. Docker takes care to map it under `/container_folder` in the container, which means that eflint can access it under that name.

To make it even more concrete, the following example will run the [`old-examples/counting.eflint`](old-examples/counting.eflint) file:
```bash
docker run -it --rm --volume ./old-examples:/examples eflint repl /examples/counting.eflint
```


## Run tests

Execute the script `run_tests.sh` to execute all the tests in folder `tests/`. 
This applies the executable `eflint-repl` (in `--test-mode`) to all the `.eflint` files in `tests/`. 

A test that fails is a test that has queries evaluating to false. All other output by the tool is suppressed.

Input to a test, determining the truth-values of instances of open-types, is provided in a file with the same name but with extension `.eflint.input`.

## Executable `eflint-repl`

Run eFLINT as a REPL.

`eflint-repl <FILE.eflint>` or `eflint-repl`

The scenario in `FILE` is ignored (although this may change in the future).
Once loaded, type `:help` to see the available commands.

## Executable `eflint-server`

### Usage

`eflint-server <FILE.eflint> <PORT> <OPTIONS*>`

with `<OPTIONS>` either:

* `--debug` (increases verbosity of the server)

### Protocol

The `eflint-server` listens to commands on the given `<PORT>`.

If a command is executed successfully this might result in the server updating its internal state.
If this is the case then the response will contain a field `newstate : <INTEGER>`.

---
#### Responses
Responses from the protocol can have one of the following forms.

**Status response**
```
{
    response                 : "success",
    old-state                : <INTEGER>,
    new-state                : <INTEGER>,

    source_contents          : <VALUE*>,
    target_contents          : <VALUE*>,
    created_facts            : <VALUE*>,
    terminated_facts         : <VALUE*>,

    violations               : <VIOLATION*>,
    output-events            : <EVENT*>
    errors                   : <ERROR*>
    query-results            : <BOOL*>

    new-duties               : <VALUE*>,
    new-enabled-transitions  : <VALUE*>,
    new-disabled-transitions : <VALUE*>,
    all-duties               : <VALUE*>,
    all-enabled-transitions  : <VALUE*>,
    all-disabled-transitions : <VALUE*>,
}
```
Where `<VIOLATION*>` is an array of elements of the form:
```
{
    violation : "trigger",
    value     : <VALUE>
}
{
    violation : "duty",
    value     : <VALUE>
}
{
    violation : "invariant",
    invariant : <STRING>
}
```
A `<VALUE>` is either an `<ATOM>` of the form
```
{
    tagged-type : <STRING>,
    fact-type   : <STRING>,
    value       : <STRING>|<INTEGER>,
    textual     : <STRING>
}
```

or a `<COMPOSITE>` of the form

```
{
    tagged-type : <STRING>,
    fact-type   : <STRING>,
    value       : <VALUE*>
    textual     : <STRING>
    
}
```
and `<VALUE*>` is an array of values.

**Facts response**
```
{
    values : <VALUE*>
}
```
**Path response**
```
{
    edges : <EDGE*>
}
```
Where `<EDGE*>` is an array of elements of the form:
```
{
    phrase                   : <STRING>,
    source_id                : <INTEGER>,
    target_id                : <INTEGER>,

    source_contents          : <VALUE*>,
    target_contents          : <VALUE*>,
    created_facts            : <VALUE*>,
    terminated_facts         : <VALUE*>,

    violations               : <VIOLATION*>,
    output-events            : <EVENT*>
    errors                   : <ERROR*>
    query-results            : <BOOL*>

    new-duties               : <VALUE*>,
    new-enabled-transitions  : <VALUE*>,
    new-disabled-transitions : <VALUE*>,
    all-duties               : <VALUE*>,
    all-enabled-transitions  : <VALUE*>,
    all-disabled-transitions : <VALUE*>,
}
```
**Head/Leaf nodes response**
```
{
    state_id             : <INTEGER>,
    state_contents       : <VALUE*>,
    duties               : <VALUE*>,
    enabled-transitions  : <VALUE*>,
    disabled-transitions : <VALUE*>,
}
```
**Exported graph response**
```
{
    current : <INTEGER>
    nodes   : <GRAPH_NODES*>,
    EDGES   : <GRAPH_EDGES*>
}
```
Where `<GRAPH_NODES*>` and `<GRAPH_EDGES*>` are JSON objects of the nodes and edges in the current graph.

**Loaded graph response**
```
{
    response  : "success"
}
```
**Killed response**
```
{
    response  : "bye world..."
}
```
**Invalid revert response**
```
{
    response   : "invalid state"
}
```
**Invalid command response**
```
{
    response   : "invalid command"
}
```
**Invalid input response**

Any input that does not follow the format discussed in the **Commands** section will be rejected by the server, responding with
```
{
    response  : "invalid input"
}
```
**Field description (make one for every response or make this universal?)**

| field | meaning |
| ------ | ------ |
| old-state | the number identifying the previous state the server was in |
| new-state | the number identifying the state the server is currently in |
| source_contents | the list of `<VALUE>` that exist in the previous state|
| target_contents | the list of `<VALUE>` that exist in the designated/next state|
| created_facts | the list of `<VALUE>` that exist in the designated/next state but not in the previous state|
| terminated_facts | the list of `<VALUE>` that exist in the previous state but not in the designated/next state|
||
| violations | the duty violations, invariant violations, or non-compliant/disabled actions and events that were caused by the command that receives this response |
| output-events | the list of output events (executed-transition) TODO|
| errors | the list of errors (non-deterministic transition/disabled transition/compilation error) TODO|
| query-results | the list of query results (True/False) TODO|
||
| new-duties | the new duties brought into existence by the command that receives this response |
| new-enabled-transitions | the actions and events that can be triggered and will not cause a violation which were disabled in the previous state  |
| new-disabled-actions | the actions and events that cannot be triggered or cause a violation when triggered which were enabled in the previous state |
| all-duties | the duties present in the current state |
| all-enabled-transitions | all actions and events that can be triggered and will not cause a violation  |
| all-disabled-actions | all actions and events that cannot be triggered or cause a violation when triggered |
| old-state | the number identifying the previous state the server was in |
| new-state | the number identifying the state the server is currently in |
||
| phrase | a string that was executed as a phrase to create the corresponding edge |
| source_id | the number identifying the previous state of an edge |
| target_id | the number identifying the next state of an edge |

---

#### Commands
Valid commands have one of the following forms.

##### Status report
The `eflint-server` can check the status of the server by retrieving the last edge to the current state of the server.

```
{
    command : "status"
}
```
If the server is ready and waiting for further commands, it will respond with information about its current state with a **Status response**

##### Killing the server
The `eflint-server` can kill a server with the following form:
```
{
    command : "kill"
}
```
The server will gracefully terminate with a **Killed response**

##### Facts
The `eflint-server` can return all the facts in the current state using the following form:
```
{
    command : "facts"
}
```
A successful request will respond with a **Facts response**.

##### Types
The `eflint-server` can return all the types declared in the current state using the following term:
```
{
    command : "types"
}
```
The response is an object mapping the name of a type to the declaration of the type matching the internal representation of the declaration.

A variant of the above is the command "physical-acts" that returns all the (act-types) that are declared using the physical keyword.
```
{
    command : "physical-acts"
}
```

##### Path
The `eflint-server` can return all the edges between the current state and the root state. If an <INTEGER> is provided for the value in the request form, the `eflint-server` will return all the edges between the current state and state assocciated with the provided <INTEGER>. A history request is in one of the following forms:
```
{
    command : "history",
    value   : <INTEGER>
}
{
    command : "history"
}
```
A successful request will respond with a **Path response**.

##### Leaf nodes/head nodes
The `eflint-server` can return all the leaf nodes of the execution graph/server using the following form:
```
{
    command : "trace-heads"
}
```
A successful request will respond with a **Head/Leaf nodes response**.
##### Executing phrases
The `eflint-server` can send and execute arbitrary phrases to the server, in the textual format accepted by `eflint-repl` (see the relevant documentation in the section "Executable `eflint-repl`") using the following form:
```
{
    command : "phrase",
    text    : <STRING>
}
```
The response can be that of a **status response**, **Invalid input response**, or **invalid command response**

##### Backtracking
The `eflint-server` can backtrack to one of its previous states (configurations), triggered by a command of the form:
```
{
    command     : "revert",
    value       : <INTEGER>,
    destructive : <BOOL>
}
```
The provided `<INTEGER>` should be a positive number previously been sent as part of a response or be a negative number, in which case the server will revert to its initial state. A successful backtrack will respond with a **Status response** in the new state, or a **Invalid revert response** when it fails. The `destructive` field determines whether the revert is intended to remove nodes from the execution graph while backtracking. This field is optional (the default is false).
##### Creation and termination events
The `eflint-server` can create or terminate `<VALUE>` instances using the following forms:
```
{
    command   : "create",
    value     : <VALUE>
}
{
    command   : "terminate",
    value     : <VALUE>
}
```

An event either fails because the provided value is not a value in the normative model or succeeds, resulting in a new state. A successful creation or termination will respond with a **Status response**, or an **Invalid input response** when it fails.


##### Queries
The `eflint-server` can query `<VALUE>` instances whether they are present, absent, or enabled  using the following forms:
```
{
    command   : "test-present",
    value     : <VALUE>
}
{
    command   : "test-absent",
    value     : <VALUE>
}
{
    command   : "enabled",
    value     : <VALUE>
}
```

A query either fails because the provided value is not a value in the normative model, or succeeds because it is present or absent. A successful query will respond with a **Status response**, or an **Invalid input response** when it fails.

##### Actions & Events
The `eflint-server` can execute an action request in one of the following forms:
```
{
    command     : "action",
    act-type    : <STRING>,
    actor       : <STRING>|<VALUE>,
    recipient   : <STRING>|<VALUE>,
    objects     : <(STRING|VALUE)*>,
    force       : "true"|"false" //default is false
}
{
    command     : "action|event",
    value       : <VALUE>,
    force       : "true"|"false" //default is false
}
```
An invalid action may occur if the fields do not constitute a valid action according to the server's normative model (e.g. based on type-checking). The error contains a message indicating what went wrong (structure not specified). A successful action will respond with a **Status response**, or an **Invalid input response** when it fails.
