# Giza Validation Tests

## Highest-Value Tests

1. Lower water-air scale model
2. Well Shaft / vent capacity survey
3. Plug leakage and isolation test
4. Phased upper workcell mockup
5. Final-meter placement/seating trial
6. Precision restoration / reference drift trial
7. Residue mineral mapping
8. Midlevel granite replacement/load model
9. Throughput / lane-cycle trial

## Test 1 - Lower Water-Air Scale Model

Purpose:  
Test whether a water-applied lower node can be vented/reset without unsafe pressure.

Passes if:  
Vent/reset pressure remains below safe threshold while cycling works.

Fails if:  
Air locks, unsafe pressure, or no reset.

Affects:  
`water_applied_lower_node_gate`, `air_management_gate`.

## Test 2 - Well Shaft / Vent Capacity Survey

Purpose:  
Measure whether the Well Shaft / passage architecture can host the required displaced-air flow.

Passes if:  
Surveyed geometry and flow modeling show enough vent capacity with tolerable pressure decay.

Fails if:  
The path is blocked, too small, disconnected, or too lossy to vent the lower event.

Affects:  
`air_management_gate`, `guided_path_gate`.

## Test 3 - Plug Leakage and Isolation Test

Purpose:  
Test whether the granite plug zone can act as final isolation / decommissioning boundary.

Passes if:  
Plug seating geometry and leakage models preserve a meaningful lower/upper wet-dry contrast.

Fails if:  
Plug geometry cannot isolate air/water/residue domains.

Affects:  
`plug_isolation_gate`, `residue_prediction_gate`.

## Test 4 - Phased Upper Workcell Mockup

Purpose:  
Test whether upper-zone tasks can be physically hosted when sequenced rather than simultaneous.

Passes if:  
Movement, braking, final placement, correction, reference checks, casing finish, and access-removal repair fit in phased operations while meeting accepted-block throughput.

Fails if:  
Workers, ropes, blocks, levers, cribbing, references, casing correction, and access removal cannot coexist even when phased.

Affects:  
`upper_workcell_integration_gate`.

## Test 5 - Final-Meter Placement/Seating Trial

Purpose:  
Test the movement-to-placement transition: stopped, transferred, oriented, seated, checked, corrected, and accepted.

Passes if:  
Blocks can be seated and corrected before lock-in using period-compatible levers, wedges, packers, cribbing, and dressing.

Fails if:  
Delivery to the workcell cannot become accepted placement.

Affects:  
`placement_seating_gate`, `upper_workcell_integration_gate`.

## Test 6 - Precision Restoration / Reference Drift Trial

Purpose:  
Validate drift suppression rather than assuming perfect placement.

Passes if:  
Detection thresholds, reference stability, correction intervals, and restoration authority keep errors below lock-in thresholds.

Fails if:  
References drift, errors hide, or corrections cannot recover geometry in time.

Affects:  
`precision_restoration_gate`.

## Test 7 - Residue Mineral Mapping

Purpose:  
Test whether predicted lower wet/mineral zones, airflow paths, plug contrast, and upper dry/isolation behavior form a spatial pattern.

Passes if:  
Mineral species and contamination-controlled sampling match the predicted zone pattern.

Fails if:  
Residues are random, modern, substrate-only, or contradict lower-wet / plug-isolation / upper-dry predictions.

Affects:  
`residue_prediction_gate`, `plug_isolation_gate`.

## Test 8 - Midlevel Granite Replacement/Load Model

Purpose:  
Test whether the granite/chamber zone has a useful local role as stiff support, reference/control zone, load bridge, or transfer medium.

Passes if:  
Replacing granite with ordinary limestone causes measurable loss in structural/control budget under model assumptions.

Fails if:  
Granite gives no modeled or measured advantage.

Affects:  
`guided_path_gate`.

## Test 9 - Throughput / Lane-Cycle Trial

Purpose:  
Test whether ordinary mechanics can meet the repaired lane/cycle throughput without hydraulic block movement.

Passes if:  
Accepted-block throughput meets the required rate while maintaining braking, staging, correction, and safety margins.

Fails if:  
Cycle time, lane count, worker density, or staging losses drop accepted throughput below the required rate.

Affects:  
`ordinary_mass_movement_gate`, `placement_seating_gate`.
