# Autoresearch: learn Getting Over It in the original game

## Authority and objective

The user delegated research, implementation, operations, and experiment
decisions, with no further decision questions, on 2026-10-04. Continue across
scheduled invocations until independently verified completion, interruption,
or a real access, safety, or spending blocker. CPU Upgrade is authorized;
CPU XL is also authorized **after** the current pilot completes, if measured
capacity or elapsed-time needs justify it. Larger hardware is not a remedy
for a failed control or exploration design.

This is a long-running research goal, not a claim that success is guaranteed.
The scheduled operator and remote worker are separate: the worker executes
bounded batches; the operator examines evidence and selects the next batch.

## Physical success, not reward optimization

Primary metric: **worst-seed reference full-climb completion fraction**, higher
is better, for the best variant with all declared training seeds completed.
At least three distinct training seeds are required. Record first-ledge holds,
retained altitude, deaths, real game ticks, sample/update counts, wall time,
resource use, and compute cost independently.

A candidate requires nominal full completion in every training seed and
at least 80% completion in the nine declared reference cases per seed
(at least 8/9). Final success additionally requires:

- Independent held-out legal warm-ups/action-noise streams, at least 20 cases
  per seed, with at least 80% completion and a nominal completion for every
  seed. These cases must be declared before evaluating the chosen checkpoint.
- Fast/reference agreement covering its learned upper-route contact sequence.
- The original summit condition, body world Y >16000, on a continuous legal
  trajectory from the ordinary starting terrain. No placement, altered gravity,
  or fabricated collision geometry may count as learning evidence.
- A saved model, matching frozen normalizer, dependency/source/asset
  fingerprints, legal action trace, and replayable reference completion.

Structured perturbations are not IID physical worlds. Do not make binomial
confidence claims from their success fractions. MAD experiment comparisons
are advisory, not a substitute for independent training-seed replication.
`tools/research_goal_metrics.py` deliberately never declares the final goal
verified from standard campaign aggregation alone.

## Current result: memory-aware hammer goal completes26steps, body acquisition untested

Added ONLYopt-in `cursor_feedback=True` to `HammerTargetPhase`; default
contract/actions/observe summaries unchanged, all30historical defaultsteps/
backend exact beforephysics. Bootstrap once from last actuallyissued prefix
command and actualpostraw217; nextpre mustequal thatpost. Eachactualpost
updates estimate=rawpointer13/14*128 minus OWNissuedfloat32command*128,
never uncompensateddesiredpointer. Returned/bootstrap inputs copied; pending/
prepost/invalidmode/legalcommand/duplicatebootstrap/timeout/no rearm guards.
Goal/reach/axes/offset/tolerance1/cap30unchanged; illegalcompensationfails,
no clipping/filter/gain/seed/currentfuture noise oracle.14phase/55focused/
344fullPython+JS pass. Fullsuite flushwarnings are expectedfaultinjection.

Frozen6rollout implementation smoke: nominal600historical gate, known
ordinary299prefix/reset14001/noise13105 defaulttargetphase versusoptin,
allactualcontrols withsamecontinuousnoise; variableearlystop/equalmax329
declared. Goalstage basephase298/calls299staysfrozen, no laterplayback.

| Reference targetphase | Steps | Physical tiperror | Final body / gain |
|---|---|---|---|
| Defaultuncompensated |30timeout|3.304582|(268.882791,32)/11|
| Opt-inpastcursorfeedback |26success|.870482|(268.844997,32)/11|

Candidate rawtiperror.870480, actualmotion, alive; localrawANDphysical1pixel
completiongate true. Stopscontrolled325, default329. Body NOT reference-
aligned andneithercontrastarmholdsledge;0deaths/summits/updates. This is
singleknownstate hand-designed localcompletion, not robustteacher/corpus/
learning/bodyrecovery. Default30failure andclosedpulse751/fresh8/9strict
failures immutable; no retrospectiveextensionor tolerance relaxation.
Only causalphasecontroller DESIGN admitted after this completion.

2508control+720reset/6rollouts,owned30.222317seconds within180work/210owned
caps. Source/newmode/prior/cursoradmission/plan/scripts/parent/budget/deadline/
secret-stripped ownedchild/durabletrace/cleanup bound. Independentall6raw
metric/control/caseclock/actionobserve/memory histories and3fullbackendpairs
exact. All4nominal/defaultFULLhistoricaltraces unchanged; both newfirst300
physicalhistories reproducecursorcontrast. Equal299prefix/actualpreinputs,
eachpostestimate subtracts ownissuedaction, baseclock frozen verified.
Evidence: `artifacts/cursor_feedback_smoke_20261005_v1/verification.json`.

Independently privatePAUSED1791168305.4767606;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no paidreservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

Next admitted bounded IMPLEMENTATION/design+smoke: a causal one-attempt
source-clock wrapper around unchangedcontactprior, raw217/owncommandhistory/
resettableprivatephase only. Singlecheckpoint beforecontrolleddecision300
after299actualobservedsteps; lowerplantedhammer predicate:
rawprevioushammerqueryhit==1,lasttravel<3,hammerworldY<fixedrow300goalY-1,
legalgoalreach26..102/axes128. No case/seed/traceoracle. Ineligiblecheckpoint
permanentbypass/exactoriginal. Eligiblecase uses unchangedfixedgoal/optin
cursorphase/tolerance1/max30steps; bootstrappreviousactuallyissuedcommand.
On firstactualgoalaction consume ONE baseprior phase299 via its ordinary
proposalcall, explicitlyignored/overridden; basecalls300/sourcephase299
thenfreeze throughgoalstage, NOT tied to additionalphysicalgoalsteps.
Afteractualgoalcompletion resume nextorderedbasephase300; no arbitrary
phasejump, backtracking, repeat/rearm, extra goal or terminalmacro.
Fail/timeout terminal. Preserve globaloneaction/actualpostobserve/prepostlink/
privateclocks/max751controls, and firstgoal actualphysics current325history;
baseproposal/sourceclock metadata difference explicit, ignoredproposal not
teacherlabel. This is a controller design, not alreadyprovenbodyrecovery.
Tests/default/bypassparity first, freezeactualsource/rule/plan/deadline
beforeknowncase nominal/failed13105 originalphysicssmoke onreferencefast:
4rollouts/max3004control+480reset/180work/210ownedseconds. Nominal must
bypassexactall751originalcontrols/physics; prefix299 andgoalphysical325exact,
allbackend/rawmetrics. Require candidate originalcentralheld ANDfinal90
central/speed2/bodyfraction.8/nodeaths before broaderwrapper validation.
Secondaryreportednot substitute; goalcompletionalone notacquisition.
No laterpriorplaybackduringgoal or blindphysical-clockadvance, target/gain/
noise/cap/tolerance/cutoffscans, closedplanretry/9case rewrite, labels or
learning. Any latercomposition/freshwholevalidation/captureddata/clock-
memorylearnercontract remainsseparate; no unchangedBC/PPO scaling.

## Prior result: causal cursor alignment passes, hammer error slightly worsens

Frozen6rollout one-step cursor-response comparison completed. Nominal600
historicalgate, then exact299ordinary originalcontrollerprefix/reset14001/
noise13105, uncompensatedsameworldgoal versusunitpastobservedcursor-error
subtraction at300. Equal299fullphysics/controls AND actualraw217pre/full
prestate. Samecontinuousnoise; no seed/currentappliedaction/future noise
in estimator. Firsttargetaction fixed, no stableblock/errorminimum selection.

| Reference one-step measure | Uncompensated | Past-cursor compensated |
|---|---|---|
| Actualcursor error toCOMMONdesiredpointer |1.137445398|.000703795|
| Hammer-world targeterror |11.145062381|11.265576588|
| Hammer travel |4.474497014|4.715062720|
| Hammer queryhit |false|false|

Declaredcursoralignmentgate true, but HAMMERerror worsensslightly. This
cannot be promoted as hammertracking/completion/recovery/learning progress.
Incrementalhammer(-.3712,-.2632), bodydelta(0,0), no lift orhold.
Pastestimate(.927917480,.658210754) fromrawprepointer13/14*128 minus
previousactuallyissuedowncommand; currentseed/noise/post notreadbypredictor.
Uncompgoalpointer andsourceprior remainfixed; candidatefloat32action
(-.663948357,-.430981845) legal. Originalmotionrequestgain0.4consistent
withlocalcursorchange, not completegravity/contactsolver inversion.

2400control+720reset/6rollouts,owned31.341925seconds within180work/210owned
caps.49focusedPython+JS safeguards pass, controller/physics/metrics unchanged.
All6rawmilestone/proposed/applied/caseclock histories,3fullbackendpairs,
nominal600/uncompensated300sourcehistories/equal299prefix/preinputs exact.
Source/prior/proposal/completedaudit/plan/scripts/parent/budget/deadline/
secret-stripped ownedchild/durabletraces/cleanup verified.0updates/deaths/
summits/labels/completion/recoveryadmission. Only separatecausalfeedback
implementation/smoke admitted, not anotherfullpolicy or teacher.
Evidence: `artifacts/cursor_response_probe_20261005_v1/verification.json`.
Closeduncompensated1pixel/30stepfailure3.304582 and allpriorgates preserved.

Independently privatePAUSED1791166955.9553962;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no reservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

The historical admitted bounded IMPLEMENTATION/smoke added opt-in past-cursor feedback in
the boundedhammer-target phase, defaultuncompensated behavior exact.
State ONLYraw217pre/post, fixedgoal and ownactuallyissuedcommand history.
Bootstrap once from last actuallyexecuted prefixcommand and its observedpost;
aftereachstep estimate=actualpostrawpointer*128-OWNcommand*128 (not prior
uncompensateddesiredcommand). Nextaction subtract that estimate withunitgain.
Explicit action/actualpostobserve/prepostlink, rejectmissing/wrong/duplicate
history, no first-step seedoracle or recurringbootstrap. Legalaxes/reach
guards; samegoal/offset/1pixel/30steps/no rearm orcaprenewal. No filters/gain/
noise/tolerance/goal/cutoff scan. Preservealloldactions/contracts bydefault.
Freeze source/rules/plan before actualpipeline-smokephysics. Nominal600
gate, knownordinary299prefix/noise13105/reset14001, defaulttargetphase versus
optinfeedbackphase onreferencefast,max6rollouts/2516control+720reset/
180work/210ownedseconds, variableearlystop declared. Default6available
priorhistories/sourceprefixes exact; candidatefirst300mustreproducecurrent
cursorcontrastphysically. Require raw ANDphysicaltiperror<=1/actualmotion/
alive/fullfidelity for localtargetcompletion; otherwise preservefailure.
Cursoralignmentpass alone notcompletion/bodylift. Even localcompletion
only admits further causalphase DESIGN; recovery/composition/freshwhole
validation and captureddata/clock-memorylearnercontract remain separate.
No substantivelearning, paidscaling, targetretry ofoldclosedplan or labels.

## Prior result: offline pointer audit supports causal lagged-cursor local test

Frozen180second OFFLINE audit completed on6savedtraces/2516rows from failed
observedtargetphase,0newplay/reset/updates. Trace/source/project/completed
review/script/plan/budget hashes verified; all3fullbackendpairs exact,
30targetstep pointer/error/servo arithmetic independentlyreconstructed.
Original1pixel/30stepfailure remains3.304582physicalerror/nohold/gain11;
no player/learnedpolicy improvement or teacher admission from audit.

All30posthammer queriesfalse,29pre+postbothfalse; stagegoalreach86.488407..
90.864862 within26..102, renderoffset always0,20. Pre-stateunclampedmotor
requestmax7.411530<50, slewchangemax15.934812<40. These simplecomputed
requests don't show cap pressure; they are not fullinternal branch/force
observations. OriginalGravity executes BEFOREmotor; naiveprestate0.4motor
prediction differs fromactualhammerdelta byup to4.707578 inquery-free steps.
So do not claim cursor noise is the onlycause or freequery guarantees a
linearservo. Sourceorder/motor/limits excerptsverify independently.

Actualrawpointer13/14 matchesphysicalpointer within3.78418e-6pixels
across2516rows. Actualcursor-command residual mean norm4.583581pixels.
Strict causal ONE-step-lag estimate=currentpre rawpointer*128 minus previous
actuallyissued owncommand*128. Predictor uses only previousactualpost and
owncommand, no currentappliedaction/post/noise_seed/metadata/future noise.
Descriptiveestimate-currentresidual mean1.488157/max9.968753pixels,
22/30errors<.002pixel. Estimate becomesstale when disturbancechanges.
No claim thispredicts allfuture noise or reconstructs any changed trajectory.
All30counterfactualunit-subtractioncommandslegalonRECORDEDinputs only.
Physicalminimumtiperror2.140451/final3.304582; no passedcompletion.

Derived ONE proposal atFIRSTdeclaredtargetaction300, not chosenbystable
blocks/lowesterror: pastestimate(+.927917480,+.658210754) subtractfrom
uncompensatedpointer(-84.057472229,-54.507465363) gives
(-84.985389709,-55.165676117),float32action(-.663948357,-.430981845).
Gain1unit residual subtraction, no filter/gain/clock/target scan. Independent
scalar raw-pointer/own-action arithmetic verifies; originalGravity-before-
motor excerpt retained. Command is not executed/simulated; realtip/body
effect or goalcompletion not inferred. Laterboundedproposal/source review
did not rerun audit or extend its originaldeadline.
Evidence: `artifacts/tracking_audit_20261005_v1/verification.json`,
`causal_cursor_feedback_proposal.json`, `proposal_verification.json`.

Independently privatePAUSED1791165658.0955834;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no paidreservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

The historical admitted separately frozen ONE-step actualcursor
response comparison, nominal600historicalreferencefast gate then
ordinary299prefix/reset14001/noise13105 with uncompensatedsameworldgoal
versusoneunit pastobservedcursor-residual subtraction at300.6rollouts/
max2400control+720reset/180work/210ownedseconds. Equalactualprestate/full
prefix and allbaseline/history/backend/rawmetric fields mandatory.
Require strictlylower actualcursor error relative to the COMMONdesired
goal-derivedpointer, legalaction/no deaths. Report actualhammer targeterror/
query/travel/bodyresponse honestly, even iftiperrorworsens; cursor alignment
is not plantrelease, completion or bodylift. No changednoise, currentfuture
noiseoracle/seedinput/filter/gain/goal/cutoffscan or failed30planretry.
Pass onlyadmits separate causalfeedback implementation/smoke, not target
completion/fullrecovery/teacher/labels/learning. Any eventual30step proposal
needs a newfullcontract, honestmemory/command-observe linkage andunchanged
1pixel/30cap, then recovery/wholevalidation beforedata/learning.

## Prior result: observed hammer-target phase times out, tracking audit next

Implemented separate `research/hammer_target.py`, onefixedworldgoal and
actualraw217pre/post pairs only. Recompute pointer=goal-currentrawbody-
fixedoriginaloffset0,20; legalaxes128/reach26..102 checked, no clipping or
caprenewal. Exactlyactionthenactualpostobserve/nextpre=lastpost. Target
completion is rawposthammer-worlderror<=1, notqueryrelease/bodyalignment.
Atmost30steps/oneattempt; illegalgoal/terminalaltitude/timeout terminal,
no rearm/reset/resumedfeedback. Existing stationarytolerance1unchanged.
8newtests/49focused/338fullPython+JS pass; originalcontrollers/physics/
milestones unchanged. Fullsuite fault-injection flushwarnings expected/pass.

Separately frozen6rollout localtest: nominal600historical gate, known
noise13105/reset14001 baseline299+30original versus candidate299+atmost30
goalsteps. Currentrawbody feedback, samepriorrow300worldgoal/noise/offset;
basephase stays298/calls299 throughout targetstage, no laterprior actions.
Variableearlystop/equalmax329 declared, not equalterminaltimes. No placement,
recordedprefixoverride, tolerance/gain/duration scan, secondgoal ormacro.

Candidate timesout30, rawgoalerror3.304590/physicalerror3.304582>1.
Actualhammermotion occurs, but neither rawcompletion nor physicalgatepasses.
Candidatefinalbody(268.882791,32),gain11 versusbaseline(268.888479,32),
gain11; neitherhold. No deaths/summits/updates/bodyrecovery/design/data/
teacher/learningadmission. Keep failed1pixel/30stepgate, no retrospective
3.4pixel tolerance or extra ticks. This test isolates bounded tiptracking,
not validatedacquisition or proof a differentgoal/largergain wouldwork.

2516control+720reset/6rollouts,owned30.220299seconds within180work/210owned
caps. Source/newphase/prior/completedfailedfollowthrough/plan/scripts/parent/
budget/deadline/secret-stripped ownedchild/durabletraces/cleanup bound.
All6rawmilestone/control/caseclock/action-observehistories,3fullbackendpairs,
equal299prefix/initialprestate, oldnominal600/baseline329/candidate300physical
histories independentlyexact. Bothgoalstages stop30/no rearm.
Evidence: `artifacts/hammer_target_probe_20261005_v1/verification.json`.
All earlierclosedpulse751/fresh8of9gates remainimmutable, primarygoal0.

Independently privatePAUSED1791164643.951258;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no paidreservation, remote
write, deployment, publicrelease or substantive localtraining.

The historical admitted180second OFFLINE tracking-authority/
disturbance audit of this6savedtrace/2516row set,0newplay/reset/updates.
Bindtrace/source/completedreview/script/plan/budget beforeanalysis. Inspect
each30goalstep actualraw13/14pointer versus commandedaction andposthammer
worldtargeterror, originalmotor/slew/reach andbody/renderoffset. Determine
whether residuals track applied cursor noise or contact/servo/geometry lag;
different laterstates remain descriptive/querynotforce. Any disturbance
estimate must use only past actually observed pointer and owncommand history,
never evaluatornoise_seed/currentfuture noise or unobservedstate.
Only mechanically supported causal feedback hypothesis may be proposed
after audit, with a fresh localphysicalcontract before testing.
No tolerance/30cap/noise suppression/goal/gain/phase scan, target retry,
closedplan extension, labels or paidlearning. Goalcompletion/bodyalignment/
recovery/fullvalidation and data-clockmemorylearnercontract remainseparate.

## Prior result: single release follow-through fails acquisition, completion-phase next

Separately frozen single-release FOLLOW-THROUGH completed. Nominal600gate,
knownfailednoise13105/reset14001 originalversus sameONEtick300worldgoal
override after299exactordinarysteps, then unchanged contactcontroller/
continuousnoise throughfixed751. No secondrelease, terminalmacro, extra
targets/gains/caps/proxychanges, placement or closed9case retry.

| Reference arm | Final body | Retained gain | Central/secondary held |
|---|---|---|---|
| Original contact controller |(269.481845,32)|11|false/false|
| One release + original continuation |(269.479241,32)|11|false/false|

Both final90central/secondary supportfalse,0deaths/summits/updates.
Declaredcentralrecovery/designadmissiongatefalse. Originalnominal600
central+secondary/gain83 exact. Candidate is a failed pulse+feedback
diagnostic, not causalcontroller/teacher/corpus/labels or learnedpolicy.
Originalfresh8/9failedstrictgate and localreleasepass remain immutable.

Controlledtick300localeffect exactlyreproduces: error14.708234->11.145062,
querytrue->false/travel4.474497, tip(-4.049067,+1.904252),body~4e-13.
Savedhandoffreview: error tofixedgoal9.504054tick301,14.798242tick302,
19.645380/24.818840/27.598087ticks303..305 asbasephases300..304advance.
Hammer remainsquery-free throughout300..305, firstlater queryhit352.
So this is NOT immediate replanting on the nextstep. The released hammer
does not complete the fixedreferencegoal before blindly timedlater strokes;
body falls tolowY32. Laterstates differ betweenarms, so follow-through is a
wholefeedback-stage comparison, not a directsingle-step bodyeffect or proof
of the firstfailure's completecause. Queryhits notforces/solverbranch.
Supplemental savedhandoffinspection adds0gameplay, no timing/tolerance search.

6rollouts/4204control+720reset,owned36.495458seconds within180work/210owned
caps.41focusedPython+JS pass, controller/physics/metrics unchanged.
All6rawmilestone/proposed/applied/caseclock histories,3fullbackendpairs,
all6priornominal/300ticklocalhistories, fullbaseline751 andequal299prefix/
contrastactualprestate exact. Exactlyonecandidateoverride/backend verified.
Source/prior/localadmission/plan/scripts/budget/deadline/ownedsecret-stripped
child/durabletrace/cleanup bindings pass.
Evidence: `artifacts/hammer_followthrough_probe_20261005_v1/verification.json`
and `handoff_review.json`.

Independently privatePAUSED1791163335.8149176;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no reservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

The historical admitted separate observed HAMMER-TARGET completion
phase, not a pulse-length scan or recoveryretry. Keep ONEfixedrawpriorrow300
worldgoal/offset0,20/formula/noise andordinary299prefix unchanged. Recompute
pointer=goal-currentrawbody-offset eachaction, until ACTUALpostrawhammer
worlderror<=1pixel (existingstroke stationarypositiontolerance), atmost30
steps/1second, oneattempt/no rearm/caprenewal. Do not count firstqueryrelease
as completion; no bodyalignment/acquisition implied by tipqualification.
No laterprior strokes during target stage; no resumedfeedback yet.
Require causal action/postobserve alignment, legal128axes/reach26..102,
real hammer motion andfinalerror<=1/no death/fullfidelity, not queryalone.
Freeze phase/source/work/deadline beforephysics. Nominal600referencefast
gate, baseline299+30originalcontinuation versus candidate299+atmost30
completionsteps,6rollouts/max2516control+720reset/180work/210ownedseconds.
Variablecandidate stoppingexplicit, equalmax329not equalterminaltimes.
Allprefix/old300response/baseline329histories exact. This pass would admit
later causal phasecontroller DESIGN only, not fullrecovery/teacher/data/
learning; bodypath, composition, wholevalidation remainseparate. No new
goal/tolerance/gain/time scan, terminalmacro, phasejump or failed751plan
extension. Preserve failures anddo notscale unchangedBC/PPO.

## Prior result: single hammer-world action releases lower plant, recovery untested

Frozen6rollout local one-step contrast completed: nominal600historical gate,
then ordinary299step originalcontactcontroller/noise13105/reset14001prefix,
baseline versusONEderived rawprior next-row hammer-world goal at tick300.
Actual proposed prefix controls applied with originalcontinuousnoise, no
placement/savedstate or recordingoverrides. One finalaction override is
explicitdiagnostic, not a learned/validatedteacher control.

Equal299fullphysical/control histories AND actual217preinput/fullprestate
beforecontrast. Goal(186.932344,3.814357), legalpointer(-84.057472,-54.507466)
fromrawprebody/fixedoffset0,20; float32action(-.656699002,-.425839573).
No target/clock/gain/cap/proxy scan, extraactions or cutoff extension.

| Reference local response | Baseline | Derived action |
|---|---|---|
| Hammer-targeterror afteraction |14.708234|11.145062|
| Hammer queryhit |true|false|
| Hammer travel |0|4.474497|

Commonpreerror14.708234. Candidateerror below BOTHcommonpre andbaselinepost,
queryrelease/positiveactualtravel/no deaths; declaredlocalresponsegate true.
Incrementalhammermotion(-4.049067,+1.904252). Incrementalbodydelta only
(+3.98e-13,+2.84e-14), numericalresidual/not meaningfulbodylift.
This is a controlled local release effect, NOT recoveredledgelanding,
causalproof oforiginalfailure, robustteacher, correctivecorpus or learning.
Noise-case300tickarms stop without eitherhold; nominal600retainsgain83/
central+secondary. Historicalfresh8/9failedstrictgate remains immutable.

2400control+720reset/6rollouts,owned30.928560seconds within180work/210owned
caps.41focusedPython+JS pass, repo controller/physics/metrics unchanged.
Source/prior/proposal/audit/plan/script/parent/budget/deadline binding,
secret/browser-stripped owned child/durabletraces/cleanup pass. Independent
all6rawmilestone/proposed/applied/caseclock histories, all3fullbackendpairs,
nominal600/baseline300sourcehistories and exactlyonecandidateoverride/backend
verify. No updates/summits/deaths/teacher/data/fullrecoveryadmission.
Evidence: `artifacts/hammer_release_probe_20261005_v1/verification.json`.

Independently privatePAUSED1791162189.1954892;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no reservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

The historical admitted separate single-release FOLLOW-
THROUGH, not morelocaltargets. Nominal600referencefast gate; failedcase
original versus sameone tick300worldgoal override after299exactsteps,
then unchanged originalcontactcontroller/continuousnoise through fixed751
horizon.6rollouts/max4204control+720reset/180work/210ownedseconds.
All oldnominal/prefix/base751/candidate300histories exact; equalcontrastpre,
all backend traces and raw metrics required. Candidate must have original
centralheldevent AND final90central/speed<=2/bodyfraction>=.8/nodeaths to
admit later causal conditionalcontroller design. Report secondarysupport
without substituting it for declaredcentralgate. No automaticterminalmacro,
extra release/hold pushes, target/phase/cutoff search, expiredplanretry or
9case rewrite. This pulse+unchangedfeedback continuation is a diagnostic,
not whole-wrapper/newcohort or labels. Localbodylift/recovery cannot be
presumed fromtiprelease. Only after such recovery would new causalcontroller
implementation, freshfullvalidation and separatecaptureddata/clock-memory
learnercontract be reconsidered. Do not scale unchangedBC/PPO.

## Prior result: offline acquisition audit motivates one hammer-release authority test

Completed frozen180second OFFLINE audit of6saved751tick originaltraces:
nominal,failednoise13105,successfulnoise13104,reference+fast/4506rows.
0newgameplay/reset/updates; all trace/project/source/completedreview/script/
plan/budget bindings verified. All6raw milestone/proposed/applied/control-
clock histories and3fullbackendpairs exact. Original motor0.4/blocked
bodyrequest-.5/sourceexcerpt exact; queryflags still not forces/solverbranch.
Evidence: `artifacts/acquisition_audit_20261005_v1/verification.json`,
`audit.json`, `original_contact_excerpt.txt`, `local_authority_proposal.json`.

Physical results unchanged: freshwrapper8/9central/8/9secondary,failed
noise13105final(269.481845,32)/gain11/nohold,0summits/deaths/learning.
Audit is explanation/proposal, not player improvement or teacher admission.

Failedcase reachesX200tick269/X250tick276/Y65tick268, but neverX285 orY100
through751. Nominal/successfulnoise13104 reachY100tick367/X285tick368.
FailurebodyX fixes at269.481845fromtick500; last hammerqueryhit482.
Last120bodyqueryhits120/hammerhits0/saturated16pixelcorrections120.
Late heldfloor and free-hammer motion are not target-platform acquisition
or established body authority. No gain/terminaltrigger/cap widening.

At predeclared100tick snapshot300, failedbodypre(270.989817,38.321823),
hammerpre(194.994691,-8.487297), causal previoushammerhittrue/travel0.
Nominalbodypre(279.381311,48),hammerpre(188.480375,.670175),previous
hammerhitfalse/travel2.850853. Failedactualbody moves(-1.195117,-3.279796)
and hammer remainsfixed; nominalbody stationary and hammer moves freely.
Signproxy active onfailedcase, but the continuing prior is at a different
plant geometry. This is a descriptive same-clock contact/stroke mismatch,
not proof the proxy/action at300caused the earlier loss.
All noise streams differ fromtick1, commonapplied-control/stateprefix0;
only firstpreinputs exact. Failed-vsnominal >1bodypixel starts30/>10starts289;
vs successfulnoise13104 starts28/170. Later unequal-state differences do
not isolate single-action effects or identify first causal failure.

Derived ONE local mechanically motivated goal, no target/action/clock scan:
ordered next rawprior row300hammerworldtarget(186.932344,3.814357).
Originaloffset0,20 holds all4506savedstates; pointer=target-actualbody-offset.
At failedtick300pre, proposedpointer(-84.057472,-54.507466),float32action
(-.656699002,-.425839573),targetreach90.864866within26..102/axes128.
Reference row is a fixed prior goal, not a futurefailed observation or an
off-state corrective label. Candidate requests motion away from lower plant
toward the known next stroke, but real release/bodyeffect not yet tested.
Independent scalar arithmetic/prior/raw linkage/legalbounds verify.
Later boundedproposalreview did not rerun audit or renew its deadline.

Independently privatePAUSED1791160887.322387;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no reservation, remote
write, deployment, publicrelease or substantive localtraining. Goal0.

The historical admitted one-step response check, now completed above, used nominal600reference/fast historical
gate, then ordinary299step exactfailednoise13105/reset14001 prefix and
baseline versus this ONE hammer-world action at controlledtick300, withsame
continuednoise.6rollouts/max2400control+720reset/180work/210ownedseconds.
Actual pre-input/history must be equal, all prefixes/baselines/backend fields
exact. Require candidate posthammer-targeterror below BOTHcommonpreerror
and baselineposterror, plus actualqueryrelease OR positivehammertravel,
no deaths; no assumed sign/bodylift.
Local actuator-response gate only, never fullrecovery/teacher/labels/learning.
No further targets/pushes/timingattempts, phasejumps, sweeps, placement, failed
9case retry or gate rewrite. New causalcontroller/recovery/freshvalidation
would be separate contracts after local authority, before data/clock-memory
learner admission. Do not blindly scale unchangedBC/PPO.

## Prior result: fresh wrapper8/9central, strictgate fails on earlier acquisition

Frozen exact same originalcontactcontroller versus causalwrapper on9unused
structuredcases: reset14001,nominal,left/right(+/-.75,-.125)*3/four-tick
warmups,noise.02/seeds13100..13105. Hidden/ignored JSON/JSONL exact
reset_seed/noise_seed field search found no previous use before declaration.
Original/wrapper/reference+fast,max751ticks; fixed permanent monitor stopping
and no rearm/caprenewal. Equal maximum horizon, not equal terminaltimes.
No rule/source/target/gain/proxy/cap/noise/metric edits or placement.

| Reference arm | Final90 central support | Final90 secondary support | Retained gain |
|---|---|---|---|
| Original contact-sign prior |7/9|8/9|83in8cases,11in1|
| Causal terminal wrapper |8/9|8/9|83in8cases,11in1|

Noise13101independently reaches leftedge(295.169232,104). One rawstate
attempt recovers to(315.237517,104):600base/30plant/onepush/93release,
3settle+90independenthold/90bodyhits,724controls. It is a second exercised
recovery under different noise, not eightrecoveries or learnedskill.
All8othercases permanentlybypass and full751control/physics/base-metadata
histories equal original. Nominal/left/rightfinalX322.585886/322.585884/
322.585903,Y104. Other successfulnoiseX325.627033/325.943050/329.308637/
324.976926,Y104. No deaths/summits/updates.

Noise13105fails BOTHledge holds; atcheckpoint after600observed transitions
already(269.481845,32),rawbodyqueryhit1,basephase599. Final751state same
position,gain11,body-queryfraction1/maxspeed.481703 overlast90, but below/
outside bothregions. Wrapper correctly bypasses the ineligible rawstate;
no failed planting/push, no phase stall or a missed eligible trigger.
This locates an earlier acquisition failure, not its causal action/contact
error. Do not widen terminal trigger to floor support or relax9/9to8/9.
Auxiliary boundary inspection initially used absent phase metadata key;
actualselected_phase corrected in inspection only, errorpreserved/no physics
rerun or frozenreview edits.

36rollouts/26982control+4320reset,owned161.207101seconds within immutable
300work/330owned cap.41focusedPython+JS pass, controllercode unchanged.
All18fullbackendpairs,18wrapperfirst600freshoriginalprefixes and4full
historicalnominaltraces exact. Independent36raw milestone/support/control/
caseclock/action-observe histories verified. Strictfresh9/9gatefalse,
separate data/learnercontractadmissionfalse, no teacher/corpus/labels or
paidlearning. Keep failure immutable; no successful-only8case admission,
retuning/retry ofclosedplan or unchangedBC/PPO scaling. Primaryfullgoal0.
Evidence: `artifacts/terminal_wrapper_fresh_20261005_v1/verification.json`
and `failure_boundary_review.json` beside it.

Independently privatePAUSED1791159934.6042366;80444390source,
onstate-20261004-v1/onstate_study/contexted3a53c3/closeddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no newreservation, remote
write, deployment, publicrelease or substantive localtraining.

The historical admitted offline audit, now completed above, used acquisition
audit of existing nominal,failednoise13105 andsuccessfulnoise13104 original
traces/reference+fast,6traces/4506rows,0newgameplay/reset/learning. Bound
source/trace/completedreview/script/plan/budget hashes beforeanalysis.
Inspect ordered prior stroke/contact transition around lost acquisition,
actualhammer query/travel/body motion/applied controls and original motor/
collision response. Distinguish equal-prefix local effects from unequal-state
descriptive comparisons; queryhits are not force/solverbranch. Only derive a
mechanically justified distinct local contact-authority test after audit,
with a fresh physical contract before play. No terminaltrigger widening,
phasejump/gain/target/cap/proxy/threshold scan, closedcase retry, detector
relaxation, labels or paidlearning. Require recovery/fidelity/fullvalidation
before any separate captureddata/clock-memory learnercontract.

## Prior result: whole-wrapper development cohort9/9central, fresh validation pending

Separately frozen unchanged originalcontactcontroller versus causalwrapper
on all nine previous developmentcases: reset13001,nominal,left/right
(+/-.875,.125)*3/four-tick warmups,noise.02/seeds12100..12105. Max751
controlledticks/arm/reference+fast. Original runs full751; wrapper stops on
its fixed permanent monitor success/failure or751cap. Equal maximum horizon,
not equal executedticks or matched terminaltimes. No rule/source/target/gain/
proxy/cap/noise/metric edits, recordedactionoverride or placement.

| Reference arm | Final90 central support | Final90 secondary support | Retained gain |
|---|---|---|---|
| Original contact-sign prior |8/9|9/9|83each|
| Causal terminal wrapper |9/9|9/9|83each|

One observed-state attempt in noise12100:600base/30plant/onepush/92release,
2settle+90qualifiedholdticks,723controls,final(314.427961,104) instead of
original751tick edge(293.727677,104). Eight cases permanently bypass at the
one checkpoint; ALL751raw/control/physics/base-metadata rows equal original
arm, not just finalposes. No harm to alreadycentral histories. Nominal/
left/rightfinalX322.585886/322.585759/322.585918,Y104. Remaining five
noisefinalX325.311196/322.016009/325.547513/324.204089/324.070853,Y104.
All9centralfinalsupported windows/originalheldevents,0deaths/summits/updates.

36rollouts/26980control+4320reset,owned159.047487seconds within immutable
300work/330owned cap. Source/controller/prior/plan/scripts/admission/budget
bound; secret/browser-stripped owned child, durable rows and owned cleanup.
41focusedPython+JS collision checks pass; no repo controllercode changed.
All18fullsamehostbackendpairs,36old600physical/controlprefixes and6known
fullsmoke wrapper histories exact. Independent36raw milestone/support/
applied-control/caseclock/action-observe histories reconstruct and strict
9/9gate recomputes. Backend copies are fidelity, not extra independent trials.
Evidence: `artifacts/terminal_wrapper_cohort_20261005_v1/verification.json`.

Pass admits fresh fixed-wrapper validation ONLY. Cases are reused development,
not freshheldout, multipletrainingseeds, learnedpolicy or admittedteacher/
corpus. Original600eightofninefailedgate and fixed90failure remain immutable;
this is a distinct newcontroller/751maximum protocol, not a retroactive pass.
Primaryfullgoal0, no paidlearning or labels. Eight bypass exactness is
preservation evidence, not eight separately exercised recovery primitives.

Independently privatePAUSED1791158683.839298;80444390source,
onstate-20261004-v1/onstate_study,contexted3a53c3 andcloseddeadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no newreservation, remote
write, deployment, publicrelease or substantive localtraining.

The historical admitted fresh validation, now completed above, used development-validation cases
beforeplay, reset14001,nominal,left/right(+/-.75,-.125)*3/fourtickwarmups,
noise.02/seeds13100..13105,ninecases. Exact same original-versus-wrapper
arms/reference+fast,atmost751ticks/36rollouts/max27036control+4320reset/
300work/330ownedseconds; fixed stoppingrule and all original metric/support
criteria. Verify exact case/seed fields unused before declaration. Require
9/9reference finalcentral supported holds/no deaths/nominalexact/fullbackend
fidelity, preserve bypass exactness, no gains/caps/targets/proxy/trigger scans.
Do not presume one arming attempt or success by noise/case identity. Fresh
validation pass may admit a separately captured data/clock-memory-aware
learner contract, never automatic labels/paidlearning/summit promotion.
Failure stays closed, not renewed or reclassified. No unchangedBC/PPO scaling.

## Prior result: causal terminal wrapper smoke passes, whole cohort pending

Implemented `research/terminal_controller.py` around unchanged contact-sign
prior. Only raw217pre/post float32 and resettable privateclock/phase, no
case/seed/trace-index/privileged-state inputs. One checkpoint after600actual
observed transitions, beforedecision601: slow/body-supported leftsecondary
edge285<=X<305,Y100..112,speed<=2. Float32encodedboundaries used to ensure
encodedcentralX305bypasses instead of roundoff-triggering. No missed-checkpoint
rearming, secondattempt or caprenewal. Max751decisions.

Fixed30plant(26,-56),onepush(0,-56),originalrelease. Require action/pre then
actualapplied one-tick observe/post; nextpre equalslastpost exactly. Base
clock advances even during override; settling monitor consumes firstrelease
post-state, neverpushpost. Monitor ticksrelativecontrolledclock, not global
resetsettling. Old330fullPython+JS pass; final encodedboundary edit verified
with15focused tests. Newtests coverbypass/unsupported/fast/coordinateguards,
no-rearm, plant/push/monitoralignment, prepostlink,751cap and reset.

Frozen6rollout implementation smoke: nominal andnoise12101central bypass
all751ticks on originalcontrols; knownnoise12100edge activatesonce,
30plant/onepush/92release(2settle+90hold),723ticks,final(314.427961,104).
All three finalcentral supported holds/gain83,0updates/deaths/summits.
Edge full723physicaltrace equals validatedmanualprimitive; first600ofall
cases exactoldcontroller. Candidate outputs actually applied with original
noise, no sourceprefixoverride or case-oraclebranch in controller.
Nominalfinal(322.585886,104),centralnoisefinal(325.311196,104).

4450control+720reset,all threefullbackendpairs exact. Independent6full
rawmilestone/proposed/applied/prepost/monitor/noise traces verify, both
bypasses exactbaseoutputs. Wrapper smoke passes, only wholecohortadmitted.
No teacher/corpus/data/learner/summit promotion. Primarygoal0.
Evidence: `artifacts/terminal_wrapper_smoke_20261004T234047944352Z/verification.json`.
Closedfixed90failure and old600ninecase8/9central/failed9gate unchanged.

Independently private PAUSED1791157675.4369287;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no new reservation/HFwrite/
deployment/publicrelease/substantive local training.

The historical admitted cohort, now completed above, compared wholewrapper versus
originalcontactcontroller on same9developmentcases reset13001/warmups/
noise12100..12105, atmost751ticks/arm/reference+fast,36rollouts/max27036
control+4320reset/300work/330ownedseconds. No controller/rule/timing edits,
all old600prefixes exact and bypassexact; require9/9reference finalcentral
supported holds/no deaths/fidelity. This newcontroller/horizon does not
rewrite old600failedgate or qualify as freshheldout. Even passing requires
fresh wrappervalidation before data/clock-memory-aware learnercontract;
no labels, paidlearning or unchanged BC/PPO scaling.

## Prior result: settle-aware local recenter hold passes, conditional design only

Implemented/tested separate `research/settled_hold.py` monitor, never
changing originalMilestoneTracker. Consecutivefinite30Hzstates, atmost30
settle ticks; centralposition/speed<=2/bodyqueryhit triggers independent
holding phase. Trigger sample excluded, next90region/speed/alive ticks
counted with originalbodyfraction>=.8. Timeout, terminal, any holdregion/
speed loss or insufficientcontact fails with no rearming/cap renewal.
All323Python+JS pass; edge predicate/hold criteria unchanged.

New separately frozen local test retains600ordinaryprefix/30plant/
onepush/noise12100/originalcontactcontroller. Maximum751ticks/180seconds,
not the closed90window extended inplace. Pushed branch settles in2ticks,
then90qualifiedholdticks/90bodyqueryhits, final(314.427961,104),gain83,
velocity0; original3secondcentralheld detector alsotrue. Controlled723ticks.
Unchanged and plant-only branches failsettlingtimeout30 atX293.727677/
303.229350, stop661ticks, no restart. No deaths/summits/learnerupdates.

8rollouts/5290control+960reset, all fourfullbackendpairs exact. Oldprefix
controls/observations/rewards/physicalstates identical through available
history; monitor metadata alone added. Independent8full rawmilestone/
proposed-applied-control/noise/monitor traces reconstruct; held samples are
distinct from trigger. No forces/privileged reset or backend duplication
claimed as independent success. New localconditionalterminaldesigngate
passes, not robustteacher/model/data admission or primaryfullgoal.
Evidence: `artifacts/settle_aware_probe_20261004T232031597236Z/verification.json`.

Closedfixed90failure89ticks and original8/9central/9/9secondary/failedstrict
9/9cohort remain unchanged. This is hand-designed single-edge recovery,
not learnedpolicy/multipletrainingseed/held-out summit competence. Goal0.
Independently private PAUSED1791156280.5652258;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledgerbytespreserved,7closed$0.4564241866528988; no new reservation/HFwrite/
deployment/publicrelease/substantive local training.

The historical admitted implementation, now completed above, wraps the fixed
contact-signcontroller, one attempt after600decisions only for raw supported
slow left-edge landing(285<=X<305,100<=Y<=112,bodyquerytrue,speed<=2).
No case/seed/trace-index trigger. Already-central inputs remain exactoriginal
controller. Keep30plant(26,-56),onepush(0,-56),originalrelease controller,
30settle cap/90hold and no-rearm failure. Inputs raw217plus private resettable
phase/clock only; align monitor update to actually applied one-tick states,
not ignored predicted controls or futureobservations. Freeze wrapper contract
and bounded original-physics smoke before play; preserve safety/action caps.
Only subsequent separately declared whole-wrapper cohort can reconsider
teacher/corpus admission, and later learner must handle clock/memory honestly.
No automatic old9casegate rewrite, labels or paid learner scaling.

## Prior result: push/release settles centrally, fixed90hold gate one tick short

Completed frozen release diagnostic with unchanged600ordinaryprefix,
30plant(26,-56),onecontrast hold/push(0,-56),90original contact-controller
release steps. Continuednoise12100, equal721terminal horizons, no
extra pushes/targets/gain/caps/threshold changes or privileged placement.
Nominal600baseline and all prior631tick histories reproduce exactly.

| Reference arm | Final pose | Central qualification |
|---|---|---|
| Unchanged terminal |(293.727677,104)|nohold|
| Plant-only+release |(303.229350,104)|best.166667s,nohold|
| Plant+push+release |(314.427961,104)|89qualifiedticks/2.966667s,nohold|

Pushed body settles with finalvelocity0, centrally positioned and body
supported. But the firstrelease tick632is at(312.001215,103.842922),
speed2.182757>original2limit/bodyqueryfalse. It is the sole nonqualified
row in final90. Remaining89region/speed ticksqualify; bodyqueryfraction
.988889. Declaredfinal90body-support/original3sheldgatefalse. Do not append
one tick, relax speed/hold or treat nearby successful state as a pass.
This is settling progress, not admitted recovery/teacher/learnedpolicy.

Prior localbodyauthority(+5.2,.183846),fixedhammer,13/30hits/travel0
reproduced at contrasttick631. Later release states differ across arms,
so late outcomes are a full feedback-stage comparison, not an isolated
one-step action causal contrast. Fullconditionalterminaldesignblocked.

8rollouts/5526control+960reset,0updates/summits/deaths. All four fullbackend
pairs and eight priornominal/631traces exact. Independent8full rawmilestone/
proposed-applied-control/noise reconstructions and boundaryreview pass.
26focusedPython+JS, source/prior/controller/admission/script/plan/deadline/
ledger bindingsvalid. No newgameplay for the boundary analysis.
Evidence: `artifacts/terminal_release_probe_20261004T225830472380Z/verification.json`
and `settling_boundary_review.json` beside it.

Independently private PAUSED1791154976.046585;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988, no reservation/HFwrite/
deployment/publicrelease/substantive local training. Goal0; original8/9
central/9/9secondary and failedstrict9/9gate unchanged.

The historical diagnostic hypothesis, now tested above, separated settling and qualified-hold timing
be separate state-observed phases, not a fixed90wallclock immediately after
an impulse. Keep prefix/30plant/onepush/controller/noise fixed; predeclare
atmost30settle ticks using originalcentralregion/speed<=2/bodyquery evidence,
then90qualified hold ticks under the same controller with full original
bodyfraction>=.8support contract. No timing sweep or closed90plan retry;
failure/timeout/lostqualification cannot renew caps. Freeze the full phase
rule and maximumwork/deadline before physics. Only such local settledhold
would admit conditionalterminal design, not labels, nine-case gate changes
or learner/summit promotion.

## Prior result: real planting/push moves body into center, hold not settled yet

Completed frozen8rollout local original-renderer test. Nominal600tick
playback central hold reproduces first. Terminal arms use unchanged
ordinary-start600tick edge_case/noise12100 contact-controller history;
all sourcepre/action/post/reward/info/telemetry rows exact. Noise continues
after600with the same physical clock, no placement or noise suppression.

Plant-only and plant-push share30identical(26,-56)steps and exact pre-input
before the one contrast step: hold(26,-56)versus push(0,-56). Comparator
hold is the declared contrast, not a cutoff extension. Real hammer-query
hits13/30, last common hammertravel0. Matched push adds(+5.2,+.183846)
body motion, hammer difference0. Local planting/body-authority gatepasses;
local support may be bodyORhammer query, explicitly not the milestone hold.

| Reference terminal arm | Final body pose | Retained gain |
|---|---|---|
| Unchanged continuation |(293.727677,104)|83|
| Plant-only |(304.741395,104.381272)|83.381272|
| Plant+onepush |(309.941395,104.565118)|83.565118|

The push reaches centralcoordinates, but bodyvelocity(3.745127,1.050551)
is too fast for the original<=2hold criterion. Both intervention best
qualified centralwindows only.166667seconds, no new held event. No deaths/
summits/learnerupdates. This is real local actuator authority and direction,
not settled recentering, robust teacher or learned-policy progress.

4986control+960reset,all fourfullbackendpairs exact. Independent8full raw
milestone/proposed-applied-control/continued-noise traces reconstruct and
the equal-history response gate recomputes.26focusedPython+JS pass.
Source/controller/geometryadmission/script/plan/deadline/ledgerbindingsvalid.
Evidence: `artifacts/terminal_plant_probe_20261004T223832761543Z/verification.json`.
Original8/9central,9/9secondary and failed strict9/9gate remain unchanged.

Independently private PAUSED1791153896.6747024;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988, no reservation/HFwrite/
deployment/publicrelease/localtraining. Primarycompletion0.

The historical admitted diagnostic, now completed above, used knownedge600prefix,
unchanged30plant and onepush, then90ticks resumed original contact-sign
controller to test release/settling. Compare unchanged continuation,
plant-without-push and plant-plus-push through equal721tick horizons,
plus nominal600reference/fast baseline: max8rollouts/5526control+960reset,
180work/210ownedseconds. Keepnoise/rules/targets/gain/caps/thresholds fixed,
freeze actual source/admission/cases/deadline before execution. Require final
90central position/speed/bodycontact support and fidelity before a full
conditional terminalcontroller design. No secondpush/target/cutoff search,
old9case retry/gate rewrite, label admission or learned/summit claims.

## Prior result: terminal audit supports a right-side plant test, not recentering yet

Completed frozen180second offline audit of6captured traces/3600rows:
nominal,edge_noise12100,central_noise12101,reference+fast.0newgameplay/
reset/learning/HFwrites. Current physical outcomes remain8/9central,
9/9secondary,strict9/9gatefalse; no new controller, corpus or teacher.

Final120ticks: all3bodies have queryhit120/120 and constantX; all3hammers
queryhit0/120. Edge correction saturated120/120 (centralcases0), proxy
inactive. EdgehammerX383.358..390.854 whilebodyX293.728. This is consistent
with free hammer motion far to the right, not established body-control
authority. Telemetry still does not expose actual solver branch/force.
Edgecurrent quasi-static world hammer target(386.605,80.010), offset(0,20).

Original Player collider is SVG16.75x49.61678, rotationcenter
(10.43447,12.55767), bottom37.0591below position atdirection90/size100.
Hammerhitbox16x16bitmap/resolution2 means roughly8x8stage pixels. Body
Y104does not imply terrainY83; approximate alpha surfaceY65can support this
tall collider. Do not substitute the alpha descriptor for renderer hitboxes.
16905approximate terrain grid points, within25000cap; right-side surface
atbodyX+26=319.728,Y65, no opaque sampled-band points atbodyX-26=267.728.

Discarded initial offline(-26,-40)leftplant geometry before game testing.
One derived rightplant(26,-56)pointer targets(319.728,68), reach44.407within
26..102, approximatefootprint18/81opaque samples. This is not renderer
contact or an actually applied action. Follow-on(0,-56)leftward hammer
request could yield rightward body motion through original-.5blocked
response, only if real planting occurs. No sign/gain/threshold/cap tuning.

Evidence: `artifacts/terminal_authority_audit_20261004T221822853423Z/verification.json`.
Audit completed within original immutable deadline; later bounded
verification checked geometry/one mechanically chosen footprint/pause,
not an audit retry/deadline extension. One inspection failed because Pillow
does not open original body SVG; raw SVG/XML inspection resolved it without
installing dependencies/rasterizing/editing assets. Failure preserved.

Independently private PAUSED1791152688.22913;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988, no new reservation. Goal0.

The historical bounded physics proposal, now completed above, froze legal600tick edge
prefix reproduction, then unchanged terminal continuation versus fixed
(26,-56)plant, atmost30ticks. A third branch uses identical plant history
and one(0,-56)push; require equal pre-input, actual query/travel evidence and
positive incremental bodyXresponse/reference-fast fidelity. No arbitrary
placement, pointer scan, cutoff extension, force inference or teacher labels.
Only local real planting/authority can admit a separate full terminal
recenter stage. Preserve the failed9/9case/gate and original controller.

## Prior result: fresh validation improves to8/9central, fails strict9/9gate

Frozen exact same contact-sign clock-guided rule versus pure playback,
reset13001,nominal,strongerleft/right(+/-.875,.125)*3/fourtickwarmups,
noise std.02/seeds12100..12105,600tick cases/reference+fast. Exact
noise_seed/reset_seed field search found no prior use before declaration;
numeric matches in benchmark hashes/terrainY12100were not case seeds.
No rule/source edit, gain/cap/threshold/sign sweep or prefix overrides.

| Reference arm | Central final support | Secondary held | Retained gain |
|---|---|---|---|
| Pure playback |5/9|6/9|63.697..83|
| Contact-sign feedback |8/9|9/9|83each|

Candidate nominal/strongleft/strongright finalX322.585886/322.585759/
322.585918,Y104. New noise12101..12105finalX325.311196/322.016009/
325.547513/324.204089/324.070853,Y104, central final support.
Noise12100fails central, final(293.727677,104),gain83; final90Xconstant,
Y103.538617..104,speedmax.461383,bodyquerycontactfraction1, secondary
final support. It physically holds the ledge edge, not the frozen central
regionX305..335. No claim of climbing/control impossibility.

Strict all9central-final-support/no-death/nominal/fidelity consideration
gatefalse. Do not substitute8/9orsecondary9/9post hoc: no teacher/corpus/data
admission or paid learning. Controller is hand-designed/time-guided, not
learned-policy progress; primaryfullgoal0. Improvement relative to playback
on this declared subset is real, but not multi-seed/held-out summit proof.

36rollouts/21600control+4320reset,0updates/summits/deaths. All18fullbackend
pairs and fourhistoricalnominaltraces exact. Independent36full rawmilestone/
action/caseclock traces and final support checks pass.26focusedPython+JS.
Ownedelapsed152.9937seconds within immutable300second budget. Source/rules/
prior/admission/script/plan/ledger bindingsverified; tracesdiagnosticonly.
Evidence: `artifacts/contact_validation_probe_20261004T215921117225Z/verification.json`
and `edge_support_review.json` beside it.

Independently private PAUSED1791151516.0854468;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988, no new reservation,
HF writes, deployment, public release or substantive local training.

The historical diagnostic, now completed above, inspected terminal authority at the captured
edge landing, including hammer pose/query/travel, original planted response
and terrain. Final16pixel correction is saturated, bodyXconstant, signproxy
inactive; do not infer a force or that more gain cures it. Determine whether
a distinct legal plant-and-recenter terminal stroke is justified before
freezing any local physical test. Preserve all cases/failed strictgate; no
closed-plan retry, successful-case-only labels, gain/cap/threshold/sign
sweep, detector relaxation or unchanged BC/PPO scaling.

## Prior result: contact-sign controller holds all three development cases

Completed the admitted fixed-rule full comparison with no controller edits:
pure playback, old timed correction and contact-sign timed correction,
nominal/reset12001,leftwarmup,noise11105,600ticks each/reference+fast.
Actual candidate controls apply throughout after fixed forced warm-up;
no recorded-prefix override, placement, learned update or rule sweep.

| Reference case | Pure playback central/secondary | Old feedback central/secondary | Contact-sign central/secondary |
|---|---|---|---|
| Nominal |true/true,gain83|true/true,gain83|true/true,gain83|
| Left warm-up |true/true,gain83|true/true,gain83|true/true,gain83|
| Noise11105 |false/true,gain82|false/false,gain61.027|true/true,gain83|

New final poses(322.585886,104),(322.585838,104),(330.224551,104).
All three final90tick windows stay inside unchanged central region, body
querycontactfraction1 and maxspeeds0/0/.445238. Nominal/warm-up Xconstant,
noiseX330.224551constant and Yrange103.554762..104. This is real final
supported ledge acquisition on these selected development disturbances,
not just latched events. Candidate correctedticks579/573afterinterventions,
nonzero sign reversals142/139; nominal correction0 and full traceexact.

Broader-validation gate passes, but only for a hand-designed clock-guided
controller: not new learned policy, robust teacher, summit or model promotion.
Three reused cases cannot establish general correction competence. No
corpus/labels admitted or training launched. Primary fullcompletion metric0.

18rollouts/10800control+2160reset,0updates/summits/deaths. All nine full
same-host backend pairs exact; all twelve old pure/world-feedback full
traces reproduce exactly. Independent18full raw milestone/action/case-clock
traces and final support windows reconstruct.26focusedPython+JS pass;
no repo controller code changed (last full315suite remains recorded).
Owned elapsed73.8478seconds within immutable300second work bound.
Evidence: `artifacts/contact_recovery_probe_20261004T213808503161Z/verification.json`.
Backend copies are fidelity, not extra independent successes.

Independently private PAUSED1791150349.8276567;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988; no new paid reservation,
HF writes, deployment or public release.

The historical admitted direction, now completed above, froze fresh development-validation
cases for exact same rule versus pure playback, with no retuning/data
collection. Proposal: reset13001, nominal, left/rightwarmups(+/-0.875,.125)
times3/fourticks each, noise std.02/seeds12100..12105, ninecases/600ticks/
reference+fast. Maximum36rollouts/21600control+4320reset,300work/330owned
seconds. Persist fresh actual source/cases/deadline before gameplay, verify
new seeds/cases and nominal baseline. Require all9reference central final
supported holds/no deaths/nominal parity/exact backend fidelity before
considering corrective corpus admission. Even passing needs separate
captured pre-action/applied-control data and a learner contract that handles
explicit clock/memory honestly; not ordinary feed-forward imitation by
assumption, not final held-out multi-seed policy completion.

## Prior result: local contact-sign gate passes; full recovery not tested yet

Added opt-in `mode="contact_timed_feedback"` only. Fixed explicit clock,
prior, gain1/norm16/axis128caps; reverse correction when causal raw previous
hammer queryhit==1 AND previoushammertravel<3pixels. Raw binary/nonnegative
proxy guards, no true solver branch/force observation. Old modes unchanged:
7200saved action/metadata rows exact. All three modes reproduce600actual
nominal actions/phases.315Python tests+JS pass.

Fresh frozen180second local check first reproduces nominal timed central
hold at(322.586,104),gain83 on reference/fast, not a new learned hold.
Then three arms replay identical legal prefixes from ordinary(0,21), with
no state placement, and differ only at one local action. Candidate proposals
are explicitly overridden during prefixes, never candidate closed-loop
skill or eligible teacher labels. All arms share exact final raw pre-input.

Noise11105tick28: old relative-to-playback body response(+.098,+.114);
new sign-aware response(-.098,-.1138), hammer difference0. Dot with intended
body error changes-.112921to+.112807, proxyactive. Warm-up tick14 proxyfalse,
new/old action and responseexact. Local intended-response gate passes.
This is a concrete one-step direction improvement, not recovery, teacher
validity or primary completion improvement. Zero full new-controller
closed-loop recovery cases. Prior failed noisy recipe remains rejected.

14rollouts/1452control+1680reset,0updates/summits/deaths, all seven full
backend pairs exact. All legal prefixes, pinned nominal and old local
final-step baselines exact. Independent14full raw milestone/proposed/
applied-control/clock traces reconstruct and local gate recomputes.
Evidence: `artifacts/contact_sign_probe_20261004T212005018592Z/verification.json`.
Backend copies are fidelity, not independent recovery successes.

Independently private PAUSED1791149106.3813038;80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Ledger bytes preserved,7closed$0.4564241866528988, no new paid reservation,
HF write, deployment or training. Full goal0.

The historical admitted diagnostic, now completed above, froze comparison of pure
playback, unchanged timed feedback and contact-sign timed feedback on the
same nominal/reset12001,leftwarmup,noise11105development cases, reference/
fast,18rollouts/10800control+2160reset maximum,300second work/330owned
including cleanup. Keep sign proxy/threshold/gain/caps/prior/clocks fixed.
Nominal pure baseline/old timed traces must reproduce; nominal candidate
must be exact, actual perturbation holds and fidelity required. Do not
retry/retune failed rules or admit teacher labels/learning from a tiny
development subset. Passing would only allow broader predeclared feedback
validation, never summit or saved-policy promotion.

## Prior result: offline audit finds one same-prefix planted-response reversal

Completed a frozen180second offline audit of12captured clock-ablation traces/
7200rows;0newgameplay/reset/learning and no HF writes. Trace/project/source/
completed-review/script/plan/budget hashes match. Actual physical results
remain the prior study's2/3central feedback holds, no noisehold/gain61.027
versus playback secondaryhold/gain82,0summits/deaths. This audit is not new
player or learned-policy progress.

Noise11105first applied contrast is controlledtick28 after27exact common
legal action/full physical-state rows, with identical raw pre-input.
Feedback correction(-0.490001,-0.569308)pointerpixels becomes actual delta
(-0.490,-0.570); hammer response difference0, body extra(+0.098,+0.114).
Body moves opposite intended correction. Previous hammer-queryhittrue and
previoushammertravel0. Originalmove-hammerf/b{ blocked branch passes
(-0.5*requested hammer motion) to the body; with motor0.4, this local response
matches the expected negative0.2pointer-to-body sign. This is one controlled
common-prefix contrast, not a complete later-failure causal diagnosis.

Warm-up first proposed control differs tick2, but forced warm-up masks it
until appliedtick14 after13exact common action/state rows. First equal-input
contrast changes hammer position, not body; previous queryhitfalse and
previoushammertravel37.203pixels. Ignored proposals are not applied actions.
Noise body separation>1pixel begins tick30, query-hitflag difference tick285;
warm-up counterparts32/61. Those later pre-inputs differ: descriptive only.
Both successful/failed segments can have the same query-hit flag, so it is
not force, normal, a planted-state guarantee or the internal solver branch.
Audit correction-contact counts are descriptive and include ignored warm-up
proposals; they do not identify a causal contact-effect frequency.
Evidence: `artifacts/contact_response_audit_20261004T205819078549Z/verification.json`.

Independently private PAUSED1791147764.199187; actual80444390source,
onstate-20261004-v1/onstate_study and closed deadline unchanged. Ledger bytes
preserved,7closedestimated$0.4564241866528988, no new reservation. Goal0.
The completed audit ran inside its immutable deadline; subsequent bounded
verification checked hashes/first proposed-versus-applied contrasts/pause,
without rerunning the audit, extending its deadline or changing its results.

The historical mechanically motivated hypothesis, now tested above, kept clock/prior/gain1/norm16/
axis128fixed; reverse correction only when raw causal pre-input has hammer
queryhit and previoushammertravel<3pixels, matching the original wall-test
threshold. Proxy is fallible, not privileged true-contact/branch observation.
First freeze a bounded ordinary-spawn recorded-prefix one-step sign check on
reference and fast, reproducing the prior baseline before local inversion.
Only intended local body response/fidelity can admit a fresh fixed-case
recovery check. No teacher/labels/learning admission from that single point,
no sign/threshold/gain sweep or unchanged BC/PPO scaling.

## Prior result: explicit clock restores warm-up hold, correction harms noise

Added only opt-in `mode="timed_feedback"` in `research/stroke_controller.py`.
Phase is explicitlymin(one-tickdecisioncalls,599), not inferred from pose.
The gain1body-error correction, norm16/axis128caps, actual600row prior,
source/world-coordinate decoding and three development cases remain fixed.
Default stroke gating unchanged:3600logged old actions/metadata reproduce
exactly. Both modes still reproduce600actual nominal actions/phases; nominal
physical control/observation/reward/telemetry trace exactly matches playback.
Stroke gate settings remain recorded but inactive in the timed mode.

| Reference case | Pure timed recording | Explicit-clock feedback |
|---|---|---|
| Nominal |central+secondary held,(322.586,104),gain83|identical,zero correction|
| Left warm-up |central+secondary held,(322.577,104),gain83|both held,(319.942,104),gain83|
| Noise11105 |secondary only held,(335.292,103),gain82|nohold,(208.585,82.027),gain61.027|

Removing completion gating restores the selected warm-up central hold; it
does not fix everything. Noise feedback loses the secondary hold that pure
playback has and retains less height. All feedback phases reach599, not a
phase stall. Correction acts on579/573post-interventionticks. The reused
three-case central gate remainsfalse, no teacher/corpus/data admission or
learned-policy progress. No claim of general feedback impossibility.
Keep centralX<=335unchanged; the timednoisebaseline remains secondary only.

Fresh12rollouts/7200control+1440reset,0updates/summits/deaths, within immutable
300second owned work bound. All six full same-host backend pairs and six
pinned old timed baselines exact. Independent full raw milestone/control/
perturbation-clock reconstruction passes.311Python tests+JS pass.
Evidence: `artifacts/timed_feedback_probe_20261004T203929123127Z/verification.json`.
Backend copies are fidelity, development cases are not fresh held-out trials.

Independently private PAUSED1791146514.6997206; actual80444390source,
onstate-20261004-v1/onstate_study and its closed deadline unchanged. Ledger
bytes preserved; seven closed estimates$0.4564241866528988, no new paid
reservation, HF write, public release or local learner training. Goal0.

The historical diagnostic, now completed above, inspected corrective segments in
captured noisy playback/feedback and the original planted-hammer-to-body
transfer. Determine whether a contact-aware correction rule is mechanically
justified before proposing it. Query contact is not force or complete
collision response. Use existing traces first, no new gain/cap/tube/nearest
metric sweep or controller retries. A new rule needs fresh frozen bounds/
cases and actual recovery/fidelity before teacher validation, labels or any
paid learning contract. Do not simply rerun unchanged BC/PPO or collect
off-state teacher suffix labels.

## Prior result: ordered stroke feedback preserves nominal but fails recovery

Inspected original PlayerbF/bG: motor request0.4*(pointer-hammer+body+render
offset), change limit40, motor limit50, reach26..102 and real contact solver.
Those physics are unchanged. The new diagnostic `research/stroke_controller.py`
uses only raw217pre-action inputs and resettable private phase. Body/hammer
world-position projection onto the next ordered reference stroke gates at
most one forward row; fixed perpendicular tube26pixels, stationary points
within1pixel/speeds<=2. No nearest-state search, backtracking, forced phase
jump or unconditional elapsed-clock progress.

Adds gain1*(reference body-actual body) to the prior pointer, norm-capped16
pixels then legal128axis limits. This approximates world-target compensation,
not inverse collision control or a guaranteed corrective label. The unchanged
600row prior reproduces all600offline actions/phases and actual nominal
reference/fast trajectory exactly, including the central+secondary hold.

| Reference case | Timed recording | Ordered stroke feedback |
|---|---|---|
| Nominal |central+secondary held,(322.586,104),gain83|identical,phase599,zero correction|
| Left warm-up |central+secondary held,(322.577,104),gain83|nohold,(59.448,20.770),gain-0.230,phase58|
| Noise11105 |secondary only held,(335.292,103),gain82|nohold,(169.478,29),gain8,phase173|

Both perturbed final120phase ranges are constant; after interventions,
correction acts on564/572ticks. Maximum correction norms8.36655/16pixels.
Warm-up final progress-15.6753; noise finalprogress0.939637/perpendicular
distance27.3929, with both completion gates false. These gate states describe
failure, not single-factor causality; progress and correction changed together.
The baseline noise is still outside unchanged centralX<=335, not promoted.
Reject the stroke recipe as corrective teacher: no corpus/data admission,
learning, model improvement or summit.307Python tests+JS pass.

Frozen12rollouts/7200control+1440reset,0updates/summits/deaths, within the
300second work deadline. All six full backend pairs and all six old timed
baseline traces exact. Independent review reconstructs all12full raw
position/velocity/contact milestone traces and verifies every proposed and
actually perturbed legal control against captured pre-inputs and case clocks.
Backend copies are fidelity, not independent successes.
Evidence: `artifacts/stroke_feedback_probe_20261004T202114143143Z/verification.json`.

Independently private PAUSED1791145725.5072744; actual80444390source,
onstate-20261004-v1/onstate_study and closed historical deadline unchanged.
Seven closed estimated costs$0.4564241866528988; ledger bytes preserved,
no paid reservation/remote writes/public release. Full goal remains0.

The historical single-axis ablation, now tested above, kept gain1 body-error correction,
16pixel norm/128axis caps and prior fixed; replace observable-stroke gating
with an explicitly declared physical playback clock. Compare timed-feedback
versus pure playback on the same three development cases. This tests whether
correction can help without deadlocking progress; it is not state-inferred
phase acquisition, a fix, teacher admission or robust learned skill. Freeze
fresh source/rule/case/deadline bounds before any physics. No tube/gain/cap
sweep, arbitrary phase jumps, off-state teacher suffix or learner scaling.

## Prior result: control-history feedback improves one partial climb, not recovery

The frozen second prototype changes only phase-distance features:
`feature_set="control_history"` adds pointer_x/y,last_tx/ty,control_memory_x/y,
last_hammer_distance,last_effort to the original13features. Prior, raw217input,
original3576row RMS, weights4forposition/1elsewhere,8back/12ahead window,
actual recorded actions, reset12001, left warm-up and noise11105 are unchanged.
The original matcher remains the default. Both versions exactly reproduce all
600actual recorded-input/control pairs; this is not off-state label validity.

| Reference condition | Original13feature matcher | Added21feature matcher |
|---|---|---|
| Nominal |central+secondary held,(322.586,104),gain83|identical held result,phase599|
| Left warm-up |nohold,(-3.362,21.996),gain0.996,phase28|nohold,(280.249,79.011),gain58.011,phase280|
| Noise11105 |nohold,(35.640,19),gain-2,phase106|nohold,(33.936,19),gain-2,phase135|

This is real partial climbing progress in one selected warm-up, not a learned
policy or successful recovery. New left/noise phases remain exactly280/135
through the final120ticks. Warm-up final90ticks have body-querycontactfraction1
and speed0, but Y79.011is below both unchanged ledge regions. Noise final90
maxspeed0.44524and contactfraction1 atY19are floor support, not climbing.
Neither perturbed case passes either detector; no corrective teacher/corpus
or learner training is admitted. Stop nearest-feature/window tuning.

Fresh14rollouts comprise nominal timed reference/fast gate plus three cases
times two matchers times two backends:8400control+1680reset,0updates/summits/
deaths. Every full backend trace agrees exactly; all six old13feature traces
also exactly reproduce their pinned historical files, with no baseline drift.
All14full milestone traces independently reconstruct from raw position,
velocity and body-contact telemetry. Backend copies are fidelity, not new
recovery trials.299Python tests+JS pass. Frozen300second work envelope ran
within its deadline; immutable plan/script/prior/source/budget hashes verified.
Evidence: `artifacts/phase_history_probe_20261004T200234917165Z/verification.json`.

Independently private PAUSED1791144426.67216; actual source8044439043a1725dc5911577c85096cd04ddc4ae,
sessiononstate-20261004-v1/modeonstate_study and its closed historical deadline
are unchanged. Seven closed estimates total$0.4564241866528988; ledger bytes
preserved. No paid reservation, remote write or public release. Full goal0.

The historical structural follow-up, now tested above, was to inspect the pointer-to-hammer
servo and these stalled strokes; derive a legal stroke-progress controller
with observable completion gates and state-error action correction, rather
than selecting another nearest-pose metric. Freeze its actual rule, action
limits, tick/deadline bounds and nominal/perturbation cases before physics.
Compare with timed playback and require actual recovery/reference-fast parity
before any labels or new learning contract. No forced arbitrary phase jump,
teacher suffix at unrelated states, metric/window sweep or unchanged BC/PPO
scaling. This design is a hypothesis, not a proven fix.

## Prior result: phase-feedback prototype reproduces nominal but fails recovery

Implemented `research/phase_controller.py`: a non-learning state-matched
trajectory prior, not a corrective oracle. It selects among8preceding/
12following rows of the validated600row nominal demonstration using13existing
body/hammer/contact features, original3576row frozen RMS and fixed weighted
distance. No unconditional clock advance, hidden teacher index, reset
placement, altered physics or learned update. Targets are actual prior
applied controls, legal float32 relative-pointer actions; nearest-state
proximity alone never makes them corrective labels at another state.

The frozen first physical check compares time-indexed versus state-matched
controls in nominal/reset12001, legal left warm-up and fresh noise11105.
Each600tick case runs reference and fast after an exact central-held
time-indexed nominal baseline gate.12rollouts/7200control+1440reset ticks,
0learning,0summits/deaths. All phase/action/raw observation/reward/info/
physical telemetry backend fields match exactly. Copies are fidelity,
not independent recovery successes. No paid reservation or HF write.
All twelve frozen metric traces independently reconstruct exactly from raw
position, velocity and body-contact telemetry, including failed held fields.

| Condition | Time-indexed control | State-matched prototype |
|---|---|---|
| Nominal |central+secondary held,(322.586,104),gain83|identical held result,phase599|
| Left warm-up |central+secondary held,(322.577,104),gain83|nohold,(-3.362,21.996),gain0.996,phase28|
| Noise11105 |secondary held only,(335.292,103),gain82|nohold,(35.640,19),gain-2,phase106|

Do not relax the central X<=335gate for the baseline noise endpoint.
Feedback13feature nearest-phase matching stalls/cycles under both
perturbations: left last120phases27..29 (425unchanged/83backtracks across
600ticks); noise last120phases106..115 (462unchanged/29backtracks).
Nominal offline600recorded-input actions reproduce exactly, as does the
physical nominal run, but that does not establish off-state recovery.
The simpler timed recording is better on these two selected perturbations.
Reject this matcher as a corrective-data teacher; no new corpus or learner
training is admitted.295Python tests+JS pass. New tool/tests/docs committed,
raw failed trajectories remain diagnostic only.
Evidence: `artifacts/phase_controller_probe_20261004T194209476868Z/verification.json`.

The historical next hypothesis, now tested above, was to include pointer and control-history
features (pointer_x/y,last_tx/ty,control_memory_x/y,last_hammer_distance,
last_effort) in the matcher while preserving prior/RMS/window/weights/actions/
test cases. They may disambiguate similar poses mid-stroke; this is a
hypothesis, not causal proof or a fix. Freeze a fresh declaration before
running; no repeated tuning/cutoff search or arbitrary corpus collection.
Only actual physical recovery and fidelity can admit a corrective teacher.

External budget notice was reviewed; cost contents match the committed
seven closed batches and are left byte-for-byte unchanged. Cumulative
closed estimate$0.4564241866528988, no active reservation. Private Space
independently PAUSED1791143260.6853201, same80444390source/onstate completed
session/mode, no configuration/image/deadline change. Goal metric0, no new
learned-policy competence. Continue controller-learning research, not
kernel/transport work or unchanged BC/PPO scaling.

## Previous result: completed comparison; selected-data addition failed

All six runs are complete and independently contract-validated at pinned
dataset `d3fc0808ad5e434b839963529989c6bf4545f739`. Source/game/data, frozen
settings/RMS, exact legal action clocks, real optimizer/source-sample work,
matched-seed initial parameters/reference traces and saved reload flags pass.
Remote summary and `tools.research_goal_metrics` projection equal the
independent review. Durable no-resume claim and all12saved companion
identities are present; same-seed RMS companion bytes match. Binary packages
were not downloaded/reloaded here, so no portable/saved-policy replay claim.

| Recipe | Central holds seeds9/10/11 | Secondary holds | Median retained gains | Final central endpoints |
|---|---|---|---|---|
| Original demonstrations |2/3/2 out of9 each|2/4/3|4.3693/18.3677/11.5412|2/3/2|
| Original plus logged success |3/1/0 out of9 each|3/1/0|13/4/10.5001|2/0/0|

All six nominal central holds fail,0/54final/postclone summits and deaths.
Original worst-seed central fraction2/9; augmented0/9. Both full-climb
fractions0 and first-skill candidatesfalse. Added selected trajectory does
not consistently improve control and worsens this comparison's worst-seed
held-event result. It is not proof that all self-imitation is ineffective.
Do not promote, scale, repeat unchanged, or reinterpret small supervised
error/retained altitude as robust learning. The original recipe also fails.

Two augmented central events are transient: seed9noise5 and seed10noise2
leave after holding.24central/secondary position/contact windows and9final
central-region90tick contact windows checked. Query hits are not forces;
raw velocities are absent from evaluator info, so tracker speed qualification
is not independently reconstructed. The original source/physical benchmarks
remain frozen. This study is structured-case replication, not IID population
statistics or final held-out/upper-route summit verification.

Actual full-comparison work12000BC calls/3072000sample presentations:
2688000original and384000logged.0PPO/training control/reset physics.
108distinct before/after reference rollouts194400control+25920reset ticks;
54final/postclone cases. Preflight and local smokes remain separately
accounted, not counted as learned-policy replication.11checker/goal tests pass.
Evidence: `artifacts/onstate_complete_review_20261004T191902458785Z/complete_review.json`.

Worker completed2026-10-04 19:01:44UTC. Private owned Space independently
PAUSED1791141541.9557095 /19:19:01UTC, rechecked1791141827.4268486.
Same80444390source/onstate session/study mode/ed3a53c3context/original deadline.
Original reservation closes at conservative **$0.0385**,77rounded minutes
including all elapsed time until independent pause verification, even paused
operator gaps. All seven batches now closed at **$0.4564241866528988**.
These are estimates, not actual provider bills or remaining credits.
No new reservation, remote write, restart or source/configuration change.
Goal metric0; researcher remains active, no current access/funds blocker.

Next bounded implementation: prototype a **state-responsive legal corrective
teacher** for reliable first-ledge acquisition. Use the known real hammer-plant
primitive/validated legal trajectory as a prior, but choose/adjust actions
from observed pose/hammer/contact feedback rather than a blindly advanced
time index. This controller is not built or validated yet; no oracle claim.
Freeze its observation/control/resource contract before any rollouts and
validate ordinary-spawn nominal plus declared perturbation recovery on
independent reference and fast backends before new data or learner training.
Only actually applied controls at their exact captured pre-action states can
be corrective labels. Failed examples stay diagnostic; no teacher suffix at
unrelated states, arbitrary extra noisy-success pooling or inverse clipping.
Require demonstrated recovery/target consistency before another matched
learning study. No unchanged BC/PPO extension, kernel loop or paid scaling.

## Previous partial result: added-data benefit reversed; last arm active then

Five complete run contracts pass at pinned dataset
`d797a550c6ae7085fe604542690a59959b3eca13`, last augmented seed11 missing.
Source/game/data, frozen settings/RMS, actual optimizer/source-sample counts,
fresh legal action traces, matched initialization/reference behavior and
durable no-resume claim all validate. Complete original-data cohort fails
the unchanged first-skill/summit gates; augmented cohort is incomplete.
No winner or robust improvement is declared from the partial matrix.

| Arm/seed | Central held | Secondary held | Median retained gain | Final central-region endpoints |
|---|---|---|---|---|
| Original9 |2/9|2/9|4.3693|2|
| Augmented9 |3/9|3/9|13|2|
| Original10 |3/9|4/9|18.3677|3|
| Augmented10 |1/9|1/9|4|0|
| Original11 |2/9|3/9|11.5412|2|

All five nominal central holds are false;0/45final/postclone summits/deaths.
Original cohort worst central fraction2/9, worst full completion0 and no
nominal completion. Seed10 reverses seed9's one extra event: added data
loses held cases, retained median and final ledge support. Its only central
event (`new_action_noise_2`) is transient, ending(520.535,26.521), retained
5.521. Seed9's augmented noise5 transient remains. This one selected
successful trajectory does not show consistent benefit across the observed
seeds. Wait for the last control before closing; even favorable seed11
cannot rescue existing nominal and>=8/9-per-seed first-skill gate failures.
Do not scale or start another data/optimizer experiment while this one runs.

Twenty-four central/secondary qualifying position/contact windows checked;
9final90tick central-region/contact windows pass. Speeds are absent from
evaluator info, so raw velocity qualification is not independently rebuilt.
Query hits are not forces and latched events are not final support.
Actual five-run work10000BC calls/2560000presentations,0PPO/training physics.
90distinct before/after reference rollouts162000control+21600reset ticks;
45final/postclone cases. Saved companion identities/size hashes are pinned
metadata only, not locally downloaded/reloaded or proved portable. Active
seed11's initial parameters match its original peer; no completed active
learning work is inferred.11local checker/goal tests pass; goal metric0.
Evidence: `artifacts/onstate_later_review_20261004T185906597412Z/verification.json`.

At UTCepoch1791140346.597413 /2026-10-04 18:59:06, private Space RUNNING
`original_plus_logged_success_seed_11`, no error, same80444390source,
session/mode/contexted3a53c3 and1791144140.4793909deadline;3793.882seconds
remained. Original$0.06 reservation stays open, closed+reserved estimate
$0.4779241866528988 unchanged. No remote write, new local game/training,
pause, budget renewal, source edit or deadline change. Next: one bounded
terminal/last-arm review and original reservation closure ONLY after durable
artifacts and independently owned PAUSED. Keep the researcher running.

## Previous partial result: one extra seed9 event, not robust improvement

The running comparison has two complete contract-valid seed9 runs at pinned
dataset `0f0ae67493534e4bffc3d8a01ef11ace20f0111b`. All source/game/data,
frozen settings/RMS, legal fresh-case action traces, actual update/source-sample
work and matched initial parameters/reference traces pass the strict checker.
The exclusive durable no-resume claim is verified. Four runs remain missing;
no complete three-seed cohort, skill candidate or full-goal improvement exists.

| Seed9 arm | Central/secondary held events | Median retained gain | Nominal hold | Summits/deaths |
|---|---|---|---|---|
| Original demonstrations |2/9,2/9|4.3693|no|0/9,0/9|
| Original plus logged success |3/9,3/9|13|no|0/9,0/9|

Original arm holds `new_hammer_right` and `new_action_noise_3`; augmented
holds `new_hammer_right`, `new_action_noise_2` and `new_action_noise_5`.
Both finish in the central ledge region in only2cases, with90body-query
hits across their final90ticks. Augmented noise5 held at tick893 but later
left, ending(536.593,60.896), retained39.896. Its extra counted held event
is transient; the original noise1 ends above the ledge at(306.283,124.032),
retained103.032 but does NOT satisfy the held gate. Endpoint height is not
skill. Both no-noise trials fail: original(137.660,24), augmented(21.867,21).
Higher one-seed counts/median are not robustness, population statistics or
proof of a beneficial data recipe. Keep all remaining controls unchanged.

Independently checked qualifying90tick position/contact windows:
original held ticks629/1064 with89body-query hits each; augmented850/1140/893
with90/90/88hits. Query hits are not forces. Exact velocities are not exposed
in evaluator info, so speed qualification remains the frozen source tracker,
not a claimed independent velocity reconstruction. All actual legal actions,
clock, latched held fields/outcomes and retained origins validate.

Actual verified work for these two completed runs:4000BC optimizer calls,
1024000sample presentations (896000original+128000logged),0PPO and0training
control/reset ticks.36distinct executed before/after reference rollouts,
64800control+8640reset ticks;18final/postclone cases,0summits/deaths.
Four completed saved companion identities/size hashes are pinned by metadata,
same-seed RMS companion bytes match. Model/RMS binaries were NOT downloaded
or reloaded here; trainer's saved-reload checks do not prove portable replay.
Active seed10 has only its initial manifest/RMS in this snapshot; no completed
work is inferred.11local checker/goal tests pass; conservative goal projection0.
Evidence: `artifacts/onstate_partial_review_20261004T183915603589Z/verification.json`.

Actual private Space is RUNNING `original_demonstrations_seed_10`, same
source80444390/session/mode/contexted3a53c3. The real epoch check at
1791139109.743019 is UTC2026-10-04 18:38:29, leaving5030.736seconds before
deadline1791144140.4793909 (20:02:20UTC). Use the configured epoch/UTC clock,
not date-only interface notices, for expiry decisions. No pause, upload,
source/configuration/deadline change, reservation closure or renewal.
Original$0.06 remains open, closed+reserved$0.4779241866528988 unchanged.
Next: one bounded later snapshot of remaining seed10/11 complete controls,
claim/progress/saved metadata and physical outcomes. Only terminal/failure/
actual epoch expiry permits closure after verified owned PAUSED.

## Previous launch: preflight passed; matched comparison started

All eight declared Linux preflight checks are complete and independently
validated at pinned dataset `53b2f8dec8f361f193a14a299d466caab711ed30`.
Owned private Space was independently PAUSED1791137892.5876534 before the
intentional study transition. Exact source/game/data/RMS, original legal
timing/controls, physical metric contracts, same-seed initialization/reload,
resources and both small smoke runs pass. The known terrain descriptor
disagreement at(-80,-30) remains documented, not hidden or a physics change.

Fast/reference numeric physics errors are0 across the declared fidelity
cases; six contact-rich timing cases match observations/rewards/telemetry
exactly and production evaluation agrees. Placement tests are diagnostic
only, never task progress or training labels. Two smoke arms share exact
initial weights/untrained traces, preserve RMS/value/logstd/PPO and saved
reload, using16BC calls/1024presentations. Four128tick reference smoke runs
stay at(0,21), retained0, no holds/summits/deaths; these are not the full study.
Linux stack Python3.11.17/NumPy2.4.3/Torch2.6.0+cpu/SB3 2.7.1/one thread.
Effective8CPU/32GB capacity and>=12GiB available RAM pass. Worst measured
reference fixture0.00956727s/tick gives a descriptive linear108rollout
projection1859.88seconds, not a completion guarantee. More than twice that
projection plus300seconds remained at launch; CPU XL is unnecessary.
Evidence: `artifacts/onstate_preflight_review_20261004T181812585650Z/complete_review.json`.

The frozen actual six-run comparison is intentionally started on the SAME
session `onstate-20261004-v1`, mode `onstate_study`, source
`8044439043a1725dc5911577c85096cd04ddc4ae`. New passed context
`ed3a53c349d08380401bc2a27d466ea58c378210` was published while PAUSED, then
only context/mode changed and one intentional restart requested. No source,
hardware, scientific controls, data, budget or deadline changed. Original
start1791136940.4793909/deadline1791144140.4793909 (**20:02:20UTC today**),
$0.06 reservation and closed+reserved estimate$0.4779241866528988 remain.
No second reservation, extension or resumed checkpoint.

One pinned study startup at1791138266.1662903, dataset
`392854a3fe7ed9214d79fdee38d3ecb8b9b390f7`, shows actual RUNNING,
`onstate_dispatch`, no error. Source/game/data and actual variables are
exact. No durable execution claim appears in that snapshot yet, and no
completed learner work/reference outcome is inferred. Restart's immediate
return said PAUSED, but this independent snapshot proves running dispatch.
22local admission/result/worker/trainer tests pass. Goal metric stays0.
Evidence: `artifacts/onstate_preflight_review_20261004T181812585650Z/study_startup_verification.json`.

Next bounded review: keep active source/variables/deadline untouched; pin
later artifacts and inspect claim, flushed BC call/source-sample prefixes,
complete saved model/RMS metadata and strict six-run checker/reference
outcomes. Report held events, retained final height/deaths/summits and actual
control/reset/update work, not supervised error or peaks. At terminal/failure/
deadline preserve durable artifacts, independently verify owned PAUSED and
close the original reservation. Never resume, renew or skip missing arms.
Standard aggregate still cannot verify final held-out summit/upper-route
fidelity/saved-controller goal, even if a first-skill candidate emerges.

## Previous launch: fresh Linux preflight, full training not started then

Fresh session `onstate-20261004-v1` is running only `onstate_preflight`.
The learning hypothesis remains original demonstrations versus original plus
logged successful learner-state controls, matched budgets/seeds/RMS and fresh
reference trials. This launch is a correctness/transport preflight, not the
full six-run comparison or evidence of improved climbing.

Current deployed source `8044439043a1725dc5911577c85096cd04ddc4ae`,
context `0675220a2a01544e20fdee9bfc4e2f01aa168f00`, admitted data revision
`b1d44bd3f157e0a00809116c7b3c1e085401b6a1`. Fresh 448-file reviewed source bundle
and exact unchanged 5376-row corpus were published while independently PAUSED.
Authenticated ownership, both private targets, 8vCPU/32GB CPU Upgrade,
one replica and paid never-sleep default were verified. Official
`hf://docs/hub/spaces-gpus.md` reverified $0.03/hour and minute billing.
22 local admission/result/worker/trainer guards pass; source/data hashes
match the previously 289-test+JS/end-to-end-smoke validated implementation.

One new immutable reservation covers preflight AND any later admitted study:
start1791136940.4793909 / **2026-10-04 18:02:20UTC**,
deadline1791144140.4793909 / **2026-10-04 20:02:20UTC**,
maximum **$0.06** including startup, CPU Upgrade/one replica. Six old batches
stay closed at estimated $0.4179241866528988; closed plus reserved
**$0.4779241866528988**, below $10. Estimates are not bills or remaining credits.
Do not create a second reservation for the study or extend this deadline.

One pinned startup snapshot at1791136999.7649724, dataset
`3416e48bb72d84c475e3f1e1b8f70f41578e95d6`, shows actual **RUNNING**,
durable **onstate_admitted**, no error. Actual source/session/mode/context/
deadline/max-hours match admission; all source/game/data fingerprints are
independently exact. No complete checks or physical results are yet validated.
Do not infer successful preflight, game exposure or learned control from
startup admission. Full training has not been requested. Persisted operator
ticket has `preflight=None`; prospective local validation is not passed
remote evidence. No running image, variables, deadline or queue edits.
Evidence: `artifacts/onstate_deployment_20261004T175845470617Z/startup_verification.json`.

Next bounded review: inspect one pinned later snapshot for all eight declared
checks, source/data/RMS/fidelity/smoke/resource reports and exact physical work,
plus independently verify PAUSED. Only durable complete passed preflight and
PAUSED permit a new matching study context and intentional `onstate_study`
restart within the SAME deadline/reservation. Failure/interruption/deadline
requires durable artifacts and owned PAUSED verification, then ledger closure;
never silently resume, relaunch a failed preflight or renew its cap.
No full training or physical skill promotion from this startup record.

## Previous implementation: remote learning runner ready for fresh preflight

The frozen original-versus-added-successful-data comparison now has its
Linux-only execution path, private worker and strict six-run result checker.
The scientific conditions remain fixed: seeds 9/10/11, actor-only 2000x256,
original RMS/architecture, 256old versus192old+64logged per batch, and fresh
reference cases. Only the operational admission description changed.
No full study, paid preflight, source upload or new reservation has launched.

`research/onstate_execution.py` binds the new `onstate-*` session, source,
data archive, passed preflight, two-hour/$0.06 envelope, cumulative ledger,
live direct parent PID/creation time, exclusive durable claim and fresh paths.
Old imitation permits cannot admit this work. Credentials and browser
attachments are stripped from children. Interruption/failure stops scheduling;
no checkpoint continuation or rerun in-place. The existing immutable-deadline
and cleanup-reserve protections are reused.

`research/onstate_train.py` never runs training physics or PPO. Its training
interface rejects reset/step. Only fresh owned original-renderer reference
evaluation controls the game. Completed BC prefixes/source presentations are
flushed to JSONL, and a partially failed warm start is marked used before
optimization so it cannot silently retry. It verifies frozen RMS,
value/logstd/PPO state and saved parameter/prediction reload.

`research/onstate_campaign.py` checks actual work, source/data/dependencies,
fresh legal action-noise clock, control/reset totals, matched-seed initial
weights/reference traces, frozen physical holds, retained height/deaths/summits.
Only complete three-seed cohorts can form candidates. Its projection uses
`tools.research_goal_metrics` and cannot verify final held-out completion.
`deploy/onstate_worker.py` adds `onstate_preflight` and `onstate_study`,
eight exact preflight checks, source-private bounded downloads,20second
durable backups, automatic pause even if owned cleanup raises, and no resume.
Core old timing evaluation defaults remain the unchanged standard cases;
the new explicit cases argument does not alter historical checks.

Two bounded actual seed9 CLI smokes passed on the original reference renderer.
Four128tick rollouts all end retained gain0, no central/secondary holds,
summits or deaths. Initial policy hashes and both untrained traces are exact.
Actual512control+960reset ticks,16BC calls/1024presentations,0PPO/full-study work.
These short lightly fitted policies show no new climbing ability; they only
validate the pipeline, not the frozen1800tick skill hypothesis. All289Python
tests plus JS collision checks pass; no unresolved test failure.
448file reviewed bundle `artifacts/hf_bundle_20261004T173335214453Z/` not uploaded.
Evidence: `artifacts/onstate_execution_20261004T172829900864Z/verification.json`.

Private Space independently PAUSED1791135286.9078948, same7be7d58dsource,
noise-probe session/mode/context/deadline. All six reservations stay closed
at estimated$0.4179241866528988, no new spend. Goal metric remains0.
Next bounded management step: verify current CPU Upgrade price/PAUSED source
ownership, reserve a fresh <=2hour/<=0.06USD on-state session, publish the
tested source, unchanged admitted data and preflight context while PAUSED,
then intentionally start only `onstate_preflight`. Require durable complete
eight-check passed preflight and independent PAUSED before a matching passed
study ticket/mode restart. Preserve the original session deadline through
preflight and study; no automatic training from an incomplete/failed preflight.
Do not reopen any old closed session or expand budgets silently.

## Previous implementation: next learning data and comparison, smoke only

The next controller-learning comparison now has an admitted data path and a
frozen scientific contract. It compares original demonstrations alone with
original demonstrations plus controls actually applied during the selected
successful learner trajectory. This is preparation, not improved climbing:
no new physical rollout or full study training ran, and the goal metric stays 0.

`research/onstate_data.py` derives and safely loads 5376 raw pre-action examples:
3576 eligible original rows and 1800 captured learner-state rows. All reviewed
source files and component arrays are SHA-bound. The original RMS is fitted
only on the original 3576 rows, verified exactly and frozen. Logged controls,
physical row indices, global noise clock and normalized input continuity are
checked. Raw replay samples normalize exactly to the successful feedback
inputs; clipped inputs are never inverted. Source IDs avoid treating the
reference/fast copies as independent examples. All targets and the one
shared-input ambiguity remain visible, with no averaging or silent cleanup.

`research/onstate_study.py` freezes seeds 9, 10, 11 and two fresh actor-only BC
arms. Both use architecture [256,256], the same seed initialization, 2000
updates x256 samples (512000 presentations) and lr 0.001, with no PPO.
Original-only batches draw 256 original examples; augmented batches draw
192 original and 64 logged examples, uniformly with replacement within each
source, then shuffle. Value/logstd/PPO state stays untouched. Equal calls and
sample counts do not imply equal FLOPs or wall time. Nine predeclared reference
cases use nominal reset 10001, new legal warm-ups (+/-0.625,0.375)x3 and noise
10100..10105. Existing noise 8105 is selected development/training evidence,
never validation. Central nominal/all-seed and 8/9 gates stay unchanged; a
ledge candidate cannot verify the summit or final held-out goal.

The shared `warm_start` supports this data path only for <=8x64 pipeline smokes.
Full on-state work is refused before old imitation permits can authorize it.
Two actual seed 9 smokes have identical initial policy hashes, exact saved
parameter/prediction reload and unchanged original RMS/value/logstd/PPO state.
Actual 16 BC calls/1024 presentations: original arm 512 old, augmented 384 old +128 new;
0 game/reset ticks, 0 PPO calls or full-study updates. MSE falls in each smoke,
but these are different data distributions and do not rank physical skill.

All 266 Python tests and JS collision checks pass. The first archive test used
a high-entropy synthetic fixture larger than the immutable 8MiB cap; its
compressibility was corrected without relaxing the loader. Read-only target
tensors now copy before conversion to avoid unsafe writable tensor aliases.
The 440-file allowlisted bundle includes data/study/tests/docs and was not uploaded.
Derived data SHA c2d0895d56706d3c0797effae5018928229866d95c22bb72c42706876f43c268.
Evidence: `artifacts/onstate_pipeline_20261004T170617730137Z/verification.json`.

Private Space independently PAUSED at 1791133809.5616088, same `7be7d58d` source,
noise-probe session/mode/context and deadline; no variable/source/session write.
All six reservations stay closed at estimated $0.4179241866528988. No new spend
or paid launch. Proposed next execution cap is 2 hours / $0.06 on CPU Upgrade,
one replica, inside $10; this proposal is NOT a reservation/admission.

Next bounded implementation: source/data/contract-bound Linux trainer and
worker admission plus a strict six-run checker, reusing existing durable
claim/deadline/backup/pause protections. Then passed remote preflight, new
source/context/session/reservation and immutable deadline before intentional
launch. Do not use old imitation permits or resume closed sessions. No more
data-coverage/kernel/transport probes, new PPO or blind scaling.
See `docs/ONSTATE_LEARNING.md` for the comparison and execution boundary.

## Previous result: useful new state coverage, not improved climbing

The offline audit compares 1800 successful full-noise learner inputs against
3576 eligible original demonstration inputs under the exact same frozen RMS.
Only 1 learner input is bitwise identical to an original input. Median nearest
distance is 7.6021 in Euclidean normalized-policy-input units, versus 0.26765 for
original demonstration leave-one-out neighbors. Base/history-only and
terrain-only medians are 3.9915 and 4.5977. These are descriptive distances,
not calibrated out-of-distribution tests or proof of the failure's cause.
The successful run offers candidate data at different states, not evidence
that it supplies corrective expertise or will generalize.

The shared starting input increases its logged action range from 0.02806386
to 0.03898251 (normalized control units, about 4.9898 pointer pixels). There is
still 1 exact-input conflicting group in the merged 5376 rows / 5372 groups;
all 1800 learner inputs are unique. Different noisy applied labels at an
identical input are ambiguous targets, not proof that no legal action works.
Do not silently replace targets or describe the selected noisy run as an oracle.

39 learner rows contain 43 clip-bound feature elements (limit 10); 66 original rows
also touch a clip bound. Never invert clipped inputs to fabricate raw data.
A separate exact offline linkage finds the previously captured 1800 raw replay
inputs, normalized inputs and actually applied controls all match the successful
feedback probe exactly. Those raw inputs were captured during the prior
validated legal recorded-action replay, not recovered by inversion. Thus
no new replay/transport work is needed to obtain candidate raw samples.
Their dataset admission and new learning contract are still unimplemented.

Next controlled learning test: fresh matched actor-only BC arms using original
demonstrations versus original plus these actual logged learner-state controls.
Keep the original frozen RMS, architecture, initialization per seed and total
optimizer/sample budgets identical; predeclare mixture weights, handle label
ambiguity visibly and avoid additional PPO until this data hypothesis is tested.
Use three fresh training seeds and newly frozen reference perturbations.
Noise 8105 is now development/training-selected evidence and cannot be independent
validation for this candidate. Repeating that run is an overfit diagnostic,
not the success criterion. The unchanged first-skill and summit conditions
remain physical gates; final held-out full-climb verification remains necessary.

Current work: 0 new game/reset ticks and 0 updates, no paid reservation/HF write.
Live monitor rechecks PAUSED/noise_probe_complete, same terminal `12c5b0fa`.
All six batches stay closed at estimated $0.4179241866528988, not a provider bill.
25 repository unittest data/cloning/study/goal safeguards pass; a first pytest
invocation could not run because pytest is not installed. No package installed.
Bounded audit executed successfully and 24 nearest distances independently checked.
Goal metric remains 0; no improved saved controller has been produced.
Evidence: `artifacts/learner_coverage_audit_20261004T163822133756Z/audit.json`
and `raw_link.json`. No new training/session/source deployment launched.

### Communication contract

The user reports feeling left out and confused by machinery-heavy updates.
Future updates must lead with: what the player can do, what failed, what this
step actually changed, and the next learning comparison. Separate diagnostic
progress from skill progress. Say explicitly when no training is running or
when another check cannot itself improve control. Do not lead with hashes,
commit IDs, test counts or deployment plumbing. Keep research autonomous.

## Previous result: full perturbation holds; either isolated segment fails

`noise-probe-20261004-v1` completed all8legal feedback rollouts and auto-paused.
Original nominal/full-noise saved-action/body/outcome baselines reproduce
exactly; all4reference/fast comparisons match on actions, observations,
rewards/info and pre/post physical telemetry. Every applied action is independently
recomputed from the frozen global masked noise stream. Nominal/late and
full/early first60tick prefixes match exactly. All frozen held-event summaries
are reconstructed from original per-tick states. No placement or learning.

What the player actually did (same selected clone7/reset1001/noise8105):

| Condition | Central/secondary held event | Retained final gain | Final X,Y |
|---|---|---|---|
| No extra noise | no/no |0.5291|62.2242,21.5291|
| Noise throughout |yes/yes|81.6639|334.4829,102.6639|
| First2seconds only |no/no|10.5361|268.7793,31.5361|
| After2seconds only |no/no|7.5005|226.1886,28.5005|

Full noise latches both at1585ticks/52.833333seconds,90body-query hits in its
90tick window,maxspeed0.82809209255. No summits or deaths in any case. Query
hits are not forces. These are4conditions duplicated for backend fidelity,
not8independent learned successes. Neither segment alone suffices for this
selected trajectory; no unique helpful action, general recovery mechanism,
population robustness, corrective oracle or full-goal result is established.

Actual14400control+1920reset ticks,0updates. Terminal pinned dataset
`12c5b0fa35ad89a4001a0ee886b142a7e8b2373e`, worker complete16:03:43UTC;
independently PAUSED1791130711.5065403 and rechecked after offline review.
Same7be7d58dsource/mode/context, original deadline1791130828.5921772 unchanged.
Reservation closes at conservative **$0.0095**, rounding persisted elapsed to
19minutes including all time until independent pause verification, not actual
provider bill. Cumulative closed estimates **$0.4179241866528988**, no active
reservation or new batch.18control/admission/goal tests pass. Goal metric0.
Evidence: `artifacts/noise_probe_review_20261004T161832060135Z/complete_review.json`.

Next meaningful learning step: audit successful full-noise learner-state
coverage and valid logged applied-action labels against existing demonstrations,
then design a fresh gated on-state self-imitation/robust recovery comparison.
Only controls actually applied at their exact pre-action inputs may become
labels; never use a time-indexed teacher at unrelated states or assume random
noise is an expert. One successful trajectory is not enough to promise
generalization. No more kernel/transport experiments, repeated cheap cutoff
searches, unchanged PPO extension or blind scaling. Keep the Linux evaluation
stack and original physical/held-out/summit gates fixed.

## Previous launch: four-condition Linux control diagnostic

Fresh session `noise-probe-20261004-v1`, mode `noise_control_probe`, is admitted
and intentionally restarted on the owned private CPU Upgrade/never-sleep/
one-replica Space. The player experiment compares nominal, fullnoise8105,
first60ticks-only noise and noise after tick60. It asks whether the selected
successful held trajectory depends on early alignment or continuing correction.
It is exploratory, not new training, held-out skill or full-climb promotion.
Exact nominal/full-noise saved-feedback baselines must pass before interventions.

Source `7be7d58de881f1b9e4c69c87958e1818d4693d8b`, context
`ef63e649fdd60ef045a01b98519c5b064e2fa420`, inputs
`c29033b9937ef9d3e074d3c2d2f28d2adaefd303`. Tested434file bundle and the original
scientific plan/model/RMS/baselines plus explicit transport amendment were
published while independently PAUSED. No closed session resumed.
Immutable start1791129628.5921772/deadline1791130828.5921772,
**2026-10-04 16:20:28UTC**, <=20minutes including startup and **$0.01** reserved.
Official CPU Upgrade price$0.03/hour reverified2026-10-04. Closed estimates
$0.40842418665 plus reservation=$0.41842418665 under$10; estimate, not bill/credits.

One pinned startup snapshot at1791129705.3538482, dataset
`258c7a3f8ba7e7e5a5b557e9a75395cd88488aaf`, shows actual **RUNNING** with durable
`noise_probe_claimed`, no error. No report yet; do not infer actual game work,
baseline reproduction, held outcomes or intervention effects from its claim.
Eighteen control/admission/goal guard tests pass. Active image/variables/
session/context/deadline remain unchanged after launch.
Evidence: `artifacts/noise_probe_deployment_20261004T155845805666Z/startup_verification.json`.
Next bounded review: pin a later dataset revision and examine actual legal
actions/control-reset work, exact baseline/backend gates, held events,
retained endpoints/deaths/summits and early/late contrast. At terminal/failure/
deadline verify durable artifacts and independent PAUSED, close reservation;
never silently resume, extend deadline, change running deployment or promote
post-hoc selected cases as robust learned control.

## Previous implementation: Linux control probe ready, no execution then

Fresh mode `noise_control_probe`/session prefix `noise-probe-*` now reuses the
original `tools/imitation_noise_probe.py` core through an owned Linux wrapper.
No scientific conditions, model/RMS, noise clock, detector or exact saved-
feedback/reference-fast gates change. Missing baseline comparisons, expanded
work or interventions after failed baselines are refused. Matching recorded
Linux dependencies and no desktop/browser attachments are checked before
fresh owned headless instances; child credentials/attachment variables removed.
Per-case control/reset totals, no-resume claim, paths/source/tool/provenance,
absolute budget,20second backups and cleanup/auto-pause are tested.

**Explicit transport amendment, not silent plan editing:** original local
zero-new-paid/no-session-change execution envelope stays in its immutable file.
Demonstrated host/stack numerical differences motivate a separately declared
fresh Linux execution envelope: <=20minutes/<=0.01USD including startup,
<=600second child including30second cleanup,8cases/14400control+1920reset ticks,
0updates. The original scientific plan SHA remains
aeb940ac3fb32209de78795cb83ebbabc69166c28ff85c47ba10651e92fe3d7c.
Declaration: `artifacts/linux_noise_transport_20261004T153843356715Z/transport_declaration.json`.

All256Python tests plus JS pass.434file allowlisted bundle built at
`artifacts/hf_bundle_20261004T154829964910Z/`, not uploaded. Actual new control/
reset/training work0. Space last independently PAUSED1791128916.506885, same
ce53b512source/inference completed session/mode/deadline; all reservations
closed at estimated$0.40842418665. No new reservation, HF write or deployment.
Evidence: `artifacts/linux_noise_transport_20261004T153843356715Z/verification.json`.
Next: verify current pricing/PAUSED ownership, reserve a unique fresh bounded
physics-only session, publish this tested bundle plus pinned original plan,
model/RMS and9.059MBbaseline JSON/context/amendment while PAUSED, intentionally
launch only its new mode. Require genuine nominal/full-noise saved-feedback
reproduction before early/late interventions. Stop on mismatch, do not skip
gates or continue a partial case. No blind scale, kernel tuning or goal promotion.

## Closed previous matched-host inference: validated and PAUSED before this probe

Fresh `inference-20261004-v1` completed its3600inference presentations,
0game/reset/training ticks, and auto-paused before the first startup snapshot.
All private source/data/context/dependency/claim/grant/work contracts pass.
Actual source `ce53b512e2ed0a2eb0a41da63a88f59e65c18634`, mode `inference_probe`,
context `25d7cbd21967f956fafc5dd1e2b34b66352dfb7a`, fixture revision
`3208843a8632eaafebb3136f0628ae562b7395fa`, complete result revision
`498527aa104591beda94b2cf3bac69c1fbf2d9f7`. Source was the tested429file bundle;
publication/configuration occurred while independently PAUSED, then one
intentional restart. No existing batch was resumed.

**Host/stack numerical difference is now demonstrated on identical normalized
float32 inputs and byte-identical model tensors.** Linux predictions match
all1800historical raw predictions exactly; Windows differs on1658/1800inputs,
maximum2.980232238769531e-7, firstaction X0.4903483986854553 versus
Linux0.4903484582901001. Both hosts repeat singleton outputs exactly, and
saved-RMS raw normalization is exact across hosts. Input SHA
d398647de2f561181993b387f7b80df66a31c37fad67feffdc4f20c6a82d329a and
parameter SHA bfaa256665fbcb52fe8b01603db98f62245abc0f5cdef2dc3734a27337005c7f.
WindowsPython3.11.9/Torch2.6.0+cu124 CPU versus LinuxPython3.11.17/
Torch2.6.0+cpu, bothNumPy2.4.3/SB32.7.1/AVX2/one thread: this isolates the
host/stack contribution, **not Torch build alone**, nor a historical full-input
proof or specific feedback-hold failure cause. No new skill, held-out,
upper-route or summit outcome. Goal metric remains0.

Reservation start1791127352.9995596, unchanged deadline1791128552.9995596
(2026-10-04 15:42:32UTC), cap$0.01/20minutes including startup. Independently
PAUSED1791127420.855593, rechecked1791127558.0345054. Reservation closes at
conservative **$0.001**, rounding the67.856second persisted elapsed interval
up to2provider minutes; actual bill unknown. All closed estimates now
**$0.4084241866528988**, no active reservation or next batch. Hardware stays
requestedCPUUpgrade/never-sleep/one replica. Seventeen admission/goal tests pass.
Evidence: `artifacts/inference_deployment_20261004T152045604879Z/complete_review.json`.

Next: implement/admit the already frozen nominal/full-noise/early/late noise
control diagnostic on the matching Linux stack, fresh physics-only session,
zero updates,<=8rollouts/14400control+1920reset ticks/600seconds. Keep its exact
saved-feedback baseline gates first; this inference-only result is **not**
permission to skip them. No kernel tuning or local Windows feedback retry.
Use fresh tested source/context/deadline/reservation and independent pause,
never restart this completed inference session. Then act on alignment/
continuing-recovery evidence with robust primitive control, not blind scaling.

## Previous implementation: inference-only comparison ready, not deployed then

`tools/matched_host_inference.py` and `deploy/inference_worker.py` implement
the frozen1800input/two-singleton-pass comparison with0game/training work.
Private mode `inference_probe` accepts only fresh `inference-*` reservations,
<=20minute immutable startup deadline,<=120second child and<=$0.01 within$10.
Owned hash-bound NPZ/model/RMS metadata are checked before deserialization;
ZIP member sizes and NPY headers/shapes/dtypes are checked before allocation.
Direct parent PID/creation time, source/tool/provenance, output paths, grant
hash and durable no-resume claim are bound. Credential-free children,20second
backups, bounded HF requests and cleanup/pause paths are tested. Repeated,
interrupted, failed or completed sessions never dispatch again. No browser
or trainer path is dispatched, and the monitor reports inference separately.

All246Python tests plus JS pass;429file allowlisted bundle built locally at
`artifacts/hf_bundle_20261004T151054432121Z/`. Initial mocked-dispatch test
used an incorrect argument slice; corrected fixture passes, no real worker
failure or training occurred. Real bounded secret-stripped local pipeline:
3600flushed inference presentations, raw-RMS normalization, archived singleton
predictions and repeat predictions all exact. Parameters/timestep/RMS and
files unchanged;0control/reset/optimizer work. LocalPython3.11.9/Torchcu124 CPU
is explicitly **not** the proposed Linux3.11.17/Torch2.6.0+cpu comparison.
Subsequent source-grant safety-only additions are fixture-tested; original
executed tool hash is preserved separately from final bundle hash.
Evidence: `artifacts/matched_host_pipeline_20261004T150755974935Z/verification.json`.

Space independently PAUSED at1791126722.6764882, same95a8e311source,
imitation completed session/mode/deadline. Estimated total$0.40742418665, all
reservations closed. **No HF upload, source/configuration change, reservation
or remote inference launch.** Goal metric remains0.
Next: verify current CPU Upgrade pricing and fresh admission, reserve unique
inference session <=20minutes/<=0.01USD including startup, publish tested private
bundle and exact numeric fixture/operator context while PAUSED, then launch
only this new inference mode. Never restart/renew closed imitation. Require
actual dependency/source/data/work and independent PAUSED evidence afterward.
Use `docs/INFERENCE_DIAGNOSTIC.md` and the frozen matched_host_plan.json below.
Do not prolong kernel investigations or blind training scale after this one
matched-input isolation; prioritize perturbation-robust reactive recovery.

## Previous corrected replay: recorded hold and physical portability verified

Fresh v2 recorded-control replay completes1800ticks/backend. All declared
remote physical fields match exactly throughout; local reference/fast raw and
normalized observations, diagnostic predictions, applied controls, rewards/
info and pre/post telemetry agree exactly. Original recorded controls alone
drive physics. Both detectors latch at tick1585/52.833333seconds; final
`(334.4829332500256,102.66391274492042)`,retained81.66391274492042.
Independent90tick windows have90body-query hits,maxspeed0.82809209255,
X334.15169..334.48293,Y102.52794..103. No summit/death. Query hits are not forces.

This reproduces one selected recorded trajectory, not two independent learned
successes, saved-controller robustness, held-out validation or full climbing.
Local off-policy predictions differ from historical raw predictions by at
most2.980232238769531e-7 normalized units/3.8147e-5pointer pixels. Remote full
observations were not recorded, so equal historical inputs or a Torch-build
cause remain unproven. Extra cross-host reward differences reach1.1102e-16;
they are diagnostics. Original causal saved-feedback baselines remain blocked.

Actual3600control+480reset ticks,2rollouts,0updates; frozen weights/RMS unchanged.
Saved-RMS normalization of all1800raw inputs exactly reproduces captured
normalized inputs. A safe numeric1800x217matched-input NPZ is553101bytes,
SHA455b95f026e78e64b01ea37326f420e76bb45bf39f5eda193118ee24d3cc19ab.
The old84+120failed attempt is preserved separately and unchanged.
23focused tests,4comparison regressions,control/capture fixture and JS pass.
PAUSED independently1791125021.4120429; same private source/session/mode/
deadline, no remote writes or paid reservation, estimated total$0.40742418665.
Evidence: `artifacts/imitation_recorded_action_v2_20261004T143756537682Z/verification.json`.

Next frozen design: one inference-only matched-input Linux/Windows comparison,
1800samples/two singleton passes/3600inference presentations,0game ticks or
updates,max120worker seconds. Implement/test a fresh private source/context
mode before any deployment; no browser/trainer dispatch. Any future CPU
Upgrade admission requires verified pricing, unique <=20minute immutable
deadline and <=$0.01 reservation including build/preflight, backed-up outputs
and independent auto-pause. **Nothing is reserved, uploaded or launched now.**
Plan: `artifacts/imitation_recorded_action_v2_20261004T143756537682Z/matched_host_plan.json`.
Then prioritize perturbation-robust reactive recovery/primitive preservation,
not blind BC/PPO scaling or repeated kernel tuning. Goal metric remains0.

## Previous recorded-action attempt: operator comparison-scope failure

Frozen v1 replay stopped at tick84 in its reference case before fast ran.
The operator compared **all** remote info fields, exceeding the declared
physical gate: reward_potential_after differs by1.734723475976807e-18.
BodyX/Y, retained gain, body/hammer query hits, latched held flags,
summit/death, physical-step count and truncation match exactly for all84ticks.
Recorded applied controls match exactly. Preserve the raw failure status;
it is not evidence that recorded physics diverged.

Actual work84control+120reset ticks,1partial rollout,0updates. At abort
pose `(-29.3055032,25.5130490)`,retained4.513049,both holdsfalse,no summit/death.
Off-policy prediction difference over this prefix is at most8.9407e-8
normalized units, but missing remote full observations still prevent a
cross-host equal-input or Torch-build cause claim. No full hold/replay result.
Evidence: `artifacts/imitation_recorded_action_20261004T141840833438Z/verification.json`.
23focused Python tests, JS collision checks, recorded-control/terminal capture
fixture and4explicit-comparison regression tests pass. Original attempted
script/report remain unchanged; no extra physics or in-place retry occurred.
Space independently PAUSED at1791123836.0914898 with unchanged source/session/
mode/deadline. All reservations stay closed; estimated total$0.4074241866528988.

Next: fresh v2 replay with **explicit original physical fields**, not a
numerical tolerance. Cross-host additional reward fields are diagnostics;
same-host reference/fast raw/normalized inputs, predictions, reward/info and
pre/post physical telemetry remain exact gates. Max2cases/3600control+480reset
ticks/300seconds/0updates or paid work. Keep the prior84+120exposure separate,
use fresh ordinary resets/output, never resume/continue the partial instance.
The original causal saved-feedback baseline remains blocked. No promotion,
placement, corrective-oracle claim or blind training scale.
Unlaunched plan:
`artifacts/imitation_recorded_action_20261004T141840833438Z/corrected_replay_plan.json`.

## Previous bounded diagnostic: archived-input inference is repeatable

Offline clone7 inference used512archived pre-action normalized217-feature
float32 inputs (256nominal/256noise8105), eight frozen variants and4096total
inference presentations. Default one-thread singleton, repetition, threads2/4,
MKLDNN disabling and deterministic-algorithm mode reproduce local archived
actions **exactly**. Batch8/512 differ by at most1.3411e-7/2.3842e-7 normalized
action units (1.7166e-5/3.0518e-5pointer pixels). This demonstrates batch-shape
numeric sensitivity, not a solution to cross-host portability or lost holds.

The remote study evaluation did **not** record full observations. Comparing
local-input predictions to remote actions gives up to0.0480786normalized units,
but those inputs are unverified and may differ through feedback. Do not label
that number equal-state error, Torch-build causality, or evidence of corruption.
Weights/timestep and saved RMS bytes are unchanged;0control/reset/training
ticks, no new paid reservation or remote write.23focused tests pass.
Private Space source/session/mode/deadline are unchanged and PAUSED at
1791122563.818163; closed estimate stays$0.4074241866528988. Goal metric0.
Evidence: `artifacts/imitation_fixed_input_20261004T135949710988Z/verification.json`.

Next frozen step: replay only the recorded full-noise8105 **applied** controls
from reset1001 on reference/fast, capturing raw/normalized pre-action inputs
and off-policy predictions. Max2rollouts/3600control+480reset ticks/300seconds,
0updates/new paid work. Require exact recorded physics/outcomes and backend
fields; stop on mismatch. No predicted action may feed physics. This is a
forensic recorded trajectory, not saved-controller competence, held-out skill,
corrective oracle, or permission to bypass the blocked causal-feedback gate.
Plan: `artifacts/imitation_fixed_input_20261004T135949710988Z/recorded_action_plan.json`.

## Previous local diagnostic: saved-policy portability gate failed

The frozen clone7/reset1001 prefix/suffix probe ran only its four baseline
rollouts (nominal/full-noise8105, reference/fast). Recorded local observations,
actions, rewards, info and pre-tick telemetry agree exactly across backends.
Both baseline first predictions differ from their remote recording by
`5.960464477539063e-8` in action X. Byte-verified model/RMS identities match,
and saved RMS is exactly the fresh 3576-eligible-row corpus fit.

Nominal physical body positions match the remote trace throughout, despite
the inference mismatch. Full-noise body coordinates first differ by more than
1 pixel at tick257; local final `(219.4806113,26.5231557)` has neither hold,
versus remote `(334.4829333,102.6639127)` with both holds. This is portability
failure, not a diagnosed cause or proof that any particular rounding error
caused the loss. Local CPU inference uses Torch2.6.0+cu124, remote2.6.0+cpu;
the build difference alone is not an explanation.

Actual work:7200controlled+960reset ticks,4rollouts,0updates. Early/late
interventions were blocked, with no tolerance relaxation or physical rerun.
Space independently PAUSED at1791120948.6116133; all reservations stay closed
at cumulative estimated$0.4074241866528988. Goal metric remains0.
Evidence: `artifacts/imitation_noise_probe_20261004T133305314172Z/verification.json`.
Two preparation errors (Hub1.32 HTTP API, Windows venv launcher ancestry)
were fixed before game work; their failed attempts are preserved. The owned
launcher exception leaves Linux training admission unchanged. Final tool also
captures terminal post-step telemetry and flushes partial rows for interrupted
diagnostics; these additions are fixture-tested, not another physical rollout.
All229Python tests and JS checks pass. Next: fixed-input inference/recorded-
action portability diagnosis before retrying this exact frozen intervention.
No blind BC/PPO scaling, closed-session restart or viewer work.

## Closed imitation comparison: historical source/configuration and results

- Closed session **`imitation-20261004-v1`**, configured mode **`imitation_study`**.
- Private source **`95a8e311664789bcf1be5c609dce148e1f300f93`**,
  exact locally tested bundle `artifacts/hf_bundle_20261004T090634364226Z/`.
- Pinned study operator context **`ae958180b348432f236c6c1e72f832a723164199`**;
  passed-preflight context **`9b3f4f0d6f1128e301e9603edecabecf12de8567`**;
  corpus revision **`c09410fbf4fd7b36bfb6976f3659b7ec28b2e38c`**.
- Actual **PAUSED**, allocated hardware absent; requested CPU Upgrade,
  one never-sleep replica remains configured. Published $0.03/hour was
  reverified from official HF docs on 2026-10-04. Historical cap **$0.48**;
  imitation closes at conservative **$0.114728001**, cumulative all closed
  **$0.407424187**, unchanged $10 ceiling. These are estimates, not bills
  or remaining HF credits. **No active paid reservation or new batch.**
- Historical reservation start **`1791104923.3790162`**; immutable deadline
  **`1791162523.3790162`**, **2026-10-05 01:08:43 UTC**. This is a distinct
  new budget, not renewal/extension/resume of the closed timing or v2 sessions.
- Complete pinned dataset **`c40574bb709f64fba893d3b44bc6f302306a51ad`**:
  all nine full contracts, exact initial/post-clone traces within every seed,
  dependency/source/data/work bindings and24saved-companion identities
  validate. Worker complete **2026-10-04 12:57:06 UTC**; independent
  PAUSED epoch **`1791118690.7391362`**, about12:58:10UTC, rechecked PAUSED.
- Final central held counts, seeds6/7/8: **scratch0/0/2, BC-only0/1/2,
  BC+PPO0/0/0**. Secondary **scratch0/0/6, BC0/1/4, hybrid0/0/0**.
  Medians **scratch-0.1973/10.9245/81.8234, BC9/7.5115/11.5050,
  hybrid24/6/5**. All worst-seed held/full-climb rates **0**; all nominal
  central-held gates false. **0/81 final full completions, zero final deaths**.
  No first-skill candidate, robust imitation advantage, promotion or scaling.
- Last hybrid seed8:393216control+5040reset ticks,42resets,3840PPOcalls,
  1437.29855learning seconds plus2000BCcalls/512000presentations.
  Nominal `(133.2963364,21.5586272)`,retained0.55863;median5,zero holds.
  Its post-clone trace matches BC-only exactly but its two central/four
  secondary cloned held cases are absent after PPO. This is paired outcome
  loss, not a general causal forgetting diagnosis.
- Whole comparison: **2359296 training control +26880 reset ticks**,
  23040PPOcalls,12000BCcalls/3072000BCpresentations. Actual distinct
  reference189case rollouts,340200control+45360reset ticks, excluding
  duplicate BC final/post-clone JSON. PPO work per scratch/hybrid cohort
  is1179648control ticks/11520calls; resets13200/13680 and
  learning4318.47146/4515.74139seconds. BC-only/hybrid supervised wall
  20.19971/20.33349seconds. Not equal total compute, sample presentations or FLOPs.
- Final model/RMS/clone24companions have bounded immutable metadata. Only
  selected clone7 has subsequently been reloaded; its noisy held baseline is
  not portable. Standard structured cases are not IID; the
  goal helper still requires independent held-out, upper-route fidelity and
  replayable saved-policy completion. Seventeen checker/goal tests pass.
  Closure evidence:
  `artifacts/imitation_finish_review_20261004T125810739136Z/complete_review.json`.
- **Next bounded step:** the declared recorded-action replay above, not another
  blind saved-feedback rollout. Noise-prefix/suffix causal interventions remain
  blocked by the failed saved-baseline gate. Closure satisfies only the
  terminal/PAUSED/ledger requirement; never substitute recorded controls for
  the original saved-controller baseline requirement.
- **Do not restart this closed session, silently renew its deadline, or scale
  failed arms.** The autonomous operator remains active (Loop22bd00f8 listed
  running after closure), because original summit/robust multiple-seed
  held-out completion is still unverified. Historical sections below are
  intermediate evidence, not instructions to resume the closed batch.
- All **nine remote preflight checks** pass at immutable dataset
  **`67712baf8f4f0464a4b03e133ed97439b32462ef`**. Worker completed at
  **09:17:38 UTC**; independently verified **PAUSED** at
  `1791105736.9293103`. 219 Python tests and JS collision checks pass.
- Review binds the exact source/game/corpus/normalization/budget. All 17 raw
  cases and six 384-tick reactive cases have zero measured fast/reference
  error. Three-arm smoke settings, work and reference stage traces validate;
  saved RMS equals a fresh eligible-corpus fit exactly, and same-seed
  untrained traces and post-clone traces/weights agree. These short smokes
  establish pipeline integrity, **not learned skill or portability**.
- Effective allocation is 8 CPUs/32 GB. Summed worker/reference peak RSS is
  about 6.09 GiB (can double-count shared pages); terrain benchmark is
  about 258 decisions/s, excluding optimization. Static terrain approximation
  disagrees at one of 135 sampled points; this is not fast/reference drift.
- Published the exact durable passed ticket while independently PAUSED.
  Changed **only mode/context**, then intentionally restarted the study at
  **`1791105924.3108993`**, returning BUILDING. Source, corpus, session,
  start/deadline, CPU Upgrade/never-sleep/one replica and $0.48 reservation
  are unchanged. No old session was resumed and no budget was renewed.
- Evidence: `artifacts/imitation_preflight_review_20261004T092140390244Z/`
  (`review.json`, `imitation_study_context.json`, `study_start.json`).
- One bounded startup monitor pins dataset
  **`8b3acc244d88f174e7fddb5ec84eebb94ae896fa`**. Independent verification
  at `1791106097.4731588` finds **RUNNING**, **`imitation_dispatch`**, no
  error, and validates the exclusive durable **`claimed_no_resume`**
  execution claim, prepared nine-run contract and corpus/source/deadline.
  No learner manifest, controlled-work sample or completed result was present
  in this initial pinned snapshot. Full study dispatch is verified; optimizer
  work and skill are not inferred from startup.
- Initial operator verification incorrectly required the paused replica dict
  to remain identical while RUNNING. HF legitimately added `current:1`;
  the existing unattended-runtime guard validates requested/current=1.
  Corrected review uses the **same immutable startup revision**, no new
  monitor/poll or deployment change. This was not a worker failure.
- Eight goal tests and six imitation-execution guard tests pass locally.
- First bounded training audit pins dataset
  **`baa7233e4b149fdddd3ec982bb7fa659f4edd8d9`** at
  `1791106840.1407928`. Actual Space/source/session/mode/context/deadline
  and one never-sleep CPU Upgrade replica are unchanged; phase
  **`ppo_from_scratch_seed_6`**, no reported error.
- The exact full-budget scratch manifest, parent grant/claim hash,
  prepared contract, corpus/RMS declaration, raw reward and physical counters
  validate. **116400/393216 controlled ticks**, **1320 reset-settling
  ticks** (11 resets), **117720 total counted ticks**. All 291 complete
  400-tick sampled rows pass accounting and reward/outcome checks.
- Two model/normalizer checkpoint pairs at **40000/80000** transitions have
  bounded nonzero metadata at that same revision. No checkpoint binary reload,
  portability or exact completed optimizer-call count is inferred.
- Training detector flags are latched central-held in 56 sampled rows and
  secondary-held in 83. These are **not independent successes, final policy
  evaluation or episode counts**. The last sampled pose is
  `(788.55567,-9.12384)`, retained gain **-30.12384**, both holds false.
  Zero summit/death flags occur in sampled rows; sparse sampling cannot count
  all terminal events or prove a continuous trajectory.
- 132 sampled raw Gaussian policy draws exceed the unit box. Bound SB3/env
  source clips them to legal controls; the trace's `action` is the raw draw,
  not an illegal applied pointer input. Never replay these sparse samples as
  if they were every-tick applied actions.
- Imitation checker reports **zero completed runs**, all nine incomplete;
  `tools.research_goal_metrics` reports no candidate/final goal. Seventeen
  imitation-checker/goal tests pass locally. Evidence:
  `artifacts/imitation_progress_review_20261004T093741216495Z/audit.json`.
  All HF operations in this chunk were reads; no running-batch changes.
- First pinned final result **`abe4b0aa973c702b1637648be1f1afbb703d0db8`**
  validates one full run, **`ppo_from_scratch_seed_6`**, with eight still
  incomplete. Actual Space remains RUNNING, phase
  **`behavior_cloning_only_seed_6`** at that snapshot; source, context,
  corpus, deadline, hardware and reservation are unchanged, no reported error.
- Final 60-second original-reference outcomes: **0/9 central holds,
  0/9 secondary holds, 0/9 full completions, 0 deaths**. Median retained
  gain **-0.197324** (untrained median 0). Nominal final pose
  **`(-2.4797933,20.7844254)`**, retained gain **-0.215575**.
  Last four nominal seconds have 120 body-query-hit ticks and zero hammer
  hits, near spawn, not ledge support or a force measurement. Applied actions
  still vary; this is not a constant-action diagnosis.
- Complete work is **393216 controlled ticks +4080 reset ticks**, **34
  resets**, **397296 counted ticks**, **3840 actual policy optimizer calls**,
  **1412.54336 learning seconds**, zero BC work/terminal-short decisions.
  Baseline/final reference stages each have 16200 control +2160 reset ticks.
- The strict imitation checker validates exact source/assets/data/RMS,
  admission/dependencies/settings/work and all before/final legal traces;
  remote partial summary agrees on complete outcomes. Its missing-file list
  predates the next arm's manifest, so compare missing-run identities, not
  stale missing-file lists. Final model/RMS companions have immutable bounded
  metadata only, not reloaded or proven portable.
- This scratch seed fails the frozen first-skill gate despite earlier
  on-policy held flags. Do not infer a cloning effect, skip the remaining
  controls, enlarge compute, or change the running experiment. Complete all
  predeclared arms/seeds before comparison and selection.
- Existing physical goal helper receives an explicit field projection of the
  validated imitation row, not fabricated pilot artifacts. No complete
  three-seed cohort, candidate or final goal. Seventeen checker/goal tests
  pass; this entire chunk used HF reads only. Evidence:
  `artifacts/imitation_snapshot_review_20261004T095748247801Z/review.json`.
- Clone-only review **`d3ed8abd536e99a85a0820f1eb5f749089d7ac12`** validates
  **two completed runs**, scratch and **`behavior_cloning_only_seed_6`**;
  seven final runs remain incomplete. RUNNING, no error, unchanged
  **`behavior_cloning_then_ppo_seed_6`** is active.
- Clone-only final reference: **0/9 central holds, 0/9 secondary holds,
  0/9 full completions, zero deaths**. Median retained gain **9** versus
  its untrained 0 and scratch final -0.1973. Nominal ends at
  **`(227.9007801,30)`**, retained **9**, with 120 body-query hits and
  zero hammer hits in the last four seconds. This is small traversal/lift,
  not the demonstrated ledge or robust skill.
- Actual actor-only cloning is **2000 optimizer calls**, batch256,
  **512000 sample presentations**, **3576 eligible rows**, about
  **6.68616 seconds**. In-corpus normalized-action MSE falls from
  **0.2562333941 to 0.0001084495**, but physical held outcomes remain false.
  Clone-only has **zero RL/PPO calls, control/reset training ticks or resets**.
  Low supervised error is not closed-loop expert reproduction or recovery.
- Same-seed scratch/BC untrained reference traces match exactly. BC final
  equals post-clone, by source and trace, **not a third independent evaluation**.
  Actual distinct BC reference exposure is 32400 controlled +4320 reset ticks
  (baseline and post-clone); do not double-count the duplicated final JSON.
- BC saved final/post-clone model LFS identities match. Its initial normalizer
  LFS identity matches hybrid's. Whole BC/hybrid post-clone ZIP hashes differ,
  which does **not** establish differing weights/inference; no binaries were
  loaded. Hybrid post-clone reference equality remains a required later check.
- Hybrid's bound full-run manifest/grant/claim validates; its sparse training
  prefix is **137200 controlled +1680 reset ticks**, latest retained
  **32.64142**, neither held flag. This is on-policy progress only, not a
  final result or a completed optimizer-call count.
- Goal helper explicitly projects both validated rows: no complete
  three-seed cohort, candidate or final goal. Seventeen checker/goal tests
  pass. Clone evaluation123902707bytes is below the prechecked128MiB gate;
  this chunk used HF reads only. Evidence:
  `artifacts/imitation_clone_review_20261004T101754929686Z/review.json`.
- Seed6 full review **`11678b29c6b960586a1455c82a1e1218b9d21ba4`** validates all
  three **seed6** arms, **three completed runs/six incomplete**. Actual
  RUNNING phase is **`ppo_from_scratch_seed_7`**, no error; source, data,
  context, start/deadline, CPU Upgrade/one never-sleep replica and cap unchanged.
- Hybrid final original-reference result: **0/9 central/secondary holds,
  0/9 full completions, zero deaths**, median retained **24** (scratch
  -0.1973, BC-only9). Nominal final **`(585.4595583,40)`**, retained **19**,
  last four seconds120body-query hits/zero hammer hits. All three arms
  therefore have **0/27 final held outcomes/completions**, no final deaths.
  Increased retained height is not the demonstrated first-ledge skill.
- Hybrid actual work: **393216 control +4320 reset ticks**, **36 resets**,
  **3840 policy optimizer calls**, **1444.40392 learning seconds**, plus
  **2000 BC calls/512000 presentations**, BC about **6.70779 seconds**.
  Early near-platform training flags remain distinct from final reference.
- **Matched-seed comparability now passes:** all three untrained legal
  reference trace hashes agree; BC-only and hybrid post-clone traces match
  exactly across all nine60-second cases, including applied actions/outcomes.
  The earlier differing whole-ZIP hashes are not a behavior mismatch.
  No tensor equality or cross-host saved-policy portability is inferred.
- Seed6 totals: **786432 training control +8400 reset ticks**, **7680 PPO
  calls**, **4000 BC calls/1024000 BC presentations**. Actual distinct
  reference work is **63 case rollouts**, **113400 control +15120 reset
  ticks**, excluding BC-only's duplicate post-clone/final JSON.
- Strict full-stage/source/dependency/work checker and projected physical
  goal helper pass; no three-seed cohort, candidate or final goal. Eight
  saved-model/RMS/clone companion identities are bounded immutable metadata
  only. Seventeen checker/goal tests pass. Evidence:
  `artifacts/imitation_seed6_review_20261004T103801371190Z/review.json`.
  This chunk used HF reads only; no local training or batch changes.
- All seed6 arms fail the first-skill gate. Finish frozen seeds7/8 before
  comparison/closure, then select a bounded first-divergence/reactive
  corrective-control diagnostic rather than blind scaling or a relaxed gate.
- Earlier prefix snapshot **`8393e54e26fda29106f20add394f17ba76609ce7`**
  has **no new final result**: three validated seed6 runs unchanged.
  Actual RUNNING phase **`ppo_from_scratch_seed_7`**, no reported error;
  source/mode/context/data/deadline/hardware/replicas/reservation unchanged.
  Seed7 prefix validates **302000 control +3720 reset ticks**, **755
  complete 400-tick sample rows**, seven bounded checkpoint pairs through
  280000. Latest training retained **24**, neither hold flag. No final
  outcome, exact optimizer-call count or binary portability is inferred.
- Used this invocation for an **offline 600-tick comparison**, not more
  polling or new physical work: the frozen failed clone nominal reference
  from `d3ed8abd...` versus the legal nominal training expert/corpus.
  Corpus/expert/clone file hashes and current game/source bindings validate.
  Expert pre-action float32 body observations are shifted to post-action
  indices, with exact manifest endpoint; maximum decoded-position rounding
  bound about **0.0000218 pixel**, much smaller than measured departures.
- First relative target component differs by **2.00631 pixels**:
  expert `(0.49577025,-0.19169308)`, clone
  `(0.48009592,-0.20012996)`. Time-aligned body distance first exceeds
  **1 pixel at tick27**, **10 pixels at tick49**. At tick600 expert is
  **`(322.5858865,104)`**, clone **`(237.3790079,32)`**, distance
  **111.55363 pixels**. This locates early departure, not its proven cause.
- **Limits:** training expert reset6001 differs from reference reset1001;
  exact full initial reference observations are absent. Once paths differ,
  equal-time action discrepancy is **not supervised error at equal states**,
  and the expert recording is not an off-state corrective oracle. No
  intervention, rollout, model reload, learning update or competence gain.
  Same final-reference LFS identities are unchanged; goal helper remains
  candidate/final false. Evidence:
  `artifacts/imitation_seed7_review_20261004T105752209730Z/offline_diagnostic.json`.
- Next bounded priority is actual seed7/8 final contracts. After comparison
  closure, a controlled **same-reset legal expert-prefix/clone-continuation**
  diagnostic can test whether early alignment/recovery matters, before
  designing new corrective data or spending on more optimizer steps.
- Seed7 partial review **`44d2c66f7287e8cc31cdfcfa92af8103eb662db9`** validates **five
  full runs/four incomplete**, including seed7 scratch and clone-only.
  Actual RUNNING phase **`behavior_cloning_then_ppo_seed_7`**, no error;
  all source/data/context/runtime/deadline/cap settings are unchanged.
- Seed7 scratch final: **0/9 central/secondary holds, 0/9 full completions,
  zero deaths**, median retained **10.924516**; nominal
  **`(223.5328626,28.8316762)`**, retained **7.831676**. Work393216control
  +4560reset ticks,38resets,3840policy calls,1499.03449learning seconds.
- Seed7 clone-only: **1/9 central/secondary holds, 0/9 full completions,
  zero deaths**, median retained **7.511521**, nominal **false** at
  **`(62.2241726,21.5291058)`**, retained **0.529106**. Cloning2000calls/
  512000presentations, MSE0.25613758->0.0001062434,6.70341seconds;
  zero RL control/reset/PPO work. Lower median than scratch is not a method
  conclusion; the one hold remains far below the declared8/9+nominal gate.
- Held case is **`action_noise_5`**, fixed noise8105/std0.02, final
  **`(334.4829333,102.6639127)`**, retained **81.663913**.
  First hold at **52.833333seconds/tick1585**. Independently recomputed
  both frozen detectors from every-tick body positions, displacement
  velocities (as in bound runtime), outcomes and body-query hits.
  The90-tick window is X334.15169..334.48293,Y102.52794..103;
  **90/90 body-query hits**, max speed **0.828092px/tick**. This validates
  the held event, not support forces, portability, robust learning or summit.
- Seed7 matched untrained reference traces agree; hybrid post-clone equality
  awaits its final trace package. BC final/post-clone alias is not another
  independent evaluation. All five completed final inventories total
  **one central/secondary held case, 0/45 full completions, zero deaths**.
  No complete three-seed cohort or goal-helper candidate/final success.
- Seventeen checker/goal tests pass. Saved companion metadata is immutable
  and bounded but not reloaded. Evidence:
  `artifacts/imitation_seed7_results_20261004T111807286622Z/review.json`
  and `held_window.json`. All remote actions were reads; no new local
  training/rollouts or running-batch changes.
- Earlier hybrid prefix **`490e7e803d6ecad7ada8c6b5c8fb320a6015b861`** has no new
  final result: five validated runs unchanged, four incomplete. Actual
  RUNNING phase **`behavior_cloning_then_ppo_seed_7`**, no reported error;
  source/context/data/runtime/deadline/cap unchanged. Hybrid prefix
  **258000 control +3000 reset ticks**,645complete sampled rows,six
  checkpoint pairs through240000. Last training retained189.47804,
  neither held flag; this is not final performance or robust climbing.
- Used the remaining chunk for **offline paired1800-tick clone traces**,
  nominal versus fixed noisycase8105: same reset1001, no warm-ups,
  exact same first raw policy prediction. All applied actions independently
  recompute from the unchanged four-tick noise clock.
- First noise changes the relative pointer by
  **`(-3.833073,-0.957458)` pixels**. Body post-action separation is
  **0.0617523pixel** on tick1; policy predictions first differ on **tick2**,
  hammer queries on **tick26**, body queries on **tick27**, body distance
  exceeds1pixel on **tick28**. Later outputs are feedback at different
  states, not proof of different weights.
- The nominal finishes at `(62.22417,21.52911)`, retained0.52911, no hold;
  the noisy run at `(334.48293,102.66391)`, retained81.66391, both holds.
  This is a post-hoc paired description of already counted outcomes,
  **not new evidence of a success rate or any particular helpful noise block**.
  Noise continues through all1800ticks; equal first outputs do not prove all
  initial features equal. A future prefix/suffix intervention must test
  necessity/sufficiency before using this as a corrective recipe.
- Same five final-reference LFS identities and projected goal-helper
  candidate/final false are confirmed. Hash/source/case-clock/prefix
  assertions pass; **zero new rollouts/updates**, no binary reload or HF
  writes. Evidence:
  `artifacts/imitation_pair_review_20261004T113802850890Z/pair_diagnostic.json`.
- Two-seed review **`7edf76f63f4a67a236145b9cf5e0e8b183688972`** validates
  **six completed runs/three incomplete**, all arms for seeds6/7.
  Actual RUNNING phase **`ppo_from_scratch_seed_8`**, no error; exact
  source/data/context/runtime/deadline/cap remain unchanged.
- Seed7 hybrid final: **0/9 central/secondary holds, 0/9 full completions,
  zero deaths**, median retained **6** (scratch10.9245, BC7.5115).
  Nominal **`(134.8168496,23)`**, retained **2**. Complete work:
  393216control +4320reset ticks,36resets,3840policy calls,
  1634.03892learning seconds, plus2000BCcalls/512000presentations.
- **Matched-stage comparability passes for both complete seeds:** all
  initial reference traces agree within seed; BC-only and hybrid post-clone
  reference traces match exactly. Seed7's noisycase8105 hold is present
  before PPO, then absent afterward: retained81.66391 ->3.52790, final
  **`(211.4653104,24.5278985)`**. This is observed paired skill loss,
  **not a diagnosed cause or a universal claim that PPO harms cloning**.
  Seed6 hybrid median rose9->24 whereas seed7 fell7.5115->6; no robust
  benefit or stable timing/control conclusion follows.
- Six completed final inventories: **one central/secondary held case,
  0/54 full completions, zero deaths**, all nominal held gates false.
  No declared three-seed cohort, first-skill candidate or final goal.
- Complete seeds6/7 totals: **1572864 training control +17280 reset
  ticks**,15360PPOcalls,8000BCcalls/2048000BCpresentations. Distinct
  reference work126case rollouts,226800control +30240reset ticks,
  excluding duplicate BC final/post-clone JSON.
- Full source/data/dependencies/physical-time/stage/work checker and
  projected goal helper pass; sixteen binary companion identities validate
  immutable bounded metadata only, no reload/portability claim.
  Seventeen checker/goal tests pass. Evidence:
  `artifacts/imitation_two_seed_review_20261004T115807788438Z/review.json`.
  All HF operations were reads, no new local training or running-batch changes.
- Complete frozen seed8 and verify automatic PAUSED before closure.
  Investigate first-divergence/recovery and preservation of primitive skills
  in a separately bounded follow-up, not blind scaling or new active settings.
- Earlier final-scratch prefix **`5df6c20390ca641d8d10a2c62471e7f4142b922e`** adds no final
  result: six validated runs unchanged. Actual RUNNING phase
  **`ppo_from_scratch_seed_8`**, no error; all source/data/runtime/context/
  deadline/cap bindings remain valid. Prefix393200control +4560reset ticks,
  983complete sampled rows,nine checkpoint pairs through360000.
  Last on-policy retained26,both holds false; **393200 is not the complete
  393216 training summary or a final reference policy outcome**.
- Predeclared a **non-executing four-condition causal diagnostic**, pinned
  to clone-only seed7 saved model/RMS identities: nominal, full noisy8105,
  noise only ticks0..59, noise only ticks60..1799. Cutoff60 (two seconds)
  follows the observed early divergence, so selection is **post-hoc/
  exploratory, not held-out verification**. Same global four-tick Gaussian
  stream must advance even during masked intervals; no stream restart at60.
- All cases use ordinary reset1001, no warm-up/placement, frozen217-feature
  RMS/raw reward and deterministic one-tick legal controls. Reference+fast:
  maximum8case rollouts, **14400control +1920reset ticks**, **600-second
  wall cap**, zero training updates/new paid reservation, owned headless
  processes only. No probe has launched, no binaries downloaded or loaded.
- **Admission waits for current comparison terminal review plus independent
  PAUSED and ledger closure.** First reproduce nominal/full-noise saved
  reference traces and exact local fast/reference actions, normalized
  observations, reward and telemetry; if baseline portability/fidelity fails,
  stop without interpreting early/late intervention effects. No current
  source/context/queue/hardware/deadline change or silent resume.
- Prefix/source/hash/admission assertions and pure array noise-mask fixtures
  pass. Same six final-reference LFS identities keep the projected goal helper
  candidate/final false. Evidence:
  `artifacts/imitation_last_seed_review_20261004T121802090256Z/`
  (`causal_probe_plan.json`, `declaration_verification.json`).
  This is bounded diagnostic preparation, **not a new ML result or
  hypothesis confirmation**, with zero new physical work or updates.
- Eight-run historical review **`8ab8568c299c2563302ee5ddb51c6339e7a280ef`** validates
  **eight completed runs**, only **`behavior_cloning_then_ppo_seed_8`**
  remains. Actual RUNNING phase is that last hybrid, no error;
  source/context/data/runtime/deadline/cap unchanged. No PAUSED/closure yet.
- Seed8 scratch reference: **2/9 central,6/9 secondary held events**,
  0/9full completions,zero deaths, median retained **81.823447**.
  Nominal **`(344.6361888,102.9068100)`**, retained81.90681, secondary
  held but central false (X beyond335). Actual393216control+4560reset
  ticks,38resets,3840policy calls,1406.89361learning seconds.
- Seed8 clone-only: **2/9 central,4/9 secondary held events**,0/9summits,
  zero deaths, median retained **11.505030**. Nominal false at
  **`(268.5098762,31.5060203)`**, retained10.50602. Central held cases
  are hammer-left `(317.84285,104)` and hammer-right `(311.33074,104)`,
  each retained83. BC2000calls/512000presentations,zeroRL;
  MSE0.25403884->0.00008516183,BC6.81014seconds.
- Recomputed both frozen detectors from every-tick coordinates/displacement
  velocities/body-query hits for all18new final traces. Four central and
  ten secondary **metric windows** validate, not14independent cases.
  **BC noise3/4 secondary holds are transient:** later endpoints are
  `(532.64385,28.65331)` and `(268.58891,31.70660)`. A latched held event
  is not continued final support. No support-force or portability claim.
- Full scratch and BC cohorts now validate all seeds6/7/8:
  central counts **scratch0/0/2, BC0/1/2**, secondary
  **scratch0/0/6, BC0/1/4**. Both worst-seed held/full-completion rates
  remain **0**, neither passes nominal+8/9first-skill gates. Do not select
  or scale from seed8's favorable median or modify either frozen detector.
- Eight completed final inventories: **five central/eleven secondary held
  events,0/72full completions,zero deaths**. This is inventory, not a pooled
  IID method-success rate. Matching seed8 untrained traces pass; paired
  hybrid post-clone traces await the last result.
- Strict full-stage/source/work checker and projected goal helper pass,
  candidate/final false. Twenty-one saved companion identities are
  immutable bounded metadata only; seventeen checker/goal tests pass.
  Evidence: `artifacts/imitation_seed8_results_20261004T123812526317Z/review.json`
  and `held_windows.json`. All HF operations were reads, no new local
  training/rollouts, active changes or budget renewal.
- **Closed-comparison instruction:** no robust cloning advantage, first-skill
  candidate or full completion is established. Do not restart or extend this
  session. Proceed only with the separately declared bounded causal probe,
  enforcing saved-baseline portability first; no new paid training/scaling.

### Closed timing study, immutable history

- Configured closed session: **`timing-20261004-v1`**, mode **`timing_study`**.
- Private Space revision: **`362327f3281811b924089251aa67438fe64dc31e`**.
- Pinned secret-free operator context dataset commit:
  **`80884fcb942397b783c9562b2cf3b987879a21a8`**.
  Historical preflight context: `1df89ec0fe48a579c234fed9e4a2e26085279811`.
- Requested CPU Upgrade, one replica, paid-default never-sleep (`sleep_time=None`).
  Actual stage is **PAUSED**; current allocated hardware is absent while paused.
- Reservation start: `1791088706.4052017`; immutable deadline:
  **2026-10-04 20:38:26 UTC**, epoch **`1791146306.4052017`**.
- Historical maximum reservation **$0.48** at published $0.03/hour.
  Timing is now closed at **$0.100149** through verified pause; all closed
  batches total **$0.292696**, below the unchanged $10 ceiling. These are
  conservative estimates, not provider bills or remaining-credit balances.
- All six timing results are complete/contract-valid at dataset commit
  **`05c589ad26da16a3cfe6885c2948990f45a6e9c5`**.
  Worker completion is **2026-10-04 07:19:31 UTC**; independent pause
  verification is epoch **`1791100724.3051379`**, about **07:58:44 UTC**.
  No source/session/context/deadline change or operator pause/restart occurred.
- No timing arm qualifies for robust promotion or scaling. The separate
  imitation admission/trainer/worker integration now passes locally and its
  distinct preflight is described above. **Do not restart this closed
  timing session or deploy smoke-only imitation as full training.**

The following kickoff/progress sections are historical evidence, not current
runtime instructions. Complete timing closure is recorded below.
- Explicit restart requested at `1791088979.409153` after source/context/
  variables were verified while PAUSED; it returned BUILDING. The next bounded
  monitor read returned APP_STARTING with durable phase `timing_admitted`.
- Pinned first-state review at dataset commit
  `bcdd369f039cb3cdfaf0fa654e378d209e423f9c` verifies exact source/game/asset
  hashes, start/deadline, configured context and runtime policy, with no error.
  Evidence: `artifacts/timing_deployment_20261004T044058033509Z/`.

**Timing preflight passed all eight checks and automatically paused.**
Pinned review at dataset commit `471eadaf676a498b52cabb5962312e3da94e378b`
validates exact source/game/assets, 17 raw-physics and six reactive timing
fidelity cases with zero measured errors, both matched smoke contracts,
effective 8 CPUs/32 GB cgroup allocation and never-sleep/one replica.
Terrain benchmark is about 266 decisions/s excluding optimization; summed
worker+reference peak RSS is about 6.08 GiB, not exclusive physical memory.
Independent PAUSED verification epoch: `1791089935.6895523`.
Evidence: `artifacts/timing_preflight_review_20261004T045845231549Z/`.

After reviewing that evidence while PAUSED, the operator published the exact
durable passed-preflight fields in the new pinned context, validated admission,
and changed **only `RL_CONTEXT_REVISION` and `RL_MODE`**. An intentional
`timing_study` restart at `1791090090.08562` returned BUILDING. Source, hardware,
session/start/deadline and $0.48 reservation are unchanged. No checkpoint resume,
extra replica, widened pilot gate or CPU XL scaling occurred.
The subsequent bounded monitor read returned **RUNNING**, durable phase
`timing_dispatch`, with no error. At dataset commit
`7a9a6cdb066dd30bc93da01a7228b7ce4aea38e6`, the operator verifies the exact
six-run campaign, admitted source/context/deadline and persisted
`claimed_no_resume` execution claim. Evidence:
`artifacts/timing_preflight_review_20261004T045845231549Z/study_kickoff/`.
No completed learner outcome or learning-progress snapshot was available in
that kickoff commit. Its then-false training-start metadata was not a runtime
monitor; the later active-run audit below corrects it from actual telemetry.
Inspect durable status/trace rather than assuming bookkeeping indicates
whether training is active.

The admitted study has six sequential runs: seeds 3,4,5, each repeat 1 then 4.
Each arm has nominal 393,216 controlled ticks and 3,840 planned policy optimizer
calls; decisions/gradient sample presentations/FLOPs are not equal. Both metrics
and all nine physical-time perturbation cases remain frozen. No learned outcome
is available at this kickoff, and no improvement/completion is claimed.
Do not upload, restart, resize, change variables/secrets or queue while it runs.
Next scheduled priority: inspect one pinned durable snapshot of current status,
claim/manifest/progress and any complete results with the timing checker.
Do not blindly resume interrupted work. At terminal failure/completion/deadline
verify durable artifacts and PAUSED; pause only this owned Space if necessary.

### First active run contract/accounting audit

At the 2026-10-04 05:17 UTC check the study remains RUNNING on the unchanged
source/context/deadline, phase `ppo_absolute_repeat_1_seed_3`. A pinned audit
at dataset commit `0520df2b4c6ab9e04f83e9fb71769900c23c61e3` validates its
remote admission, exact campaign/source/assets, default raw settled reward,
one-tick gamma `0.9998074776513175`, physical-time GAE `0.9872585449014338`,
rollout 8,192/minibatch 1,024/10 epochs and declared nine-case reference horizon.
All 437 complete sampled JSONL rows have the expected 400-decision cadence,
controlled ticks equal transitions, and monotonic whole 120-tick reset counts.
The last durable sample is transition **174,800**, controlled ticks **174,800**,
reset-settling ticks **2,040** (17 resets). Four stable checkpoint/normalizer
pairs through 160,000 transitions have immutable Hub metadata/nonzero sizes;
they were not downloaded/reloaded, so this is not policy portability evidence.

The sampled pose is approximately `(150.46,26.74)`, retaining 5.74 units, with
both central/secondary hold flags false in that current episode. Training
telemetry/previous peaks are not competence. No final training summary or
reference evaluation exists yet; the timing aggregator correctly reports all
six runs incomplete, no arm comparison or final-goal verification.
Evidence: `artifacts/timing_active_audit_20261004T051847531397Z/`.
The cost ledger's training-start metadata is now corrected from this actual
trace; reservation/start/deadline/source and financial caps are unchanged.
Next scheduled priority is the first completed result with companions, or a
bounded progress/terminal-status check. Keep the live study unchanged.

### First complete timing result: repeat 1, training seed 3

At the 2026-10-04 05:37 UTC check the first one-tick run is complete and the
unchanged queue is actively training `ppo_absolute_repeat_4_seed_3`.
Pinned dataset `112cb595ce2f2f42895b1e01d0185577c964f7b8` passes the timing
aggregator for repeat-1 seed 3, with manifest/admission/source/reward/evaluation
and training-work contracts intact. It has **0/9 central v1 holds, 1/9 secondary
support holds, zero full completions and zero evaluation deaths**. Median
retained gain is **0**, equal to its untrained baseline median.

The isolated secondary hold is `action_noise_5`: first qualified at 5.83 game
seconds, final approximately `(302.12,104)`, retaining 83 units. Body-query
hits cover 1,753/1,800 controlled ticks, including all final four seconds.
It remains just outside the frozen central X minimum 305. This is a genuine
declared-case support outcome under recorded reference metrics, not
nominal/robust skill, held-out success or portable saved-policy reproduction.
Nominal remains near `(1.01,21)`; most other cases stay near spawn/low terrain.
Neither the pilot gates nor metric definitions are changed.

Training reports **393,216 actual controlled ticks**, **4,440 reset ticks**
(37 resets), zero shortened terminal decisions, **3,840 actual policy calls**
versus the separately labelled 480 internal counter, and 1,453.60 learning
wall seconds. Model/normalizer companions are durable with nonzero immutable
Hub metadata; they were not downloaded/reloaded for this review.
All before/after reference cases consume 1,800 controlled ticks each and have
separately counted initial/automatic reset work.

The one-tick evaluation JSON is 81,189,517 bytes because it records four times
as many decisions as repeat 4. An initial operator-only 32 MiB size gate refused
it; verified immutable metadata permits a bounded 128 MiB retry, which passes
the full trace checker. This was an audit limit, not a learner failure, and
did not change the worker/source/settings. Use bounded per-file size metadata
before future timing-result downloads, rather than assuming pilot file sizes.
Evidence: `artifacts/timing_first_result_verified_20261004T054007933164Z/`.

Only one of six runs is complete. Do not rank timing arms, scale, promote or
infer a three-seed effect from it. Finish the same six-run study under its
unchanged deadline/cost cap; next scheduled priority is the paired four-tick
result or a bounded terminal/progress check.

### First matched timing seed pair validated

At the 2026-10-04 05:57 UTC check both training-seed-3 arms are complete;
`ppo_absolute_repeat_1_seed_4` is now actively training in the unchanged queue.
Dataset commit `b0865f09d77e33efe5cc3d7b660a9cb40b539517` validates both
complete run contracts, common dependencies/admission/source and durable
model/normalizer metadata. Three-seed cohorts remain incomplete, so the
aggregator deliberately returns no worst-seed timing-arm comparison.

Repeat-1 seed 3 retains its **0/9 central, 1/9 secondary holds**, median retained
0. Repeat-4 seed 3 has **0/9 central and 0/9 secondary holds**, median retained
**27.77**, nominal approximately `(271.29,51.95)` with retained 30.95.
Both untrained medians were 0; both trained arms have zero reference full
completions and zero evaluation deaths in the nine 60-second cases.
This is a descriptive single-seed tradeoff, not an established timing effect,
robustness claim, promotion or reason to scale.

Repeat-4 training has 98,304 decisions, **393,167 actual controlled ticks**
versus nominal 393,216, **6,960 reset ticks** (58 resets) and 24 terminal short
decisions. Repeat 1 has 393,216 decisions/controlled ticks, 4,440 reset ticks
and no shortened decisions. Each performs **3,840 policy optimizer calls**;
learning wall time is **1,453.60 /690.37 seconds** for repeats 1/4. Thus actual
controlled exposure differs by 49 ticks, reset exposure also differs, and
equal calls are not equal computation or gradient sample presentations.
Keep these differences explicit rather than labelling the arms equal-cost.

Repeat-4 `hammer_right` finishes at approximately `(281.47,100.50)`, retaining
79.50. Its last four seconds have unchanged decision-boundary coordinates
and 120/120 body-query hits, but it is outside the frozen secondary X minimum
285. This is an **outside-detector contact/pose candidate**, not independently
calibrated platform support. Do not call it "no physical support" solely from
the detector, and do not widen the metric after seeing it. Any future physical
calibration/replay must be separate, labelled post-hoc and leave the study
contracts unchanged.

Evidence: `artifacts/timing_seed3_pair_20261004T055834361889Z/`.
Next scheduled priority: complete seed-4 results or bounded status/progress,
then seed 5; keep source, queue, variables, cap and deadline unchanged.

### Outside-detector recorded-action replay, post-hoc only

At the 2026-10-04 06:17 UTC snapshot, seed-4 repeat-1 transition collection
is durable through 393,200 but no complete reference result is available yet.
The image/source/context/deadline are still unchanged and RUNNING. Rather than
poll or alter it, a bounded local diagnostic replays the recorded seed-3
repeat-4 `hammer_right` case from an ordinary reset, without policy inference,
training, privileged placement or new metric definitions.

All **1,800 controlled ticks** reproduce the remote body positions with
**zero** measured decision-boundary error. The independent local original
reference and fast traces have **zero** measured error in all tested per-tick
numeric/discrete telemetry. Final pose is `(281.47135,100.50353)`, retained
79.50 units. For the final four seconds, X/Y are unchanged on every tick,
body-query hits cover 120/120 ticks and physical speed is zero.
The headed original-renderer capture shows the pot at the raised Scratch
block's left lip with the hammer planted on lower terrain, consistent with
the observed contact/pose. No contact-force telemetry is claimed.

Both frozen central and secondary detectors still return false because this
pose is outside their X regions. Preserve that result exactly. The replay
establishes a real stationary contact sequence missed by these region bounds,
not cross-host closed-loop policy portability, general/held-out climbing skill,
full completion, or permission to retroactively widen a success metric.
Any future descriptor extension must be separately calibrated/predeclared;
do not infer "four-tick control cannot support the platform" from this miss.
Evidence: `artifacts/outside_detector_replay_20261004T061945777984Z/`,
including the original-renderer final capture and full legal action/trace JSON.
This is a post-hoc diagnostic of an already selected case, not a new learner
experiment. The active remote six-run batch and financial reservation remain
untouched. Next scheduled priority: seed-4 complete reference results, then
seed 5, or a genuine terminal/deadline check.

### Second matched timing seed pair validated

At the 2026-10-04 06:38 UTC check, the actual Space is RUNNING in
`timing_study`, phase `ppo_absolute_repeat_1_seed_5`, with unchanged
source/context/session/deadline, one never-sleep CPU Upgrade replica and no
durable error. Dataset commit `d939596698dc137221c4a9fa8faba5f510a06b22`
passes all four completed timing run contracts, including both seed-4 arms.
All game/assets/research-source hashes match the declared campaign. Final
model/normalizer companions have nonzero immutable Hub metadata; they were
not downloaded/reloaded, so this is not saved-policy portability evidence.

For seed 4, both repeats have **0/9 central and 0/9 secondary holds**, no full
completions and no deaths in the nine final 60-second reference cases.
Repeat 1 has median retained gain **23.57**, nominal `(646.96,52.59)` retaining
31.59; repeat 4 has median retained **-30**, nominal `(821.47,-9)` retaining
-30. Both untrained baseline medians were 0. The one-tick endpoint gain is
better for this seed, whereas seed 3's endpoint median favors repeat 4.
These two pairs do not establish a replicated timing effect, robust platform
retention, promotion or scaling eligibility.

Repeat-1 seed 4 records **393,216 controlled ticks**, **4,320 reset ticks**
(36 resets), no terminal-short decisions and **1,399.51 learning seconds**.
Repeat 4 records **393,196 controlled ticks**, **5,640 reset ticks** (47 resets),
12 terminal-short decisions and **676.22 learning seconds**. Both record
**3,840 actual policy optimizer calls**, separate from the internal counter
480. Actual controlled exposure differs by 20 ticks; reset work and decision/
gradient sample presentations also differ. Equal planned ticks/calls must not
be described as equal actual exposure, computation or information.

Repeat-1 `hammer_left` ends at `(282.42,101.50)` retaining 80.50, with all final
120 body-query-hit ticks, outside secondary X minimum 285. Repeat-4
`action_noise_4` ends at `(1015.57,176.71)` retaining 155.71, also with 120/120
final body-query hits. These are post-hoc contact/pose observations, not
independently calibrated landings or support-force measurements; neither
satisfies the frozen first-platform descriptors or constitutes full climbing.
Preserve them without widening active metrics or treating high endpoints as
policy success.

Across the four validated runs, **0/36 final reference cases complete the
game**, and none dies within its declared horizon. Both three-seed cohorts
remain incomplete, with no worst-seed arm comparison returned by the checker.
Evidence: `artifacts/timing_seed4_pair_20261004T063847993651Z/`, including
pinned companions, complete JSONs, summary and actual runtime/variable review.
Only evidence metadata in the local ledger changes; the reservation, source,
queue, context and immutable deadline stay untouched. Next scheduled priority:
the complete seed-5 arms or a bounded terminal/deadline verification, then
full-cohort analysis and verified automatic PAUSED before any new experiment.

### Legal expert demonstration prerequisite, no learning

At the 2026-10-04 06:57 UTC monitor snapshot, the actual timing session/source/
mode/context/deadline and one never-sleep CPU Upgrade replica remain unchanged
and RUNNING. Dataset `02c1e44b5b7088ed8e6d477e7919fc692a9f2e4a` still has
four completed evaluations. Seed-5 repeat-1 training telemetry reaches 360,400
controlled ticks with 4,080 reset ticks and both ledge flags latched in that
episode near `(322.82,103.78)`. This stochastic training episode is not a
complete frozen-policy reference result or a reason to promote the study.

Instead of polling or altering the batch, a bounded local prerequisite checks
the known legal first-ledge expert for possible future imitation. Eleven
ordinary-start reference/fast cases use 600 ticks each: original float64
targets, float32-normalized targets, and the nine already declared physical-
time warm-up/noise streams with float32 targets. Warm-up replaces the first
12 ticks, prediction remains indexed by controlled tick, and noise is held
for four ticks. No placement, policy inference, optimizer or learning occurs.
The diagnostic plan is saved before the replays; total controlled work is
13,200 ticks across both backends, plus separate reset settling.

Raw and float32 nominal trajectories both finish at `(322.58589,104)`,
retaining 83 units and passing both frozen ledge descriptors. Maximum action
quantization is approximately **0.00000381 pointer pixel**. Of the nine
20-second perturbed expert cases, **8/9 pass both central and secondary
detectors**, retaining 83 at their endpoints. Noise stream 4 fails both,
ends near `(246.91,83.83)` retaining **62.83**, never qualifies a central hold,
and has zero body-query hits over its final four seconds. All eleven tested
reference/fast traces have **zero measured per-tick error** and no full
completions or deaths.

An additional verifier incorrectly expected raw/float32 inputs to produce an
identical entire trajectory. It fails at tick index 40 with a 0.0002 body-Y
difference. Direct comparison finds maximum body-Y difference 0.00027,
body-X difference 0, rounded pointer-Y difference 0.001 and no tested
discrete-state mismatch. Correct interpretation: the same final landing/hold
survives this conversion, not bitwise intermediate-state identity. This
operator assertion failure is preserved in `validation.json`; it is not a
reference/fast fidelity failure.

These are open-loop **demonstration diagnostics**, not learned-policy,
independent held-out, three-seed robustness, full 60-second study evaluations
or final-game evidence. The selected historical expert and familiar noise
streams are not new IID trials. Keep active metrics and the primary learned
completion metric unchanged. The eight short legal landings make this expert
a plausible demonstration source, while the miss motivates reactive recovery/
observation-action data rather than assuming a memorized time sequence is
sufficient.

Evidence: `artifacts/expert_robustness_probe_20261004T070002812275Z/`.
Next priority remains completed seed-5 outcomes and verified terminal PAUSED.
Conditional future hypothesis: collect provenance-bound ordinary-start
observation/action demonstrations, check identical or nearby observation
states for conflicting time-indexed targets, then separately predeclare an
imitation-plus-recovery/RL comparison. No such training, new reservation,
deployment, source change or paid batch is launched by this diagnostic.

### Demonstration-assisted learning foundation implemented locally

The user explicitly requested implementation after the literature review.
`research.demonstrations` now collects **pre-action** raw 217-feature
observations and actual legal float32 targets from ordinary spawn. It uses
training reset 6001/noise streams 9100..9105, separate from standard evaluation
1001/8100..8105. The same original physics, reward/history observations,
one-tick absolute interface and both frozen metrics are preserved.
Bounded NPZ/JSON persistence verifies hashes, shapes, finite/legal values,
non-pickled data, game/environment provenance and physical eligibility.
Failed expert trajectories stay in the data with false training eligibility.

Nine 600-tick expert collection cases produce **5,400 physical rows**; six
pass the frozen central detector. **3,576 rows** are BC-eligible after removing
forced 12-tick left/right warm-up labels. Teaching opposing externally imposed
warm-ups at the same spawn caused an exact-state target conflict of about
1.0035; those intervention labels are not policy targets. After exclusion, one
exact-state conflict remains with target range about 0.0281, attributable to
the varied demonstrated actions. Near-state ambiguity and off-trajectory
corrective expertise remain untested. Do not call this time-indexed teacher
a DAgger oracle.

A first nominal reference comparison passes observation/action equality but
fails direct metadata equality because Python tuples become JSON lists.
Descriptors are now canonically serialized, and a new corpus is collected
without overwriting the first artifacts. The corrected **600-tick nominal
reference/fast raw pre-action observations, actions and outcome info match
exactly**. This does not verify all training streams or an upper route.
Corpus: `artifacts/demonstrations_20261004T072714652488Z/`.
Parity: `artifacts/demo_collection_parity_20261004T073039320276Z/`.

`research.behavior_cloning` implements actor-only PPO initialization using a
separate optimizer. It fits observation RMS on eligible demo data, freezes it,
and leaves value parameters, action log-std, fresh PPO optimizer state and RL
transition counts unchanged. Full cloning is deliberately **not admitted**
through this local smoke CLI. An eight-update/64-sample pipeline smoke lowers
supervised mean-square action error **0.255668 -> 0.145106**, but its short
nominal reference trajectory remains at spawn, with no hold/full completion.
This is working initialization machinery, not acquired climbing skill.

Saved model weights and frozen normalizer statistics match a repeated seeded
warm start exactly. A saved-model 128-tick reference/fast closed-loop check
has zero measured action/observation/reward/telemetry error and no success.
Smoke: `artifacts/cloning_smoke_20261004T073212387553Z/`.
Verification: `artifacts/cloning_pipeline_verification_20261004T073750651481Z/`.
All **187 Python tests plus JS collision tests pass**, including refusal to
silently extend a cloning smoke by repeatedly warming the same learner.

`research.imitation_study` records a **non-executing proposal** for fresh
seeds 6/7/8: scratch PPO, BC-only and BC-then-PPO, with common frozen demo RMS,
unchanged observations/reward/actions, central/secondary reference cases and
separate BC/RL sample and optimizer work. It is not equal total compute.
Plan: `artifacts/imitation_study_20261004T074252246079Z/plan.json`.
No new reservation, paid training, source upload, worker/queue change or
deployment occurred. The full clone/recovery/RL trainer, complete-study
checker and bounded worker admission still need integration and tests; the
current full-cloning guard must stay until those exist. Next bounded priority:
finish timing closure, then implement that admission and a genuine remote
first-skill comparison, not another viewer feature or unrestricted desktop
training. Preserve the $10 ceiling and require a fresh preflight/session/cap.

### Promising fine-control seed 5 and requested visible replay

Pinned dataset `0c07c5cbce7ae847715b815c044e668df363eff5` independently passes
the complete repeat-1 seed-5 manifest/training/reference contract. Its final
nine cases have **2/9 central and 5/9 secondary holds**, median retained gain
**82**, zero full completions and zero evaluation deaths. Nominal ends at
`(320.52873,104)`, retaining 83 and passing both hold metrics; hammer-left
also passes central at approximately `(333.28,103)`. This is the first
validated nominal learned hold in this timing study, but not robust all-seed
or full-game competence. Fine central counts across seeds 3/4/5 are 0/0/2,
secondary 1/0/5, so this configuration still lacks all-seed retention.

Training reports 393,216 controlled ticks, 4,440 reset ticks/37 resets,
zero short decisions, 3,840 actual policy calls and 1,450.23 learning seconds.
Final binary companions have immutable nonzero metadata; they were not
downloaded/reloaded. The full coarse cohort/terminal pause is not reviewed
in this implementation chunk. The latest actual-variable check at 07:19 UTC
had unchanged source/context/session/deadline, RUNNING, one never-sleep CPU
Upgrade replica. Read actual status again next invocation, not this historical
phase, before acting.
Evidence: `artifacts/visible_learned_run_20261004T072937674870Z/run_review.json`.

The user asked to watch the most promising run. `research.visible_replay`
checks all nine run contracts plus actual game/critical-source hashes, then
plays recorded nominal targets through the original renderer, with per-tick
body-position checks. It is labelled **recorded actions, not live training,
local inference or full completion**, runs near 30 Hz, pauses at the final
pose and repeats for at most 30 minutes.

Detached-process viewer attempts fail first from a Git dependency and then
ChromeDriver initialization; the native detached window does not persist
across command cleanup here. The browser-owned implementation uses Factory's
persistent Chrome Browser pane instead, not a saved user browser profile.
It is observed progressing through tick 587 without recorded-position error;
the user subsequently confirms seeing it sit on the ledge. Some later pane
inspection calls return an about:blank evaluation context despite the tab
listing the game. Do not claim that proves a replay failure or keep navigating
the user's requested view. They have been told that the policy stalls on this
ledge and cannot improve while replaying. Do not spend more research time on
viewer polish, do not portray this hold as the summit, and do not cancel the
operator merely because a run/study finishes.

### Complete timing study validated and cost closed

At the 2026-10-04 07:58 UTC closing review, actual variables still bind the
same closed timing session/source/context/deadline and the Space is PAUSED.
Worker `timing_complete` is durable with no error at pinned dataset
`05c589ad26da16a3cfe6885c2948990f45a6e9c5`. All six manifests, training
summaries and complete before/after reference traces pass the timing checker;
dependency/admission/game/assets and every recorded research-source hash
agree. New local imitation modules were never part of this deployed source.
All six final model/normalizer pairs (12 objects) have nonzero immutable
Hub metadata, but are not downloaded/reloaded in this closure.

| Repeat | Central holds, seeds 3/4/5 | Secondary holds | Median retained gains |
| --- | --- | --- | --- |
| 1 | 0/9, 0/9, 2/9 | 1/9, 0/9, 5/9 | 0, 23.57, 82 |
| 4 | 0/9, 0/9, 0/9 | 0/9, 0/9, 0/9 | 27.77, -30, 4 |

All untrained median gains were 0. There are **0/54 final full completions**
and **zero deaths within the 60-second evaluation horizons**. Both complete
arms have worst-seed central/secondary hold rates 0 and worst-seed completion
0; the predeclared worst-seed timing difference is 0. Fine seed 5's nominal
hold is genuine seed-specific progress, not robust all-seed success or full
climbing. Endpoint gains favor different arms for different seeds, so do not
claim a general timing improvement from these three structured pairs.

The final coarse seed 5 reports median retained 4, 393,190 actual controlled
ticks, 5,520 reset ticks/46 resets, 12 shortened terminal decisions,
3,840 actual policy optimizer calls and 764.95 learning seconds.
Across each full arm, policy calls total **11,520**. Fine/coarse controlled
ticks are **1,179,648 /1,179,553** (95 fewer coarse), reset ticks
**13,200 /18,120**, and learning wall seconds **4,303.33 /2,131.54**.
One-tick decision/gradient sample presentations are four times greater.
Equal planned exposure/calls do not imply equal realized physics, reset work,
compute or information. This is a diagnostic result, not CPU XL justification.

Independent verified PAUSED epoch `1791100724.3051379` closes the conservative
elapsed estimate at **$0.1001491661** for timing and **$0.2926961857** for all
closed sessions. The estimate intentionally includes time until operator
verification, including already paused time; it is not actual billing.
No new reservation, paid run, upload, variable change or restart occurred.
Evidence: `artifacts/timing_complete_review_20261004T075825867253Z/`.
The frozen pilot goal checker was rerun against the separate completed v2
snapshot and still reports zero worst-seed completion, no candidate/final goal.

The next hypothesis is demonstration-assisted reactive skill acquisition,
not more samples of this failed setup. Implement the complete proposed
remote-only scratch/BC/BC+PPO comparison and checker, preserve separate BC/RL
work, frozen demo RMS, no privileged reset and original reference cases.
Require fresh worker admission, passed preflight, independently verified
PAUSED and a new capped reservation before full learning. The existing
smoke-only guard stays until that integration is tested. No final-goal or
saved-policy portability claim follows from this closure; keep the operator
for further bounded useful work rather than cancelling at batch completion.

### Three-arm imitation/PPO trainer stages integrated locally

`research.imitation_train` now runs scratch PPO, BC-only and BC-then-PPO
through one explicit staged pipeline. All arms fit observation RMS once from
the same eligible demonstrations, freeze it before baseline evaluation and
keep it unchanged throughout cloning, PPO and reference evaluation. The
cloner can consume this pre-fitted RMS without refitting it. Original
observations/reward, one-tick absolute actions, physical-time gamma/GAE and
both frozen metrics remain unchanged; no privileged resets or recovery oracle
are introduced.

Each run writes provenance/data/normalization/settings, untrained reference
cases, optional post-cloning checkpoint/evaluation, final model/normalizer,
actual BC calls/presentations and separate PPO/controlled/reset work.
The local pipeline accepts only the small smoke settings. Actual model
rollout/batch/epoch/gamma/GAE/architecture must match those declared settings
before any work, preventing larger rollouts from silently exceeding the cap.
Full CLI execution and full function settings remain refused before data,
output creation or browser access until separate remote admission exists.
The existing legacy/timing trainer and worker are not changed.

Three ordinary-start pipeline smokes at seed 6 use the same 3,576 eligible
demo rows and shared frozen statistics. Scratch and BC+PPO each perform
**256 actual controlled ticks**, **120 reset-settling ticks** and **four PPO
optimizer calls**; BC-only consumes **zero RL/control/reset ticks**. Cloning
arms separately perform **eight BC calls /512 sample presentations**.
All declared reference stages use the nine original cases at 128 ticks each,
with reset work counted separately. Their short finals have no holds/full
completions/deaths and median retained 0; these are pipeline checks, not
learning-effectiveness evidence.

All three untrained nine-case reference traces are exactly equal. Saved
frozen mean/variance/count are exactly equal across arms. BC-only final policy
weights are bitwise equal to BC+PPO's pre-PPO clone checkpoint; saved gamma
and GAE match the one-tick physical-time contract. These checks establish
stage/normalization comparability, not cross-host robustness or upper-route
fidelity. Evidence:
`artifacts/imitation_three_arm_smokes_20261004T082101406129Z/verification.json`.
All **196 Python tests plus JS collision checks pass**.

The owned Space is independently rechecked PAUSED with its same closed timing
source/session/context/deadline. No upload, reservation, restart, new paid
training or settings change occurs. Next bounded priority is the strict
nine-run imitation campaign checker and Linux parent-bound worker admission,
then full-budget trainer dispatch under a fresh capped preflight/session.
Reuse these tested stages rather than another disconnected smoke or viewer
feature; do not remove full-run refusal until admission is real and tested.

### Nine-run imitation campaign contract/checker implemented locally

`research.imitation_campaign` now prepares and validates the declared
scratch/BC/BC+PPO comparison, sequential within fresh seeds 6/7/8. It has
only preparation/summarization commands and cannot execute jobs. Preparation
requires complete timing evidence without robust all-seed central retention,
validates the separate training demonstration streams/data hash, and freezes
eligible-observation normalization and current source/game provenance.
No paid reservation, worker dispatch or remote activation is conferred.

The strict JSON checker binds each full run to source/dependencies, admitted
session/deadline/corpus, full per-arm budgets, original one-tick ordinary-start
environment, raw reward/discount/GAE, frozen demo RMS and all nine original
reference cases. It validates untrained/after-cloning/final checkpoints,
separate 2,000 BC calls/512,000 presentations versus 3,840 PPO calls where
applicable, actual controlled/reset exposure and BC-only zero RL work.
Matched-seed initial reference traces must agree across arms; the two clone
checkpoints must agree before PPO. Changed/missing stages, data/settings,
forced reward scaling, mixed dependencies/admission and smoke evidence are
refused. Missing companion files remain incomplete. Three distinct complete
seeds are required per arm before candidate retention is considered, and
standard cases never establish final goal or automatic scaling.
Binary integrity, frozen saved-RMS contents and saved-policy portability
still need independent verification; this is a JSON checker, not a proof
that arbitrary metadata is authenticated physical evidence.

Initial validation has two recorded failures: a paired-trace test mutation
changed the trace but not its duplicated pre-reset final record, so it was
correctly rejected earlier than the expected invariant; the fixture is fixed.
Actual preparation then compared JSON list warm-ups with tuple descriptors
from the raw plan. It now uses the canonical serialized contract and has a
regression test. Neither failure affected the paused remote Space or learner.

Preparation against the complete trusted timing snapshot and 3,576-row
eligible corpus succeeds; all nine full runs remain missing/unlaunched.
Real before/after stage traces from all three bounded trainer smokes pass
their declared 128-tick physical case checks but are intentionally rejected
as full-study evidence. Synthetic full-budget fixtures test only checker
orchestration; no full learner/physics outcome is inferred from them.
Evidence: `artifacts/imitation_campaign_20261004T084341116202Z/checker_verification.json`.
All **205 Python tests plus JS collision tests pass**.

The owned Space remains independently checked PAUSED on the same closed
timing source/variables; cost ledger, historical deadlines and $10 ceiling
are unchanged. Next bounded priority: implement the Linux-only sequential
imitation executor/parent grants, pinned data/context/preflight transport and
worker integration, then enable full trainer/clone budgets only under that
tested admission. Keep the current full-run refusal until then. Do not
prepare another disconnected plan, polish the viewer or renew old sessions.

### Remote imitation admission, full-budget wiring and fresh preflight

`research.imitation_execution` now reuses the timing executor's generic
tested cost/source/preflight validator, with a distinct imitation protocol
and exact nine-check set. Linux-only sequential execution binds fresh
reserved source/session/deadline, dataset/normalization, effective capacity,
and a durable exclusive no-resume claim before the first learner. Per-run
grants bind direct parent PID, seed/arm, output/corpus paths and claim hash.
Stages require a loader-created permit, not an arbitrary metadata flag.
BC checks its deadline periodically; PPO checks each step; the parent keeps
the 60-second cleanup reserve and terminates only its owned process group.

Full 2,000-step actor BC and 393,216-transition PPO budgets are now wired
under that permit. Standalone local cloning CLI stays smoke-only; ungranted
full trainer calls are refused before data/browser/output access. Actual
model/physical settings remain guarded. The original timing/pilot paths and
scientific reward/observations/cases are preserved.

`deploy.imitation_worker` imports only the owned session's pinned bounded
context/corpus and reviewed closed timing JSON. Immutable remote byte sizes
are checked before download; hashes/declared data/RMS are rechecked locally.
Its fresh preflight has unit/JS/raw/reactive fidelity, benchmark/resources and
all three bounded arm smokes. Passed preflight auto-pauses. Study start needs
operator-reviewed exact passed evidence plus PAUSED, then durable dispatch
and claim before any full learner. Interrupted/terminal sessions cannot
silently restart. Worker backup now includes owned non-pickled NPZ data,
and the monitor selects only imitation runs, not imported timing results.

A focused package invocation exposes an existing bare-import assumption in
`tests.test_timing_worker`; the repository's instructed discovery runner
passes it and all legacy tests. No production regression is inferred from
that invocation error. All **219 Python tests plus JS collision checks pass**,
including the exact deployment snapshot's **422 checksummed payload files**.
All three updated
smokes preserve bitwise policy weights, frozen normalizer statistics and
every reference stage trace from the prior trainer smokes.
Evidence: `artifacts/imitation_admission_smokes_20261004T090039798467Z/verification.json`.
No substantial desktop training or numerical-policy robustness is claimed.

After local/bundle validation, the operator reverified private ownership,
PAUSED and one never-sleep CPU Upgrade replica and reserved the distinct
16-hour/$0.48 session before any launch. Source upload while PAUSED returned
`95a8e311664789bcf1be5c609dce148e1f300f93`, still PAUSED. The legal 5,400-row/
3,576-eligible corpus and context are privately published under new immutable
revisions. Only fresh session/mode/context/deadline variables change while
PAUSED; hardware, secrets and closed-session artifacts are not modified.
The intentional preflight restart and pinned initial state are recorded in
the current-state section above. This is preflight, not a nine-run learning
result, promotion or full-game claim. Do not poll or redeploy while it runs.

### Completed historical pilot, immutable evidence

- Private Space: `isHeSatoshi/rl-over-it-poc-20261004`.
- Private artifacts: `isHeSatoshi/rl-over-it-research-artifacts`.
- Completed dataset session: `poc-20261004-v2`.
- Historical deployed revision: `34c35854133294f97fef741479641f571371b8a3`.
- Interrupted historical session: `poc-20261004-v1`, revision
  `b3bf197090f1fb5219e5cce70a0dbfcca6576ce1`.
- Tier: CPU Upgrade, one replica, sequential nine-run pilot.
- Persisted deadline: **2026-10-04 12:21:08 UTC**, epoch `1791116468.8050392`.
- PPO/absolute, SAC/absolute, SAC/velocity, seeds 0/1/2, 98,304 transitions
  each. Four-tick actions, settled reward, terrain, raw rewards, common
  physical-time discount, reference evaluation.

**The full v2 pilot completed and automatically paused on 2026-10-04.**
A pinned review of dataset commit
`7c29b01d5cae53606f252511337a70b07a09699c` validates all nine runs under
their recorded source/game/reward/evaluation contracts. The original source
revision was retained at closing; it is now historical. Never mix these
completed outputs with the separately versioned timing diagnostic.
All 81 final reference cases have zero full-climb completions and zero deaths
within their 60-second horizons. PPO v1 holds are 0/9,0/9,1/9; both SAC
cohorts are 0/9,0/9,0/9. No variant passes follow-up or scale admission.
Worst-seed reference completion is 0; neither candidate nor final goal passes.
All nine final models/normalizers and all six SAC replay buffers are durable
at that immutable dataset revision, with nonzero sizes and Hub object metadata.
This closing review did not download/reload those large binary companions;
do not mistake durable presence for cross-host policy-transfer verification.
Evidence: `artifacts/v2_complete_review_20261004T024603257492Z/`.

The operator independently verified PAUSED at epoch `1791081974.4473813`.
The ledger is closed at a conservative v2 compute estimate of $0.153724,
or $0.192547 across v1/v2, including elapsed pauses/build/preflight time.
These estimates are not the actual provider bill. That pilot is closed;
the distinct active timing reservation is described above. Keep the operator
running for useful bounded research work.
Do not restart the completed pilot or overwrite either artifact session.
The next priority is the predeclared timing diagnostic, not promotion or
blind sample/hardware scaling. Timing-aware trainer/GAE/horizon and actual
training/reset tick accounting now pass local tests and bounded smokes.
Secondary-detector integration and bounded local timing-specific reactive
fidelity now pass. A distinct non-executing run contract/aggregator now passes
local tests. A remote-only sequential executor/admission foundation now passes
local tests and is now wired into fresh timing worker modes and narrowly scoped
trainer admission. Local integration checks and smokes passed before the
distinct capped timing reservation/deployment described above. Review durable
passed timing preflight evidence plus PAUSED before any intentional study launch. Direct remote
timing CLI use without a parent-bound run grant remains refused.

Never modify, upload, restart, or resize an active future image. The replacement
includes complete-prefix snapshots for append-only logs/CSV/JSONL; binary
checkpoints still require stable-copy checks. The historical v1 image could
skip continuously appended files, so its stale logs are not a stalled-learner
proof.

The completed pilot's original gates remain unchanged. A separately labelled
new diagnostic is allowed under the delegated authority, but is **not**
promotion of this failed pilot.

### Provider interruption and fresh replacement

On the 2026-10-03 21:35 UTC check, v1 was **SLEEPING** under the provider's
one-hour idle timeout, despite active background training. The operator
verified and requested PAUSED, then confirmed PAUSED. Three complete PPO runs
remain durable; SAC/absolute seed 0 has only a 20k checkpoint and telemetry
through transition 21,500, no final evaluation, and no saved replay buffer.
Do not silently resume that checkpoint or merge partial SAC into cohort results.
Incident: `artifacts/provider_sleep_incident_20261003T213845836829Z/`.

The explicitly fresh replacement session is **`poc-20261004-v2`**, with a full
new nine-run matrix under one new source snapshot, unchanged scientific
settings, corrected optimizer accounting, and append-only artifact snapshots.
This is a recovery/rerun, not promotion or checkpoint resume. Never overwrite
v1's artifact prefix. Replacement budget is reserved in the cost ledger.
Its deadline remains **1791116468.8050392**, with `RL_DEADLINE_EPOCH` enforced
in addition to the ordinary per-batch cap.

While PAUSED, the operator called `set_space_sleep_time(-1)` and configured
the replacement session in `preflight` mode. HF represents the paid-tier
never-sleep default by **omitting gcTimeout**, so `sleep_time` is `None`,
not necessarily `-1`. The verified API returned PAUSED with no finite timeout.
The new worker rejects finite sleep time, wrong hardware, or extra replicas.
Preflight must pass and auto-pause before any intentional switch to pilot.
The initial v1 epoch/source in older loop text is historical: read this state
and the actual configured session rather than overwriting it with old values.
Replacement source is uploaded as Space commit
`34c35854133294f97fef741479641f571371b8a3` from the allowlisted bundle
`artifacts/hf_bundle_20261003T214507412596Z/`. Its explicitly fresh preflight
restart returned BUILDING. Local replacement validation passes **87 Python
tests plus JS tests**.
The active operator was replaced with updated session-aware instructions.
The replacement's remote preflight subsequently completed and auto-paused.
A pinned dataset review verifies all 87 tests, JS checks, 17 fidelity cases with
zero measured error, exact game/source fingerprints, effective 8 CPU /32 GB
quota, never-sleep policy, and the unchanged deadline.
Benchmark: about 247 terrain-enabled decisions/s without optimization;
worker plus reference peaked at about 6.07 GiB summed RSS.
Review: `artifacts/v2_preflight_review_20261003T215809890172Z/`.
After those checks, the operator intentionally changed only `RL_MODE` to
`pilot` while PAUSED and requested a fresh start. It returned BUILDING on the
same source revision. No checkpoint or prior run was resumed or mixed in.
The replacement's first completed PPO/absolute seed-0 run is contract-validated:
98,304 transitions, 0/9 v1 holds, no full completions, no deaths in the final
reference horizons, and median retained gain 24. It reports 3,840 actual policy
optimizer calls versus the separately labelled SB3 counter 480. Learning wall
time was 813.01 seconds. These physical outcomes agree with historical seed 0,
but the runs remain separately recorded under their own source snapshots.
Evidence: `artifacts/v2_run_review_20261003T222052247473Z/`.
Replacement seed 1 subsequently passes contract aggregation with 98,304
transitions and 3,840 optimizer calls: 0/9 holds, no full completions/deaths,
median retained gain 43.51. The cohort remains incomplete; no promotion.
Review: `artifacts/v2_two_run_review_20261003T224226570388Z/`.
The complete replacement PPO cohort subsequently validates at v1 hold counts
0/9, 0/9, 1/9, with no full completions or final-horizon deaths. It reproduces
the historical cohort's aggregate physical outcomes, without pooling sessions.
The first SAC/absolute run is actively training; no SAC effectiveness conclusion
is available yet. Review: `artifacts/v2_ppo_cohort_20261003T225813655321Z/`.
SAC/absolute seed 0 subsequently completes and passes contract aggregation:
98,304 transitions, 0/9 holds, no full completions/deaths, median retained
gain 0. Every final case remains at `(0,21)`. Its nominal predicted Y target
stays positive, approximately `[0.704,0.990]` normalized, and the hammer records
zero terrain-contact ticks while the body remains grounded for all 1,800 ticks.
This is a physically inactive controller outcome, not a control-bridge failure.
The exact cause of learning this behavior is not yet isolated; one seed does
not establish an algorithm-level conclusion.
It performs 88,304 actor, 88,304 critic, and 88,304 temperature optimizer calls
(264,912 total), with learning wall time 2,154.72 seconds, versus PPO seed 0's
3,840 combined-policy calls and 813.01 seconds at equal transitions.
Calls are different operations, not equivalent FLOPs. Both sample and wall-time
comparisons must remain explicit. A durable final SAC replay buffer is present;
only JSON metadata was downloaded for this review, not the large replay object.
Evidence: `artifacts/v2_first_sac_review_20261003T233847089245Z/`.
SAC/absolute seed 1 subsequently passes the same contracts with 98,304
transitions and 264,912 named optimizer calls, learning wall time 2,180.17
seconds, 0/9 holds, no full completions/deaths, and median retained gain 0.
Its nominal body remains near `(0,20.57)`, predicted Y is approximately
`[0.821,0.988]`, hammer contact is zero, and body contact covers all 1,800 ticks.
Across final cases the body stays at X=0 with Y approximately 20.57 or 21.
A final replay buffer is durable. This repeats the inactive/above-ground-hammer
outcome at a second training seed under this configuration and sample budget.
The three-seed cohort remains incomplete, but these failed seeds already
prevent its predeclared all-seed promotion gate; do not silently loosen it.
Evidence: `artifacts/v2_second_sac_review_20261004T001803114793Z/`.
The complete SAC/absolute cohort subsequently validates **0/9 holds in all
three seeds**, zero full completions/deaths, and median retained gain 0 for
each. Seed 2 repeats the grounded/no-hammer-contact outcome: nominal `(0,21)`,
predicted Y approximately `[0.273,0.987]`, zero hammer contact and 1,800 body
contact ticks. It records the same 264,912 named optimizer calls and 2,166.11
learning seconds. All three final replay buffers are durable.
This source/configuration/budget fails the predeclared gate and is not eligible
for broader-climb scaling. Do not generalize this to all SAC variants or game
solvability. The three velocity-action SAC runs remain in the unchanged queue.
Evidence: `artifacts/v2_absolute_cohorts_20261004T005803065949Z/`.
SAC/velocity seed 0 subsequently passes contract validation: 98,304 transitions,
264,912 named optimizer calls, 2,092.21 learning seconds, 0/9 holds and no full
completions/deaths, but median retained gain 6 rather than complete inactivity.
Its nominal case finishes near `(86.83,27)`, retaining 6 units, with 18 hammer
contact ticks and 1,776 body-contact ticks. Other cases retain roughly 0..8 units
on low terrain and reach X up to about 210. This is physical movement under
velocity control, not first-platform retention or robust climbing.
One seed remains insufficient for the parameterization comparison. Because
this seed fails the frozen all-seed gate, the variant cannot qualify for the
current follow-up even if later seeds improve; preserve their remaining runs.
Evidence: `artifacts/v2_first_velocity_review_20261004T013812716866Z/`.
SAC/velocity seed 1 subsequently validates at 98,304 transitions, 264,912 named
optimizer calls, 2,114.77 learning seconds, 0/9 holds and no full completions/
deaths, median retained gain **31.91**. Its nominal endpoint is approximately
`(255.16,130.67)`, retaining 109.67 units, but not a body-supported landing.
Over its last four game seconds, decision-boundary X varies 243.31..255.16
and Y 113.36..130.67, with 120 hammer-hit ticks and zero body-hit ticks.
This is a contact-rich lift/traversal trajectory, not settled platform support.
Two warm-up cases remain at spawn; other final cases retain roughly 29..40.47
units. A final replay buffer is present. The velocity cohort still has one
missing seed, and both completed seeds fail the fixed retention gate.
Evidence: `artifacts/v2_second_velocity_review_20261004T021802585667Z/`.
SAC/velocity seed 2 subsequently completes and validates: 98,304 transitions,
264,912 named optimizer calls, 2,087.04 learning seconds, 0/9 holds and zero
full completions/deaths. Median retained gain is **3.51**, with nominal endpoint
approximately `(141.49,24.51)`, 1,723 hammer-hit ticks and 1,085 body-hit ticks.
The complete velocity cohort fails the frozen gate. Its untrained versus
trained median retained gains are respectively 26.54->6, 22.71->31.91,
25.40->3.51 for seeds 0/1/2. Therefore even low-terrain endpoint movement
must not be presented as consistent improvement from learning.
The complete matrix is validated and PAUSED, not awaiting another run.
Evidence: `artifacts/v2_complete_review_20261004T024603257492Z/`.

## How to inspect and measure

On Windows, from the repository, using the existing authenticated HF CLI:

```powershell
& .\venv\Scripts\python.exe .\tools\hf_research_status.py
hf spaces info isHeSatoshi/rl-over-it-poc-20261004 --expand runtime --json
```

Download only bounded, trusted JSON artifacts needed for aggregation into a
new uniquely named local directory, pinned to one private dataset commit.
Required: campaign.json and each completed run's manifest.json,
training_summary.json, evaluation.json. Treat an upload that has evaluation
but not its required companions as incomplete, not an experiment failure.

```powershell
& .\venv\Scripts\python.exe -m tools.research_goal_metrics --directory D:\absolute\artifact_snapshot
```

Linux equivalent: `bash autoresearch.sh /absolute/artifact_snapshot`.
The script only reads/validates artifacts. It must never train on the desktop.
`bash autoresearch.checks.sh` runs correctness checks on a suitable Linux
environment; Windows equivalent is unittest discovery plus the JS test.

The current source is mostly uncommitted pre-existing work. The research branch
preserves it. Do not use broad checkout, reset, stash-drop, or git clean as
"experiment rollback." Use new artifact directories, isolated future source
snapshots/worktrees, or restore only known agent-created changes. Do not stage
unrelated existing work or alter Git identity.

## Bounded spending and failure handling

- Retain the current persisted 16-hour deadline; do not reset it.
- For future batches, use distinct session IDs and a persisted start/deadline.
  CPU Upgrade batches: at most 16 hours. CPU XL capacity benchmarks: at most
  30 minutes; initial XL training batches: at most four hours.
- Begin with one active run. Raise concurrency only after owned-process,
  optimizer, cgroup, memory, disk, and fidelity measurements justify it.
- Verify live pricing before changing tier. Previously quoted pricing was
  $0.03/hour CPU Upgrade and $1/hour CPU XL.
- Maintain a cumulative estimated paid-compute ledger. Initial operating
  ceiling is **$10 including the current pilot**. Do not silently renew this
  ceiling or assume HF credits are unlimited. At the ceiling, pause paid
  compute, preserve state, continue cost-free analysis, and report the blocker
  without asking another decision question.
- The ledger is `autoresearch.costs.json`. Reserve the planned maximum batch
  charge before launching; count elapsed time conservatively, including pauses,
  until a verified end is recorded. This estimate is not the actual HF bill.
- Pause the owned Space at batch completion, terminal failure, or deadline.
  Verify PAUSED and durable outputs. Never automatically resume a partially
  lost batch: recovery needs explicit source/checkpoint and replay-state
  integrity tests, or a separately labelled fresh experiment.
- Keep repos private. No public redistribution, GPU tiers, additional paid
  providers, real user browser sessions, unrelated processes, or account
  changes. Strip credentials from child processes and never log them.

## Hypothesis and expansion policy

For each future experiment, write its hypothesis, baseline, frozen settings,
sample and physical-time budget, seeds, evaluation cases, and stopping rule
before execution. Change one substantive factor where possible. Keep a
positive result only after full contract checks and independent replication.
Record failed experiments and why they failed; do not erase them.

1. If the current pilot passes its predeclared first-ledge gates, use its
   controlled broader-climb follow-up, not immediate large-scale training.
2. If it fails, prioritize **action timing/feedback**. An exact legal per-tick
   trajectory already reaches and holds the first ledge; resampling it to
   four-tick actions at phase zero fails. Other sampling phases can land and
   hold the same platform outside the narrow benchmark region. Test one-tick
   versus four-tick control with matched
   physical exposure, physical-time gamma, horizon, warm-up duration, and
   evaluation duration. Separately report decision and optimizer budgets.
3. If timing alone is insufficient, investigate exploration/skill acquisition:
   legal successful trajectories, imitation pretraining, outcome-conditioned
   replay, or structured curricula. Synthetic placement/calibration must stay
   separate from ordinary-start evaluation and be explicitly labelled.
4. Scale samples only for a physically improving, reproducible controller.
   Scale hardware only for a measured resource constraint or useful parallel
   throughput, not to hide a failed hypothesis.
5. Final completion verification uses frozen held-out cases, upper-route
   fidelity, legal ordinary-start trajectories, and saved-policy replay.

## What's been tried

- The legacy Node backend lacked renderer collisions, fixed body X, and
  confused controller memory with contact. Legacy learning claims are invalid.
- The original compiled game plus real renderer is causally validated.
  Fast exact-query caching matches reference on tested traces. Full upper-level
  fidelity is not yet established.
- Original controller offsets are player-relative, with eased/clamped reach.
  Body spawns at Y=21; real contact-based actions move and lift it.
- Legal bounded per-tick search holds the first ledge near `(322.59,104)`;
  four-tick resampling and the bounded four-tick search fail the hold.
- A matched 600-tick causal timing probe reproduces that per-tick success and
  all four held-action phases with **zero** fast/reference telemetry error.
  Phase 0 retains only 38.33 units. Phases 1/2 settle at approximately
  `(289.50,104)` / `(289.92,104)`, retain 83 units, and have body contact on
  every tick of the final four seconds. The original pilot's X `[305,335]`
  region rejects these genuine edge-supported platform landings.
  Keep the pilot contract frozen, but do not infer "four-tick control cannot
  climb" or "no platform support" from that narrow metric.
  A post-hoc **secondary diagnostic**, `first_platform_support_diagnostic_v2`,
  uses X `[285,345]`, the same Y/speed/three-second/body-contact requirements.
  It passes per-tick and coarse phases 1/2, not phases 0/3. It is neither a
  promotion gate nor learned-policy evidence. Declare/calibrate any new
  platform metric before a future learning experiment and retain v1 alongside.
  Evidence: `artifacts/timing_probe_20261003T211346899540Z/` and
  `artifacts/timing_support_review_20261003T211614229092Z/`.
- `climb-v2` reward is raw, potential-based, physically discounted, with observed
  settled-history state. Transient peaks and repeated contact are not success.
- Pilot PPO/absolute seed 0: 98,304 transitions, 0/9 reference ledge holds,
  0/9 full completions, median retained gain 24 versus baseline 0, no deaths
  in the nine 60-game-second final cases. This is movement, not climbing skill.
  Evidence: `artifacts/remote_pilot_review_20261003T204729761166Z/`.
- Pilot PPO/absolute seed 1 also completed 98,304 transitions with 0/9 ledge
  holds and 0/9 full completions, median retained gain 43.51, and no deaths
  within its final reference cases. Both runs pass contract aggregation.
  The three-seed cohort is still incomplete, so no variant-level selection
  is made. Latest pinned review:
  `artifacts/remote_goal_review_20261003T210724262386Z/`.
- The complete PPO cohort is now validated: v1 holds 0/9, 0/9, and 1/9 for
  seeds 0/1/2, with no full completions and no deaths in these final horizons.
  Seed 2's `action_noise_2` case holds by 5.33 game seconds, then stays near
  `(328.75,104)` through the 60-second horizon, retaining 83 units.
  This is the first learned-controller ledge hold, not robust success or
  promotion. Nominal finals are approximately `(277.30,51.38)`,
  `(280.26,64.50)`, and `(652.03,54)`. The PPO cohort is recorded as failing
  the robustness gate; finish both SAC cohorts before selecting the next batch.
  Evidence: `artifacts/remote_ppo_cohort_20261003T212305324947Z/`.
- The 20k checkpoint visibly controls the real hammer and moves to about
  `(109.28,79.70)` in a short nominal trace. It is brittle. An evaluation's
  post-reset screenshot must not be presented as its final policy pose.
- The historical v1 pilot's PPO `training_summary.gradient_updates` stores SB3
  `_n_updates`, an epoch count rather than minibatch optimizer steps.
  The correction, now deployed in v2, uses removable Torch
  post-step hooks and `optimizer-step-calls-v1` per-optimizer counters.
  It leaves tested PPO weights bitwise unchanged, supports checkpoint save/load
  during instrumentation, and removes hooks after success/failure.
  Actual 128-transition game smoke integrations report PPO 8 policy calls
  versus internal counter 4, and SAC 64 actor +64 critic +64 temperature calls
  versus internal counter 64. These are pipeline tests, not climbing evidence.
  Evidence: `artifacts/trial_20261003T212111941726Z/` and
  `artifacts/trial_20261003T212200168900Z/`.
  Optimizer-call counts are not equal FLOPs or equal compute across algorithms;
  keep wall time, configuration, physical exposure and hardware alongside.

## Continuity and termination

Read this file, `autoresearch.jsonl`, `autoresearch.ideas.md`, and latest durable
remote status before every scheduled research action. The old monitoring loop
must be replaced because it forbids all follow-ups and cancels after the pilot.
The new operator may continue with bounded diagnostic/follow-up batches after
the current worker is paused and outputs are validated.

Cancel the operator on user interruption or independently verified final
success. On access/funds/safety blockers, stop affected paid actions and state
the exact limitation; do not claim to work or spend invisibly. At context
limits, save the journal and experiment log so the next invocation resumes.
Never promise that unlimited compute or indefinite scheduling guarantees a
solution. Do not ask "should I continue?"

Goal setup checks pass 68 Python tests, the JS collision tests, both Bash
entrypoint syntax checks, and read-only metric extraction against the pinned
partial pilot snapshot. Windows' default WSL Bash is broken on this host;
Git Bash syntax validation succeeds. Use the venv Python directly on Windows.
The timing diagnostic subsequently passes all 75 Python tests plus JS checks.
Future-snapshot optimizer accounting subsequently passes all 81 Python tests,
JS checks, and bounded real-game PPO/SAC integration checks.
Recovery admission/deadline safeguards subsequently pass all 83 Python tests
plus JS checks. A first assertion expected literal sleep_time=-1; inspection
confirmed HF's paid-default None representation, and tests now cover both.

## Prepared next-snapshot shutdown hardening

The live v2 source remains unchanged. A **local-only** worker correction bounds
initial/final artifact flushing to 20 seconds and pauses even if upload fails
or hangs. It covers normal completion, expired budget at boot, interrupted
restart refusal, deadline watchdog, and fatal startup handling. This addresses
an unbounded final `sync()` after the live worker stops its watchdog. Periodic
snapshots and the external operator remain the current live safeguards.
Do not deploy it mid-pilot; apply it only in a future paused source snapshot
with fresh preflight. A timed-out flush may leave the last snapshot incomplete,
so verify durable models/evaluations/replay before any recovery or promotion.

The correction passes **90 Python tests plus JS checks**, including successful,
failed, and deliberately blocked upload fixtures proving pause still occurs.
No changes to learner, reward, physics, budget reservation, or live deployment.

## Learned-trajectory transfer verification

A local-only extension of `research.policy_fidelity` can replay any declared
standard perturbation with the same reset seed, warm-up actions, and action
noise stream as the standard evaluator. Tests preserve legacy fixture behavior
and check exact seeded-noise/warm-up semantics. All **93 Python tests plus JS
checks** pass. Do not deploy diagnostic changes into the running pilot.

Using the trusted historical PPO seed-2 final checkpoint and its frozen matching
normalizer, `action_noise_2` reproduces the v1 hold on both original reference
and fast backends for 96 decisions (12.8 game seconds). Predicted/applied actions,
normalized observations, rewards, physical/outcome info, and recorded telemetry
agree. Both retain 83 units and report `first_ledge_v1=True`; neither completes
the game. This is a selected learned-controller outcome under a declared noise
stream, **not** a held-out robustness test or general climbing competence.
Checkpoint download provenance and original game/environment fingerprints are
checked before loading. Evidence:
`artifacts/trusted_ledge_policy_20261003T224013267424Z/` and
`artifacts/policy_fidelity_20261003T224034122281Z/`.

### Secondary edge-support and inference-portability limitation

The replacement seed-2 `action_noise_5` evaluation remains at about
`(296.15,104)` but never satisfies v1's central X region. A coordinate-only
scan identified it as a candidate, not certified support. Replaying its exact
recorded remote actions for 384 ticks verifies real secondary platform support
by 7.13 game seconds, with **zero** measured local-fast/reference telemetry
error and **zero** remote-recorded body-position error at decision boundaries.
Evidence: `artifacts/recorded_edge_replay_20261003T230135948311Z/`.

However, loading the same trusted replacement checkpoint/normalizer for local
closed-loop inference does **not** reproduce that edge landing. Its predicted
action first differs from the remote trace at decision 2 by about 6e-8, while
body positions still agree then. The local fast/reference closed-loop traces
agree with each other but finish near `(88.59,38.04)` after 96 decisions.
Evidence: `artifacts/learned_edge_audit_20261003T225954450734Z/` and
`artifacts/v2_edge_policy_20261003T225850873712Z/`.

This separates reproducible recorded-action physics from a brittle portable
policy-inference outcome. Numerical inference/observation sensitivity is a
candidate cause; its exact origin is not yet isolated. Do not claim a portable
edge skill or alter the pilot gates. Future robust-policy studies should include
fixed-input inference comparisons and tiny-action/observation perturbations,
not just backend equivalence or selected seeded-noise success.

### Causal check of early action drift

The first body-position difference in the local/remote edge comparison occurs
at decision 7, about 0.00125 world units. Target differences grow above 0.01
pixel at decision 10, above 0.1 pixel at decision 15, and above 1 pixel at
decision 16; they later reach about 254.71 pixels within the 96-decision window.

A bounded three-case exact-game replay tests the recorded baseline, changing
only decision 7's X target by about 0.000252 pixel, and substituting all first
seven local applied targets (maximum change about 0.00253 pixel) while retaining
the recorded suffix. **All three still hold the platform**, retain 83 units,
and have zero measured fast/reference error. The perturbed final X positions
differ from baseline by less than 0.001 unit.
Evidence: `artifacts/action_sensitivity_20261003T231829646100Z/`.

Thus those early tiny action changes alone do not destroy the landing under
the fixed suffix. The failure involves later closed-loop amplification, rather
than a demonstrated catastrophic open-loop physics sensitivity at the first
drift. Exact observation/network/normalization causes remain unisolated.
Prioritize fixed-input inference and observation-path diagnostics, and robust
reactive control, before declaring that higher sampling rate or more compute
is the solution. These are post-hoc causal diagnostics, not policy promotion.

### Fixed-input inference fixture

A local-only `research.inference_probe` extracts continuous next-observation/
next-action pairs from saved policy traces, rejects auto-reset boundaries,
and hashes the normalized float32 fixture and trusted model. It runs no
physics and no training. This creates a portable fixture for a later
paused-host comparison without changing current inference or the live image.

On 95 fixed 217-dimensional inputs from the failed local edge rollout,
singleton inference reproduces its recorded actions **exactly**, including
repeat calls and tested thread counts 1/2/4. Batch sizes 8/95 produce maximum
normalized-action differences about 6.56e-7 /6.85e-7 (pointer differences below
0.000088 pixel). This demonstrates within-host inference-level rounding
differences under batching, independent of feedback/physics.
It does **not** establish that batching or thread count caused the live
remote/local divergence; the live evaluator uses singleton inference.
Local Torch is `2.6.0+cu124` running on CPU; deployed Torch is `2.6.0+cpu`.
Evidence: `artifacts/inference_probe_20261003T235912700282Z/`.
All **98 Python tests plus JS checks** pass. The source is local only and must
not be deployed during the current pilot.

## Conditional next-study preparation

`research.timing_study` now prepares a **non-executing** predeclared timing
comparison, conditional on finishing the pilot with no eligible follow-up.
It is not a launch, promotion, new reservation, or modification of the pilot.
Plan: `artifacts/timing_study_20261004T004121165329Z/plan.json`.
All **103 Python tests plus JS checks** pass.

PPO/absolute repeats 1/4 use new training seeds 3/4/5, the same original game,
terrain/raw settled reward/ordinary start, matched nominal 393,216 controlled
physics-tick budgets, 400-second episodes and 60-second evaluations.
One-tick decisions are 393,216 versus 98,304 for four-tick decisions.
Rollouts/minibatches are 8,192/1,024 versus 2,048/256, keeping 48 rollouts,
10 epochs and 3,840 planned optimizer calls per run. Gamma **and GAE lambda**
are scaled to equal physical-time decay. Warm-ups and noise offsets are held
for the same physical durations, not the same number of decisions.

This is not equal FLOPs or identical gradient information: the one-tick arm
has four times more decision/gradient sample presentations and observation/RPC
overhead. Terminal short steps can also change actual exposure; report actual
controlled ticks and reset-settling ticks separately. Do not mislabel nominal
budget matching as identical realized physics exposure.

The plan requires timing-aware trainer/evaluator/perturbation implementation,
frame-skip-specific fidelity and smoke checks, physical calibration of a
separate platform-support diagnostic alongside frozen v1, and a new bounded
session/reservation before it can execute. The preparation module cannot
launch training or bypass current campaign gates. If the remaining pilot
produces a legitimately eligible variant, prioritize its gated follow-up
instead of automatically executing this conditional plan.

### Secondary-detector physical calibration completed

A bounded **placement-only calibration**, explicitly `NOT_POLICY_SUCCESS`,
tests proposed platform-support X positions 285,290,296,320,340,345 by dropping
the body from Y=150 through original gravity with neutral pointer commands.
All six settle near Y=103/104 and pass the three-second/body-contact/speed
secondary detector. Only central X=320 passes the original narrow v1 region.
Outside positions X=250 and X=360 settle on low ground and fail; a 60-tick
contact window at `(320,104)` fails the three-second requirement.
All nine reference/fast calibration traces have zero measured telemetry error.
Evidence: `artifacts/support_calibration_20261004T011827646610Z/`.

This validates the secondary descriptor at the sampled physical positions and
negative cases, not every possible contact/trajectory or learner performance.
It remains separate from ordinary-start policy outcomes and does not alter
pilot reward/gates. The conditional timing study's calibration prerequisite
has evidence; timing-aware implementation, further preflight, finished-pilot
admission, and a new budget/session are still required before any launch.

### Physical-time perturbation controller prepared

`research.case_clock.PhysicalCaseClock` is a local-only future-study helper.
It indexes legal warm-up targets and seeded action-noise offsets by controlled
physics ticks. It reproduces the existing four-tick evaluator's applied actions
exactly for all nine declared cases, and gives one-tick control the same
four-tick noise offset cadence while allowing its model prediction to update
every tick. Warm-up lasts 12 physical ticks in either arm, not 12 one-tick
decisions. Clock regression/repeated calls/skipped blocks are refused.

All **109 Python tests plus JS checks** pass, including old-evaluator equality,
shared noise streams, held-noise/changing-policy separation, warm-up duration,
and noise-after-warm-up behavior. It is not integrated into the live evaluator,
does not execute the conditional plan, and is not deployed. Timing-aware
trainer/evaluator integration and fresh fidelity remain outstanding.

### Timing-aware evaluator integrated locally

`research.train.evaluate` now accepts explicit one/four-tick control and an
opt-in physical case clock. One-tick evaluation refuses legacy per-decision
perturbations or incompatible policy/normalizer/reward discounts. The default
four-tick path preserves existing case descriptors, trace rows and record keys.
The opt-in `physical-case-evaluation-v1` records requested versus actual
controlled ticks and reset-settling ticks separately, including VecEnv's
automatic reset after terminal/truncated steps. Final info remains pre-reset.
Cleanup now also runs if prediction/stepping fails.

All **117 Python tests plus JS checks** pass. Eight new synthetic tests cover
legacy traces, one-tick warm-up/noise duration, frozen normalization, short
terminal steps, incompatible configuration and failure cleanup.
`research.evaluation_timing_probe` runs no training and caps its fixture at
128 controlled ticks per case. A 96-tick constant-action ordinary-start check
passes all nine declared cases for repeats 1/4: **18 exact reference/fast
evaluation trace matches**, zero measured normalized-observation error, and
exact legacy/new four-tick trace equality on both backends. Each case reports
96 controlled ticks and 240 initial/automatic reset-settling ticks.
Evidence: `artifacts/evaluation_timing_probe_20261004T024404911122Z/`.

This is evaluator/fixture evidence, **not policy success** or comprehensive
one-tick reactive-policy fidelity. It is local only, not deployed or wired
into the trainer CLI. Remaining next-study work: trainer timing/GAE/budgets,
actual training/reset exposure, secondary-detector integration, independent
closed-loop fidelity/smokes, runner and new bounded-session admission.

### Timing-aware trainer and physical-work accounting integrated locally

The trainer now has an explicit `--timing-study --frame-skip 1|4` path.
`research.training_timing.training_settings` derives its full-run budgets,
rollouts/minibatches, physical-time gamma/GAE and episode/evaluation horizons
from the prepared plan; it refuses changed full-run budgets, reward settings
or algorithm. Smoke reductions are labelled pipeline-only and also preserve
matched nominal physical time. Trace/checkpoint intervals use physical cadence.
The legacy path keeps its former PPO/SAC learner defaults and four-tick
evaluation semantics. Timing-study **remote execution is explicitly refused**
until the bounded runner/preflight admission is implemented. This is not a
reservation, deployment, new study launch or promotion.

`PhysicalWork` observes successful steps and resets without changing returned
observations/rewards/info. It checks actual tick differences against telemetry,
counts terminal short decisions, and reports controlled versus reset-settling
work separately. Training summaries/trace rows now retain this actual exposure;
preflight/evaluation/runtime boot work are explicitly outside that scope.
Synthetic tests cover auto-resets, short terminals, invalid telemetry and
bitwise PPO/SAC weight equality with accounting enabled.
All **128 Python tests plus JS checks** pass.

Two matched ordinary-start **pipeline-only** smokes use training seed 3,
256 one-tick versus 64 four-tick transitions. Each reports **256 actual
controlled ticks, 120 reset-settling ticks and four policy optimizer calls**.
Both frozen-reference evaluations use all nine cases before/after for 128
controlled ticks per case, plus 240 initial/automatic reset ticks. Saved model
and 217-dimensional normalizer reloads preserve matching gamma and each arm's
physical-time GAE. Both have zero ledge holds/full completions in these short
horizons; this is pipeline correctness, not timing effectiveness or learning.
Evidence: `artifacts/timing_trainer_smoke_20261004T0302556740868Z/`,
including `verification.json`. No remote settings or source changed.

Next bounded priority: secondary support integration alongside frozen v1 and
independent contact-rich one/four-tick closed-loop fidelity, then the distinct
bounded session/runner/preflight. Preserve the existing pilot artifact prefix.

### Secondary support and contact-rich timing fidelity integrated locally

`research.study_metrics` adds the calibrated platform-support tracker only
under an explicit future-study contract, before the first environment reset.
It retains the original v1 descriptor unchanged and refuses an already changed
tracker. The timing-study trainer, evaluator and policy-fidelity rollout all
use both declared metrics. Legacy runs retain v1 alone. This is diagnostic
info, not a reward term or extra observation. The original campaign aggregator
must continue rejecting a changed pilot metric contract; the future timing
runner needs its own source-pinned aggregation for the declared two metrics.

The independent fidelity rollout now supports saved one/four-tick timing
contracts, physical-time warm-up/noise and per-arm discounts. Its comparison
checks exact predicted/applied actions and outcome/reward info, normalized
observations, rewards and decision-boundary runtime telemetry.
`research.timing_fidelity` uses an **untrained observation-dependent network**
whose legal downward target varies with the current observation. It performs
no learning or placement, caps each case at 512 controlled ticks and can run
headless on a future isolated preflight host.

Six ordinary-start checks, repeats 1/4 times nominal/hammer-left/noise-2,
each consume 384 ticks and pass **zero measured reference/fast differences**
in normalized observations, rewards and decision-boundary numeric telemetry,
with exact actions/info and production-evaluator trace equality. Each has
368..383 hammer-hit ticks, 3..17 body-hit ticks and varying predicted actions.
Retained gains are approximately 18.65..21.67; all central/secondary holds and
full completions are false. This verifies a contact-rich feedback path, not
learned climbing, every intermediate tick, cross-host portability or upper
route fidelity. Evidence: `artifacts/timing_fidelity_20261004T032235733238Z/`.
All **137 Python tests plus JS checks** pass.

Matched trainer smokes after adding the diagnostic retain **bitwise-equal
PPO weights and frozen normalizer statistics** to the prior timing smokes.
Training traces and all nine before/after reference case traces are identical
except for added secondary-metric info. Both arms still count 256 controlled
ticks, 120 reset ticks and four policy optimizer calls, with 217 observations.
Evidence: `artifacts/secondary_metrics_smoke_20261004T0324127860597Z/verification.json`.
No remote source/settings, budget reservation or pilot artifacts changed.

Next bounded priority: implement a distinct timing-study runner/aggregator
that freezes seeds/arms/metrics, validates all settings and dependencies, keeps
optimizer/actual controlled/reset work explicit, and enforces new session/
deadline/cost/preflight admission. Do not remove the CLI's remote-study refusal
until that admission is complete and tested. Then reserve a bounded CPU Upgrade
session and preflight a fresh private source snapshot; CPU XL is not justified
by these correctness checks.

### Separate timing-study contract and artifact checker prepared

`research.timing_campaign` prepares/checks the timing study independently of
the frozen pilot aggregator. It has **no execute operation and launches no
learner or browser jobs**. Full command generation is only a plan; the trainer still refuses
remote timing-study execution. Its six declared runs are sequential paired
repeats 1/4 within training seeds 3,4,5, with the original prepared budgets,
both metric descriptors and independent frozen reference cases.

Preparation requires the complete contract-validated nine-run pilot with no
eligible variant and refuses an existing output directory. It fingerprints
the current source/assets and retains a digest of prior pilot evidence.
Latest preparation:
`artifacts/timing_campaign_20261004T034517908263Z/timing_campaign.json`.
This is not a paid reservation, deployment or launch.

The JSON-only checker validates fixed settings/reward/normalization, gamma and
physical-time GAE, dependency/source/game equality, 3,840 actual policy calls
versus the separate 480 internal counter, actual controlled/reset work and
terminal short-step accounting. It rejects impossible reset counts given
episode horizons, counts exposure separately from requested ticks, checks all
nine legal seeded warm-up/noise action streams, metric contracts/latched hold
times, outcome-height agreement, contact counts and retained-spawn consistency.
Missing companion JSONs remain incomplete. Smoke results cannot be study
evidence. Three complete distinct training seeds per arm are required before
worst-seed arm comparisons; no automatic scale or final-goal verification.
Binary model/normalizer object integrity and independent saved-policy replay
remain separate requirements, not things this JSON checker establishes.

All **146 Python tests plus JS checks** pass, including nine new synthetic
acceptance/refusal tests. Real complete nine-case before/after traces from
both matched smoke arms pass the physical case checker and are deliberately
rejected as full-study artifacts. The prepared campaign reports six missing
runs, no comparison or success. Checker evidence:
`artifacts/timing_campaign_20261004T034517908263Z/checker_verification.json`.
The original pilot goal checker still reports 0 worst-seed completion and no
candidate/final success. No remote source/settings or ledger changed.

Next bounded priority: implement/test the remote-only sequential executor and
worker admission for a fresh distinct session, using explicit persisted budget
and source/preflight evidence, secret-stripped children, final-flush/auto-pause
and interruption refusal. Do not remove the trainer's remote-study refusal
until that admission is complete and tested. Then reserve/preflight a new
private CPU Upgrade snapshot; never relaunch or extend completed v2.

### Remote-only execution/admission foundation tested locally

`research.timing_execution` now provides a sequential six-run executor API
and strict admission validation. It is **not wired into `space_worker` or the
trainer CLI**, has no command-line execution entrypoint, and was not invoked
against a real learner. The trainer still refuses remote timing-study runs.
This is a tested foundation, not a claim that live deployment admission is
complete. No new reservation, upload, variable change or restart occurred.

Admission binds a distinct `timing-*` session to the owned Space/artifact repo,
declared contract, independently verified pre-launch PAUSED assertion, one
never-sleep CPU Upgrade replica, and all eight declared preflight checks on
the admitted source/game snapshot. It requires one active, unclosed reservation
with the same immutable Space revision/start/deadline, at most 16 hours, and
the $10 cumulative ceiling counting other elapsed/reserved charges. Source,
failed/incomplete preflight, expired/changed budget or another paid session
is refused. The parent must gather/verify that context from actual HF/runtime
and ledger evidence; this pure validator does not authenticate arbitrary JSON.

Execution requires isolated Linux, effective CPU/RAM/disk capacity and matching
prepared source/assets. It creates an exclusive execution claim before any
learner; an existing claim/run directory blocks all silent resume/reruns.
Only the declared paired seed order is scheduled, with per-run deadline and
complete artifact validation, and no new run after failure. Parent credential
variables are removed from child environments. Only its newly owned process
group may be terminated. Learners stop with a **60-second finalization reserve**
before the paid deadline; worker integration still must bound final upload/
pause and persist interruption evidence before dispatch.

All **157 Python tests plus JS checks** pass, including 11 new admission,
sequential scheduling, credential, deadline and interruption fixtures.
The first test attempt had three Windows fixture errors caused by globally
mocking `os.name` and assuming POSIX process-group attributes. A scoped host
predicate and mocked POSIX signals fix the fixtures without weakening the
real Linux-only guard. No real processes or provider state were affected.

A non-executing check against the actual closed ledger rejects completed
`poc-20261004-v2` as nonfresh and an unreserved diagnostic `timing-*` session
as lacking a reservation. Evidence:
`artifacts/timing_execution_checks_20261004T040407335016Z/verification.json`.
The actual Space remains PAUSED on its original source; its deadline and ledger
were not edited.

Next bounded priority: wire/test the worker's fresh timing preflight and study
modes, persisted source/ledger/context transport and initial/terminal durable
status, and the trainer's narrowly scoped admission check. Keep the existing
pilot path and completed artifact prefixes immutable. Only after integration
passes locally should a new capped CPU Upgrade reservation/private snapshot be
preflighted, reviewed while PAUSED and intentionally launched.

### Worker/trainer timing admission wired and tested locally

Local `space_worker` now recognizes `timing_preflight` and `timing_study` only
for a distinct `timing-*` session on the owned Space/private dataset. The old
preflight/pilot paths remain intact. `deploy.timing_worker` reads only
`<session>/operator/timing_context.json`, pinned by **`RL_CONTEXT_REVISION`** to
one immutable dataset commit, with a 2 MiB JSON bound. Context must contain the
ledger snapshot and ticket for the new reservation plus pinned prior-pilot
summary/source evidence. It is not bundled or stored in source code.

For timing preflight, the operator ticket's `preflight` must be null and there
must be no persisted session status. Reservation/runtime/source checks occur
before any jobs. The eight actual check processes include unit/JS, raw physics
fidelity, reactive timing fidelity, benchmark/resources and both matched
pipeline smokes; they are not substantive training. Only successful checks
produce durable `preflight_complete` with `study_kind=timing` and the eight
passed flags. The worker then bounded-flushes and pauses.

To intentionally start a study, the operator must independently verify that
preflight and PAUSED, then publish a new pinned context whose ticket contains
the exact durable preflight fields and set the fresh session to `timing_study`
while PAUSED. The worker rechecks actual immutable Space revision, runtime,
source/game and persisted budget. It imports only bounded JSON from the
completed pinned v2 pilot, validates the old ineligibility evidence, prepares
a fresh timing campaign and durably records dispatch/claim **before learners**.
Interrupted/nonfinal statuses block all restart/resume. Completed/failed or
wrong-kind preflight evidence cannot start a study.

Each trainer receives a parent-owned grant binding its direct parent PID,
declared seed/arm/budget, new output path and immutable execution-claim hash.
Linux/context/ledger/source/preflight/deadline admission is checked before
model/browser creation. The manifest retains a small admitted-session record;
the timing aggregator rejects missing/mixed admission sessions and binds
results to the claimed execution. Smokes remain explicitly unadmitted.
The parent runs/terminates only its owned learner/browser process group,
removes credential variables, preserves the 60-second finalization reserve,
and guarantees bounded final flush/pause paths.

All **168 Python tests plus JS checks** pass. New fixtures cover pinned private
reads, preflight-only commands, stale/repeated/wrong-source contexts, durable
pre-dispatch synchronization, interrupted sessions, initial sync failure,
successful mocked study dispatch, direct-parent/argument/claim grant checks,
and refusal after an undurable claim. Completed/failed sessions are preserved
without overwriting or relaunching. The read-only monitor now distinguishes
timing runs from imported prior-pilot files and reports secondary support/
controlled-reset ticks when present. These are mocks, not live HF admission.

Two bounded real-game smokes still report 256 controlled ticks, 120 reset ticks
and four policy calls per arm. Their weights are bitwise equal to prior smokes;
all nine before/after reference traces pass the physical checker. They claim
no remote admission or competence. The allowlisted bundle includes both
integration modules without runtime contexts/ledger/artifacts.
Evidence: `artifacts/worker_admission_smoke_20261004T0425133084373Z/verification.json`.
No HF writes, source/variable changes, paid reservation or remote jobs occurred.

Next bounded priority: verify current CPU Upgrade pricing, reserve a unique
`timing-*` session within the $10 total ceiling (including preflight/build
elapsed time), build/publish the allowlisted private snapshot while preserving
PAUSED and completed v2, and upload its secret-free operator context. Keep the
same new-session start/deadline through preflight and study; never reuse/extend
v2's old deadline. Run only `timing_preflight` first and independently inspect
its immutable outputs and PAUSED state before any study mode change.
