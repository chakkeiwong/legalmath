# eFLINT - Clingo compiler

This repository forks the [haskell implementation](https://gitlab.com/eflint/haskell-implementation) to implement a compiler from eFLINT to Clingo snippets, as per the paper "A Stable Model Semantics for eFLINT Norm
Specifications and Model Checking Scenarios".

This README is tailored for the review process. For more information on the codebase in general, see the [README](https://gitlab.com/eflint/haskell-implementation/-/blob/master/README.md?ref_type=heads) over at the Haskell repository.


## Installation
To prepare your machine to run the compiler, ensure you did the following:
1. Install [Cabal](https://www.haskell.org/cabal/) with the Haskell GHC compiler and such. The easiest way is to install with [GHCup](https://www.haskell.org/ghcup/).

   Please make sure that you manually install a **9.2.x** compiler. You can do so with `ghcup tui` and then follow the interface to install the latest compiler in that series.
2. Ensure you have [Python 3.9](https://python.org) or higher installed.

   Also please make sure that your installation has access to [pip](https://pypi.org/project/pip/) and [venv](https://docs.python.org/3/library/venv.html).


## Usage

### Compiling eFLINT to Clingo
To run the eFLINT Read-Eval-Print-Loop (REPL) with the Clingo compiler built-in, run the following in the repository root:
```bash
cabal run eflint-repl
```
Optionally, you can give an initial (specification) file by supplying it after `--`:
```bash
cabal run eflint-repl -- <FILE>
```

> Note that this step may take a while, as, the first time you run it, it will compile the binary for you first.

This will allow you to interactively supply eFLINT phrases one-by-one. When you're ready to compile the input to Clingo, give the following command:
```bash
:clingo
```
to make the compiler generate the Clingo to stdout.

Due to constraints in the existing interpreter's implementation, this method will _only_ allow you to specify type definitions (e.g., `Fact foo ...` or `Extend Act bar ...`; we refer to this as a _specification_). If you want to provide some postulations (e.g., `+foo.`, `~bar(foo)`, `some-event()`; we refer to these as a _scenario_), write them in a separate file and supply them when executing the `:clingo`-directive:
```bash
:clingo <FILE>
```

For example, you can run one of the tests by supply a specification file as input to the REPL, and a scenario file as input to Clingo:
```bash
> cabal run eflint-repl -- ./tests/clingo/01_deriv_holds.spec.eflint
:clingo ./tests/clingo/01_deriv_holds.same0000.eflint
```

Which should produce the following output:
```plain
state(1).
state(S) :- in(F, S).
state(S - 1) :- state(S), 1 < S.
:- state(S), not 0 < S.
in(F, S + 1) :- in((add, F), S), not in((rem, F), S), state(S + 1).
in((add, F), S + 1) :- in((add, F), S), not in((rem, F), S), state(S + 1).

in((add, (created, X)), S) :- in((create, X), S).
in((rem, (terminated, X)), S) :- in((create, X), S).
in((rem, (created, X)), S) :- in((terminate, X), S), not in((create, X), S).
in((add, (terminated, X)), S) :- in((terminate, X), S), not in((create, X), S).
in((rem, (created, X)), S) :- in((obfuscate, X), S), not in((terminate, X), S), not in((create, X), S).
in((rem, (terminated, X)), S) :- in((obfuscate, X), S), not in((terminate, X), S), not in((create, X), S).
in((holds, X), S) :- in((created, X), S).
in((holds, X), S) :- in((derived, X), S), not in((suppressed, X), S), not in((terminated, X), S).
in((enabled, X), S) :- in((holds, X), S), not in((suppressed, X), S).
in((dutyViolation, X), S) :- in((violated, X), S), in((enabled, X), S).
in((actViolation, X), S) :- in((actTrigger, X), S), not in((enabled, X), S).

in((enum, actor(A)), S) :- state(S) ; in((holds, actor(A)), S).
in((enum, int(A)), S) :- state(S) ; in((holds, int(A)), S).
in((enum, string(A)), S) :- state(S) ; in((holds, string(A)), S).
in((derived, x("hi")), S) :- state(S).
in((enum, x(A)), S) :- state(S) ; in((holds, x(A)), S).

state(1).
```
Finally, you can exit the REPL by typing:
```bash
:q
```

(Remember to run the above commands from the repository's root.)

Alternatively, instead of separately providing the `:clingo`-directively, you can also achieve the above from the command-line by specifying `--clingo <FILE>` as an argument:
```bash
cabal run eflint-repl -- ./tests/clingo/01_deriv_holds.spec.eflint --clingo ./tests/clingo/01_deriv_holds.same0000.eflint
```

If you run the REPL with `--clingo-no-libs`, only the specification/scenario output is generated, not the libraries (see below). For example:
```bash
cabal run eflint-repl -- ./tests/clingo/01_deriv_holds.spec.eflint --clingo ./tests/clingo/01_deriv_holds.same0000.eflint --clingo-no-libs
```
produces
```plain
in((enum, actor(A)), S) :- state(S) ; in((holds, actor(A)), S).
in((enum, int(A)), S) :- state(S) ; in((holds, int(A)), S).
in((enum, string(A)), S) :- state(S) ; in((holds, string(A)), S).
in((derived, x("hi")), S) :- state(S).
in((enum, x(A)), S) :- state(S) ; in((holds, x(A)), S).

state(1).
```


### Benchmark
To run the included benchmarks in `tests/clingo`, you can use the `test-clingo.py` script to do so.

On _Windows,_ run the following commands to create a virtual environment and install the requirements:
```bat
:: From the repository root
python -m venv .\.venv
.venv\Scripts\activate
python -m pip install -r .\requirements.txt
```

On Unix (macOS and Linux), run the following commands instead:
```sh
# From the repository root
python3 -m venv ./.venv
. .venv/bin/activate
python3 -m pip install -r ./requirements.txt
```
Alternatively, on Unix, you can also run `bash ./test-clingo.sh` instead of `python3 ./test-clingo.py` below to do the above automatically before every run if needed. You can give any command as if it was the Python script.

You can run the script with:
```bat
:: Windows
python .\test-clingo.py
```
```sh
# Unix
python3 ./test-clingo.py
# OR
bash ./test-clingo.sh
```

After installation, you can use the script to run  all tests nested in the `tests/clingo`-folder. They follow the following convention:
- Any file ending in `.sameX.eflint` is a _correctness test_ asserting _equality_ (where `X` is an arbitrary number). It contains a scenario which, when combined with a file ending in `.spec.eflint` with the same name, must give the **same** answer for both native and Clingo implementations.
- Any file ending in `.diffX.eflint` is a _correctness test_ asserting _inequality_ (where `X` is an arbitrary number). It contains a scenario which, when combined with a file ending in `.spec.eflint` with the same name, must give a **different** answer for the native and Clingo implementations.
- Any file ending in `.perfX.eflint` is a _performance test_ (where `X` is an arbitrary number). The script will measure the runtime of both implementations running the scenario combined with a specification file with the same name ending in `.spec.eflint`. This is used to generate the benchmarks in the paper.

For every _correctness test_, the script will generate either a `Test OK`-prompt, or a diff that shows the knowledge bases for either implementation as a diff (facts appearing in both knowledge bases appear in both columns; otherwise, they appear only in the knowledge base that generated it). If the code runs- and compiles successfully, you should **only see OK-tests**. There exist various options to tweak the correctness tests:
- `-t <PATH>`/`--test <PATH>`: Test only the test at the given `<PATH>`. If the path is a file, it must be a `.sameX.eflint`, `.diffX.eflint` or `.perfX.eflint`-file that will be executed. If it's a directory, it will be recursively searched to collect those files. Can be given multiple times to do multiple tests at once.
- `-T <TYPE>`/`--types <TYPE>`: Run only `same`, `diff` or `perf` tests. Can be given multiple times to run a combination of those.
- `--correctness`: When given, runs only **correctness tests.** Equivalent to giving `--types same diff`.

For every _performance test_, the script will time the native implementation, a Clingo implementation using only 1 thread and one using one thread for every hardware thread available on your system. There exist various options to tweak the performance tests:
- `-n <N>`/`--n-runs <N>`: Take the average over `<N>` runs instead of 10.
- `-P`/`--strict-perf`: Do not also run correctness tests for benchmarks.
- `-o <PATH>`/`--output-perf <PATH>`: Write the timings to a CSV file at the given `<PATH>`.
- `-e <PATH>`/`--eflint-core <PATH>`: Instead of using the standard Clingo libraries as described in the paper, use the ones given by the file in `<PATH>`. The file is read as a Clingo file and prepended to the output of the REPL with `--clingo-no-libs` (see above). For the paper's appending, the core library in `alternative_core.clingo` is used.
- `-C`/`--clingo-only`: When given, will not time the native implementation but only the Clingo.
- `--performance`: When given, runs only **performance tests.** Equivalent to giving `--types perf --strict-perf`.

More options exist. Use the `--help`-option to see more information.

### Ignored tests
A few tests in this repository are ignored, because they touch upon known issues in the compilation pipeline that will either be added later, or feature a change in semantics. Specifically:
- The tests in [`tests/clingo/dex-dipg/`](./tests/clingo/dex-dipg/) are ignored because the Clingo reasoner fails to find a satisfying model. This probably means there is either a logical contradiction or self-dependency in the spec, which eFLINT can reason around but the stable model semantics can't.
- The tests in [`tests/clingo/individuele-inkomenstoeslag/`](./tests/clingo/individuele-inkomenstoeslag/) are ignored because the Clingo reasoner fails to find a satisfying model. This probably means there is either a logical contradiction or self-dependency in the spec, which eFLINT can reasoner around but the stable model semantics can't.
- The `artikel7.2` tests in [`tests/clingo/afsprakenstelsel-dmi/`](./tests/clingo/afsprakenstelsel-dmi/) because the pipeline somehow generates cyclic aggregators (i.e., an aggregator who's value depends on itself, something impossible to express in eFLINT). This is considered a bug out-of-scope for now.
- Article 7.3 and onwards in [`tests/clingo/afsprakenstelsel-dmi/`](./tests/clingo/afsprakenstelsel-dmi/) are yet untested.


### Standalone
If you're planning to run specifications and scenarios separately with the Clingo implementation, refer to `clingo-standalone.py` that wraps the Python Clingo implementation and our Haskell transpiler to pipe the latter's result into the former. See `python clingo-standalone.py --help` (or `python3 clingo-standalone.py --help` on Unix) for more information.
