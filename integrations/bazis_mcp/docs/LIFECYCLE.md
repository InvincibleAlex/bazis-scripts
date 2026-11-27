# Native command lifetime experiment

On 2026-10-22 the user started bridge 0.2.2, get_model succeeded, then
pressed Escape. The same session reported state=stopped, with zero key
events intercepted. Assigning Action.OnKeyDown/OnKeyUp and reading back
JavaScript functions did not establish actual native keyboard event delivery.

The installed Script.pdf (printed page 74) documents Action.Continue as
keeping the command alive after the script body returns. Action.AsyncExec
executes a callback with Get* requests available; it is not documented as
an independent background service. Modern interaction/execution namespaces
were absent in the original runtime diagnostic.

Do not replace the working bridge with an unverified background variant.
Do not restart a command from OnFinish or call native APIs from a worker
thread. An external process cannot acquire the embedded Model/Action API
merely by staying alive.

Run bridge/Codex_Bazis_Lifecycle_Probe.js manually in BAZIS. It returns
normally, without Continue or model access. It writes a local private
~/.bazis-mcp/lifecycle-probe.json, observes a Node timer for at most
45 seconds / 180 callbacks, then clears it if the host retains the timer.
It does not restart itself or intercept keys. Escape and ordinary BAZIS
commands remain available. Compare the report twice several seconds apart.

- ticks_after_finish increasing: timer survives native command completion;
  native model API validity and safe scheduling remain UNPROVEN.
- finish_callback_seen=true and ticks remain zero: timer execution did not
  survive in this observed state. Stale/absent reports require checking
  initialization; do not infer success or invent a background capability.
- no finish callback: cannot assert native action completion from timer ticks.

Mock checks: node tests/test_lifecycle_probe.cjs. These verify boundedness
and no model/Continue calls, not native lifecycle or Escape behavior.

## Native observation, 2026-10-22

The user ran the probe. The local report recorded the native OnFinish
callback about 2 ms after startup, phase=action_finished_waiting_for_timer,
timer_ticks=0 and ticks_after_finish=0. It remained in that state when read
more than 10 seconds after startup. The original bridge was stopped.
Thus this normal-completion experiment did not retain the Node timer.
It provides no evidence for a resident bridge after command completion,
and cannot isolate an Escape effect because normal completion happened first.
Keeping the existing active-command bridge is still necessary until a
native cancellation handler or a supported persistent integration is verified.
