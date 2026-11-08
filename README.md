
## Offline chime regression tests

Install `requirements-test.txt`, then run:

```powershell
python -m pytest tests/test_chime_patterns.py
python -m pytest tests/test_home_assistant.py -k "package or system_trouble_and_notification_labels_are_independent"
```

These commands do not contact Home Assistant. The other tests in
`test_home_assistant.py` use the configured live Home Assistant API and can
change alarm state; run them only against an explicitly selected test instance.

The shared Chime Output controller gives entry/exit patterns priority over door
chimes during delay states. Outside delays, Chime on Open/Close labels retain
normal chime behavior. Each pulse uses the existing Chime Duration helper
(in tenths of a second; the unchanged default is 30 = 3 seconds). OFF times are
additional to that pulse duration:

| State | First 20 seconds | After 20 seconds |
| --- | --- | --- |
| Exit Delay | 1.85 seconds | 0.35 seconds |
| Entry Delay | 0.85 seconds | 0.10 seconds |

The OFF interval is selected when the pulse ends, using elapsed time since the
actual delay-state transition. A pulse or OFF interval already in progress at
20 seconds completes normally. Every alarm-state transition restarts the single
controller with an OFF command, cancelling any pending pulse or interval; the
alarm state's existing logic remains responsible for ending the delay. Startup
also clears the output. Siren control is unchanged.

The offline runner evaluates the YAML actions and templates with a simulated
clock, including documented restart semantics. It does not replace validation
inside a separate Home Assistant test instance or verify physical GPIO timing.
