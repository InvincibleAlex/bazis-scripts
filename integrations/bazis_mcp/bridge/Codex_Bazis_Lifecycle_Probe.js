// Read-only lifecycle experiment for BAZIS embedded Node 8.
// Deliberately does NOT call Action.Continue(), Finish() or Cancel().
// No model access, keyboard hooks, bridge requests or process launches.
// The timer is bounded to 45 seconds / 180 callbacks if the host retains it.
(function () {
    'use strict';
    var fs = require('fs'), path = require('path'), os = require('os');
    var reportPath = path.join(os.homedir(), '.bazis-mcp', 'lifecycle-probe.json');
    var timer = null, ended = false, started = Date.now();
    var report = {
        probe_version: '1.0', started_at_ms: started, updated_at_ms: started,
        phase: 'script_body', action_continue_called: false,
        finish_callback_seen: false, finish_callback_count: 0,
        timer_ticks: 0, ticks_after_finish: 0, done: false,
        limit_ms: 45000, max_ticks: 180,
        scope: 'Timer survival only; native Model/Action access after completion is NOT tested.'
    };
    function write() {
        report.updated_at_ms = Date.now();
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), 'utf8');
    }
    function end(reason) {
        if (ended) return;
        ended = true;
        if (timer !== null) clearInterval(timer);
        report.done = true;
        report.phase = reason;
        try { write(); } catch (_) {}
    }
    try {
        // Requires the existing local MCP installation, never writes to the model
        // or to shared folders, and never includes the authentication config.
        if (!fs.existsSync(path.dirname(reportPath))) {
            throw new Error('Configuratia locala MCP lipseste.');
        }
        write();
        Action.OnFinish = function () {
            report.finish_callback_seen = true;
            report.finish_callback_count++;
            report.finished_action_at_ms = Date.now();
            report.phase = 'action_finished_waiting_for_timer';
            try { write(); } catch (_) { end('report_write_failed'); }
            // No Continue/restart here. Observe what BAZIS does on its own.
        };
        timer = setInterval(function () {
            report.timer_ticks++;
            if (report.finish_callback_seen) report.ticks_after_finish++;
            report.phase = report.finish_callback_seen ? 'timer_after_action_finish' : 'timer_without_finish_notification';
            if (Date.now() - started >= report.limit_ms || report.timer_ticks >= report.max_ticks) {
                end('observation_complete');
                return;
            }
            try { write(); } catch (_) { end('report_write_failed'); }
        }, 250);
        report.phase = 'script_body_returning';
        write();
        // Return normally: the native host decides whether to retain the timer.
    } catch (e) {
        end('initialization_failed');
        if (typeof alert === 'function') alert('Test fundal MCP: ' + String(e.message || e));
    }
}());
