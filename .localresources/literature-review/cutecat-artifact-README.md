This is the artifact for ESOP 2025 submission #92 "CUTECat: Concolic Execution for Computational Law"

It has been tested on a Linux machine on Intel x86, which we recommend to avoid
slowdowns. See REQUIREMENTS file for more details.

# Getting started
## Installing and running the docker image

0. Make sure the docker daemon is running. `docker ps` should not return an
   error message.
1. Load the image `docker load -i esop25-ae-cutecat.tar.gz` (this should take
   under a minute)
2. Run the container with
   `docker run -it --name=esop25-ae-cutecat esop25-ae-cutecat:latest`

If you exit the container and want to enter it again, the command above does
not work. In that case, use `docker start -i esop25-ae-cutecat`.

## Smoke test

You can check that the installation works by running in the home:
    `make small`

This will run CUTECat with all optimizations on a small Housing Benefits
example located in
`catala-examples/aides_logement/tests/concolic/simple_nochild_noassert.catala_fr`
This should take a few seconds and output 15 different testcases, and 3
"assertion errors" are found at the end.

Once this works, all commands in "Step-by-step" section below should work too.

## Artifact description

The artifact image is composed of the following:
- In folder `catala`, the OCaml source code for our fork of Catala with
  CUTECat, the concolic engine presented in our paper. The core implementation
  of CUTECat is in `catala/compiler/concolic`.
  This project can be rebuilt and installed with `make install`, and unit tests
  can be run with `make tests`.
- In folder `catala-examples`:
    - `aides_logement` contains the code for the Housing Benefits benchmarks:
        - the files in the folder (and some outside of `aides_logement` are the
          pre-existing source code of the benchmark
        - files in `tests/concolic` contain the harnesses for the benchmarks:
            - `full.catala_fr` is the longest benchmark
            - `large_metropole_apl.catala_fr` is the medium-sized benchmark
              used in the ablation study
            - `simple_nochild_noassert.catala_fr` is the small example of the
              "smoke test"
    - `base_mensuelle_allocations_familiales`, `prestations_familiales`, and
      `prologue_france` are common excerpts of laws that are used in multiple
      examples
    - `impot_revenu` contains the code for the Family Quotient benchmark:
        - `nombre_de_parts.catala_fr` contains the harness for the benchmark used
          in the ablation study
        - other files are the implemented law
    - `smic` contains the code for the SMIC benchmark (French minimum wage):
        - the `smic.catala_fr` file contains the implementation of the law, and
          it is directly analyzed without a harness
    - `us_tax_code` contains the code for the US Tax Code Section 132 benchmark:
        - the `.catala_en` files contain the implementation of the law, and
          `section_132.catala_en` specifically contains a Catala scope
          `QualifiedEmployeeDiscount` that is analyzed
    - `running_example` contains the code for the running example of the paper,
      as well as the fixed version (Fig. 10).
- In folder `scripts`, several scripts used for the experimental evaluation
- In folder `tasks`, files that describe which benchmarks to run with what
  command line options. These are fed to some scripts
- When a make command has been run, a `logs` folder contains the raw outputs
  (stdout and stderr) and the statistics of the corresponding benchmarks,
  except for `make small` which directly prints its output.
- A `Makefile`. Instructions to use it are in the next section.


# Reproducing the experimental evaluation

The experimental evaluation can be run through the `Makefile`, which takes care
of the generation of raw data (running the benchmarks) and the analysis
(building the tables of the paper).

## Description of the `Makefile`

You can choose the parameters of benchmarks depending on your computer:
- The `RUNS` variable describes how many times each benchmark is run (to get a
  mean and standard deviation). Default is 4. The minimum is 2 so that standard
  deviations can be computed.
- The `THREADS` variable describes how many threads will be spawned to run
  separate benchmarks in parallel. Default is 8. It is recommended to make
  `THREADS` a multiple of `RUNS` so that all parallel runs of one benchmark run
  at the same time which reduces the standard deviation. For the most
  significant results, it is recommended that all cores of your CPU have the
  same performance profile.
- To change those variables if needed (not recommended), add `VARIABLE=value`
  after your `make` command. e.g. `make ablation RUNS=6 THREADS=12`

The main `make` targets are described below, with their estimated time. Running
the same targets after they have completed successfully should take almost no
time, since they will be able to print tables without running the benchmarks
again. For instance, `make table2` will run the whole benchmarks the first
time, but can be safely run again instantaneously to show the table again
later. To rerun the target completely, including running the benchmark, use
`make -B TARGET`.

- `make small` runs the small example for the "Smoke test" above
- `make ablation` runs the benchmarks for the ablation study. Running time
  depends on the variables described above. On the machine described in the
  paper (§5), this takes 6h. Expect 8 to 10h on a laptop.
- `make ablation_short` is the same as `make ablation`, but with a smaller
  benchmark for housing benefits. This takes less than 10min.
- `make table1` will generate Table 1 from the paper. This takes a few seconds.
- `make tableN` with `N` from 2 to 5 generates the associated tables. Depends
  on `ablation` or `ablation_short`. If `ablation` or `ablation_short` was run,
  this takes no time.
  Note that those tables may look a little different from their presentation in
  the paper (some lines or columns may be swapped), but they contain all the
  relevant data.
- `make fig12` generates a PDF and PNG version of Figure 12 from the paper
  using matplotlib.
  Depends on `ablation`. If `ablation` was run, this takes a few seconds. Note
  that the PDF may be slow to open on some PDF viewers, so the PNG is
  recommended. To open them, you should first copy the files from the container
  to the host. To do so, run the following from the host:
  `docker cp esop25-ae-cutecat:/home/cutecat/fig12.png .`
- `make fig12_short` works the same as `make fig12`, but after having run `make
  ablation_short`
- `make overhead` computes the overhead described in section 5.3 of the paper.
  It depends on `overhead_generate` which takes 7h, and `overhead_runtests`
  which takes 2.5h, and lastly the script that computes the overhead which
  takes a few seconds.
  Expect 12-15h on a laptop.
- `make overhead_short` is the same as `make overhead` but with a small
  benchmark than the whole housing benefits case study. This takes around an hour.
- `make all` makes the dependencies needed to generate all tables and figures.
  This should take at least 16h. Expect 20-25h on a laptop.
- `make clean` removes all benchmark outputs. This essentially resets the
  container.

## Step-by-step

To reproduce the main claims of the paper, including all tables and graphs,
follow the instructions below. The long version is recommended to run exactly
the benchmarks used for the paper, but a short version is available that shows
results faster but does not run the same housing benefits benchmarks as for the
paper.

### Long version (16-24 hours)
Once the container is up and running (see section "Getting started"):
1. Run `make all` to run benchmarks. This can take from 16h to a day.
2. Run `make tableN` to show Table N from the paper, with N from 1 to 5. These
   are instantaneous.
3. Run `make fig12` to generate Figure 12. Then, from the host, run
   `docker cp esop25-ae-cutecat:/home/cutecat/fig12.png .` to get the image out
   of the container and open it. This takes a few seconds.
4. Run `make overhead` to print the overhead from the paper. This takes a few
   second.

### Short version (1-2 hours)
Once the container is up and running (see section "Getting started"):
1. Run `make all_short` to run benchmarks. This can take 1 to 2 hours.
2. Run `make tableN` to show Table N from the paper, with N from 1 to 5. These
   are instantaneous. For the short version, column "Housing Benefits" from the
   paper is replaced by a smaller benchmark "HB (small)".
3. Run `make fig12_short` to generate Figure 12. Then, from the host, run
   `docker cp esop25-ae-cutecat:/home/cutecat/fig12.png .` to get the image out
   of the container and open it. This takes a few seconds. For the short
   version, this is not expected to look like the graph from the paper, more
   time is spent in the solver on branches that would be explored in a larger
   benchmark.
4. Run `make overhead_short` to print the overhead from the paper. This takes a
   few second. In the short version, this is not the same as in the paper.

### Additional claims
Some additional claims and implementations from the paper are described below,
with commands to run.

# Other claims and references to the paper
In this section, some unit tests (located in `catala/tests/concolic/good`) are
mentioned. You can open the `.catala_en` files to see the code and expected
output, and you can run them with `clerk runtest <filename>`. Clerk is the
build system for Catala.

## Section 3

The pipeline in Fig 9 is implemented in the `catala/compiler` folder, where our
work is in `compiler/concolic`. `interpreter.ml` is the main file, where the
function in charge of each evaluation of the AST with inputs is
`eval_conc_with_input` (calling the recursive function `evaluate_expr`, and the
`concolic_loop` function takes care of calling the solver, the interpreter, and
deciding which path to explore next.
The original concrete interpreter is on `compiler/shared_ast/interpreter.ml`.
Please see https://catala-lang.org/en/doc for more general documentation on the
Catala language.
Unit tests in `tests/concolic` show the behavior of CUTECat on many features of
the language.

The implementation of the running example is in
`catala-examples/running_example`, where a file implements the ambiguous
version, and another file implements the fixed version. They can be run with
`make running_example` and `make running_example_fixed`. CUTECat finds a
conflict error (with the locations of conflicting definitions) in the first
one, and there is none in the second one.

The behavior of CUTECat on lists, to which we give no symbolic encoding yet and
that thus always fall back on concrete interpretation, can be tested with unit
test `catala/tests/concolic/good/list.catala_en`.

## Section 4
### 4.1
Soft constraints are automatically generated for monetary input values, by
function `make_soft_constraints` in `compiler/concolic/interpreter.ml`. They
are tried successively until one is satisfied, by function `fold_softs`.
Their behavior is shown in unit test `tests/concolic/good/soft_groups.catala_en`.

### 4.2
Pattern matching case folding is implemented by function `optimize_expr` in
`compiler/concolic/concolic_optimizations.ml`.

A real example of the situation shown in Fig 11 can be found in
`catala-examples/aides_logement/arrete_2019-09-27.catala_fr`, line 4333. A
simplified version showing the effect of the optimization is in unit test
`tests/concolic/good/match_linearize.catala_en`

### 4.3
Trivial constraint simplification is implemented by function
`remove_trivial_constraints` in `compiler/concolic/concolic_optimizations.ml`.

Incremental solving is implemented in the `IncrementalZ3Solver` module in
`compiler/concolic/interpreter.ml`, as an alternative to the non-incremental
`SimpleZ3Solver` with the same interface.

### 4.4
Lazy evaluation of defaults is implemented in function `count_nonempty_lazy` in
`compiler/concolic/interpreter.ml`, as an alternative to
`count_nonempty_greedy` with the same signature.
The resulting behavior is shown in unit test
`tests/concolic/good/except_conflict_lazy.catala_en`.

Exception reordering is implemented by function `optimize_expr` in
`compiler/concolic/concolic_optimizations.ml`. The resulting behavior is shown
in unit test `tests/concolic/good/packing.catala_en`.

The runtime verification of the DFS invariant is implemented in function
`compare_paths` of `compiler/concolic/path_constraint.ml`, which also
determines the difference between two executions to send it to the incremental
solver.

## 5
### 5.1
Benchmarks are in `catala-examples`, as described in "Artifact description"
above. The step-by-step instructions above explain how to reproduce the tables.

### 5.2
For mutations, a file `tasks/seeds_with_conflicts` contains a list of randomly
generated seeds with which mutation testing generates conflicts.
`make mutations` will run CUTECat for each seed, on a large housing benefits
benchmark with the mutation corresponding to that seed, and stop when it first
encounters a conflict. The result is a list of seeds and found conflicts, that
can then be checked by hand.

To find seeds that generate conflicts, the following command was used:
```
seq 1000000 | shuf | head -n128 | parallel -j8 "catala Concolic --stats --seed={} --disable-warnings --conc-optim=mutation-one-conflict --conc-optim=incremental --conc-optim=lazy-default --conc-optim=trivial --optimize -s Test ~/catala-examples/aides_logement/tests/concolic/large_metropole_apl.catala_fr | head -n100 | grep -q Conflict && echo {}"
```
It generates 128 random seeds between 1 and 1000000, then only prints those that lead to finding a conflict in the first 100 lines of CUTECat output.

### 5.3
The largest housing benefits benchmark is run to generate the overhead
computation `make overhead`. Run `make case_study` to see the (raw JSON)
statistics:
```
{
  "full+surface": {
    "../catala-examples/aides_logement/tests/concolic/full.catala_fr": [
      {
        "steps": 1338575,
        "solve_time": 363.277,
        "eval_time": 23432.155,
        "max_constraints": 185,
        "time": 23896.759,
        "nb_tests": 186390
      }
    ]
  }
}
```
Total time is `time`, solver time is `solve_time`, the number of testcases is
`nb_tests`, and the number of solver calls is `steps`.
The overhead is computed by dividing the total time by the time it took for the
generated tests to be evaluated by the reference interpreter.

To check that CUTECat and the reference interpreter agree on the generated test
cases, one can first observe that none of the errors in the output of the tests
(`logs/concrete/testdir/Test_Test_N.catala_fr.out`) returned an error that was
not accounted for in the corresponding testfile
(`logs/concrete/testdir/Test_Test_N.catala_fr`). Then, because the tests
contain assertions, tests that are not expected to return errors are
automatically verified.

The conflict that CUTECat is able to find in the case study was already found
previously and fixed with an assertion. Removing line 302 in
`catala-examples/aides_logement/prologue.catala_fr` and running `make -B
overhead_generate` should find it after some time.
