const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const source = fs.readFileSync(path.join(__dirname, '../bridge/Codex_Bazis_Lifecycle_Probe.js'), 'utf8');
function environment() {
    let latest, callback, cleared = 0, writes = 0;
    const context = {
        require(name) {
            if (name === 'fs') return {
                existsSync: () => true,
                writeFileSync(p, data) { latest = JSON.parse(data); writes++; }
            };
            if (name === 'path') return path;
            if (name === 'os') return {homedir: () => '/test'};
            throw Error('Unexpected module ' + name);
        },
        Action: {
            Continue() { throw Error('Must not continue the action'); },
            Finish() { throw Error('Must let host complete normally'); },
            Cancel() { throw Error('Must not cancel the action'); }
        },
        setInterval(fn, ms) { assert.equal(ms, 250); callback = fn; return 1; },
        clearInterval(id) { assert.equal(id, 1); cleared++; },
        alert(message) { throw Error(message); }
    };
    Object.defineProperty(context, 'Model', {get() {throw Error('Must not access model');}});
    vm.runInNewContext(source, context);
    return {context, tick: () => callback(), latest: () => latest, cleared: () => cleared, writes: () => writes};
}
const env = environment();
assert.equal(env.latest().phase, 'script_body_returning');
env.context.Action.OnFinish();
assert.equal(env.cleared(), 0);
env.tick();
assert.equal(env.latest().ticks_after_finish, 1);
for (let i = 1; i < 180; i++) env.tick();
assert.equal(env.latest().timer_ticks, 180);
assert.equal(env.latest().done, true);
assert.equal(env.cleared(), 1);
const disposed = environment();
disposed.context.Action.OnFinish();
assert.equal(disposed.latest().timer_ticks, 0);
assert.equal(disposed.latest().done, false);
const noFinish = environment();
noFinish.tick();
assert.equal(noFinish.latest().finish_callback_seen, false);
assert.equal(noFinish.latest().ticks_after_finish, 0);
console.log('Lifecycle probe: no model access, no Continue/restart, bounded observation, finish/no-finish paths passed. Native lifecycle still requires manual validation.');
