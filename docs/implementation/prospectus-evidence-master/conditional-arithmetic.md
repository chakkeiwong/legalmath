# Deutsche conditional arithmetic: derivation and scope

The target is the principal allocation and stated write-up cap in Deutsche Bank
DE000A460DG7 section 5(4), PDF pp.52–55, using the retained German controlling
terms and the adjacent English translation. The source and page bytes are bound
in each E2 dossier. Whole-document legal equivalence remains unchecked.

For reduction, let N be this issue's prevailing principal, O the sum of other
effective instruments participating in the same trigger, and R the externally
determined aggregate capital restoration amount, all in the same currency. The
source requires pro-rata reduction/conversion and caps the aggregate amount by
outstanding participating capital. Thus S=N+O and L=min(R,S). This issue's
conditional allocation is L*N/S, leaving N-L*N/S. Since 0<=L<=S, the allocation
lies in [0,N] and allocation plus remaining principal equals N exactly. N must be
positive. Other ineffective reductions/conversions are excluded, as stated on
p.53; unknown effectiveness is not silently treated as either true or false.

The contractual trigger is strict: CET1 < 5.125%, equivalently a ratio below
41/800. Equality does not trigger under this particular condition. The code
requires R as a premise. It does not derive R by multiplying a ratio deficit by
risk-weighted assets, because accounting, regulatory determinations, foreign
currency and other simultaneous measures are not established by that shortcut.
The actual determination, effective time and notice history remain missing.

For write-up, the displayed p.54 cap is H=J*S/T1. J is the stated annual profit,
S the initial nominal amount of written-down AT1, and T1 the relevant tier-one
capital immediately before write-up. The implementation assumes compatible units
and requires T1>0. Given already allocated distributions D and an independently
established remaining maximum-distributable-amount allowance M, the available
conditional pool is max(0,min(H-D,M)). Those inputs do not establish their own
legal completeness or current regulatory measurement.

Let E be the hypothetical issuer-selected total, n this issue's initial nominal
amount, P the initial nominal amount of the participating write-up pool, and v
its current principal. Under explicit true premises for every implemented
condition and an issuer election, the illustrative addition is
min(n-v,min(E,available_pool)*n/P). Otherwise it is zero; an unknown condition
is rejected rather than encoded as false. The result cannot exceed initial
principal. It does not redistribute a capped issue's unused allocation to other
instruments, determine whether the issuer should elect a write-up, or claim that
the cap is a holder entitlement.

The code additionally requires explicit premises for the subsequent financial
year, no annual loss, no continuing or recreated trigger, regulatory compliance,
pari-passu compliance, and satisfied notice/payment-date requirements. These are
inputs to the conditional scenario, not independently determined legal facts.
Timing, tax/accounting effects, instrument-specific rounding, effective notice,
regulator/issuer determinations and settlement are not implemented here. Actual
event evidence would be required before reporting any realised loss or recovery.

Construction tests compare exact rational allocations independently, check both
sides and equality at the threshold, exclude ineffective capital, enforce currency
consistency and conservation, and show that every write-up condition can veto the
illustration. Passing these checks establishes the stated arithmetic properties;
it does not establish complete contractual implementation or legal accuracy.
