# A source-motivated date proof extension

The nine retained UCITS readings now have verified qualification records.
Eight are encoded but contain a `date` fact outside the current shared
constructor-preservation profile; one is unencoded. This is a proof-profile
limit. The existing application and targets already support some date
operations, so it must not be described as absence of date execution.

The inspected code uses three representations. `domain.scalar` accepts valid
calendar dates in canonical four-digit `YYYY-MM-DD` form. Java compares those
canonical strings. The Catala adapter converts dates to an exact count of days
since 1970-01-01. Assessment timestamps and evidence-validity intervals are
separate values and operations. A theorem about a date comparison does not
prove which date the regulation intends or which evidence edition applies.

The next extension should first declare the exact supported calendar and
canonical input range, with invalid dates rejected. Define the ordering relation
on valid `(year, month, day)` triples and the intended ordinal encoding. Prove
that canonical representation and ordinal comparison preserve that order in
the stated range. Declare and test leap-year, year-boundary and minimum/maximum
cases; do not infer a calendar from one circular's effective date.

Extend the independent source parser and model encoder only for date literals,
date facts and the existing equality/order operators. Generate the exact source
and target propositions and check them in Lean. Keep unknown/conflict/scope/time
selection separate unless their lifted semantics receive an explicit theorem.
Mutation checks must change a date, reverse a comparison, omit equality at the
boundary, alter the source edition and swap fact identity. An old certificate
must reject each changed proposition.

Then exercise real Java and Catala on independently computed calendar values
under declared mathematical inputs. Boundary examples alone do not prove all
calendar conversions; the formal proposition, parser/codec assumptions and
finite runtime evidence remain distinct. Replay the unchanged eight readings
with their exact questions, retaining pending-application and incorporated-source
premises. A new formal certificate may strengthen a mathematical claim while
the product still qualifies the legal interpretation or declines translation.

No date is invented merely to make the current readings produce an answer.
The current supplementary adapter run selected no runtime cases and reported
zero executions. Any future challenge set, symbolic domain and live interpretation
budget must be declared before execution, with an explicit result artifact and
original-source identity. This note is a concrete next specification, not an
implemented theorem or permission to reset an exhausted investigation.
