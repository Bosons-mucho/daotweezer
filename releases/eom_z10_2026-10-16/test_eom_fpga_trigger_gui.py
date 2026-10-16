"""Offline automated tests -- not needed for normal use.

Run only when checking the GUI software. Uses simulated connections, does not
connect to a Red Pitaya, and does not load firmware or generate hardware pulses.
For normal operation, run eom_fpga_trigger_gui.py instead.
"""
import importlib.util
import io
import queue
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('updated_gui', Path(__file__).with_name('eom_fpga_trigger_gui.py'))
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
SETTINGS = dict(host='offline', user='root', password='', port=22,
                dio0_cycles=17, delay_cycles=31)


class Connection:
    def __init__(self, initial=0, statuses=None, fail=None, close_fail=False):
        self.tool = 'offline'
        self.mem = {g.REG_CTRL: initial}
        self.statuses = list([2] if statuses is None else statuses)
        self.fail = fail
        self.close_fail = close_fail
        self.started = False
        self.writes = []
        self.reads = []
        self.closed = False
        self.hook = lambda *args: None

    def write(self, addr, value):
        self.writes.append((addr, value))
        self.hook('write', addr, value)
        if self.fail == ('write', addr):
            raise TimeoutError('write timeout')
        if addr == g.REG_CTRL:
            self.started = value == 1
            self.mem[addr] = 0
        else:
            self.mem[addr] = value

    def read(self, addr):
        self.reads.append(addr)
        self.hook('read', addr, None)
        if self.fail == ('read', addr):
            raise TimeoutError('read timeout')
        if addr == g.REG_CTRL and self.started:
            return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return self.mem.get(addr, 0)

    def close(self):
        self.closed = True
        if self.close_fail:
            raise OSError('close failure')


class Clock:
    def __init__(self): self.now = 0
    def __call__(self): return self.now
    def sleep(self, dt): self.now += dt


def controller(conn, event=None):
    messages = []
    clock = Clock()
    return g.EOMController(conn, messages.append, event, clock, clock.sleep), messages


def worker(conn, action='trigger', event=None):
    obj = g.TriggerGUI.__new__(g.TriggerGUI)
    obj.events = queue.Queue()
    obj.clear_requested = event or threading.Event()
    with patch.object(g, 'FPGAConnection', return_value=conn):
        obj.work(action, dict(SETTINGS))
    return obj, list(obj.events.queue)


class ControllerTests(unittest.TestCase):
    def test_normal_completion_and_exactly_one_start(self):
        conn = Connection(statuses=[1, 1, 2])
        ctl, messages = controller(conn)
        ctl.trigger(17, 31)
        self.assertEqual(conn.writes, [(g.REG_DIO0, 17), (g.REG_DELAY, 31), (g.REG_CTRL, 1)])
        self.assertTrue(any('DONE=1' in s for s in messages))

    def test_short_sequence_can_complete_before_first_poll(self):
        conn = Connection(statuses=[2])
        ctl, messages = controller(conn)
        ctl.trigger(1, 1)
        self.assertTrue(any('DONE=1' in s for s in messages))

    def test_busy_and_hold_block_without_any_write(self):
        for status in (1, 2):
            with self.subTest(status=status):
                conn = Connection(initial=status)
                with self.assertRaises(RuntimeError): controller(conn)[0].trigger(17, 31)
                self.assertEqual(conn.writes, [])

    def test_invalid_status_blocks_without_write(self):
        for status in (3, 4, 0xffffffff, -1):
            conn = Connection(initial=status)
            with self.assertRaises(RuntimeError): controller(conn)[0].trigger(17, 31)
            self.assertEqual(conn.writes, [])

    def test_zero_out_of_range_and_bool_block_without_io(self):
        for value in (0, -1, 0x100000000, True, 1.0):
            conn = Connection()
            with self.assertRaises(ValueError): controller(conn)[0].trigger(value, 1)
            self.assertEqual(conn.writes, [])
            self.assertEqual(conn.reads, [])

    def test_readback_mismatch_blocks_start(self):
        conn = Connection()
        def hook(op, addr, value):
            if op == 'read' and addr == g.REG_DIO0: conn.mem[addr] = 99
        conn.hook = hook
        with self.assertRaises(RuntimeError): controller(conn)[0].trigger(17, 31)
        self.assertNotIn((g.REG_CTRL, 1), conn.writes)

    def test_state_changes_during_configuration_block_start(self):
        conn = Connection()
        conn.hook = lambda op, addr, value: conn.mem.update({g.REG_CTRL: 1}) if op == 'read' and addr == g.REG_DELAY else None
        with self.assertRaises(RuntimeError): controller(conn)[0].trigger(17, 31)
        self.assertNotIn((g.REG_CTRL, 1), conn.writes)

    def test_unaccepted_start_times_out_without_resend(self):
        conn = Connection(statuses=[0])
        with self.assertRaisesRegex(RuntimeError, '超时'): controller(conn)[0].trigger(1, 1)
        self.assertEqual(conn.writes.count((g.REG_CTRL, 1)), 1)

    def test_busy_then_unexpected_idle_is_error(self):
        conn = Connection(statuses=[1, 0])
        with self.assertRaisesRegex(RuntimeError, '意外'): controller(conn)[0].trigger(17, 31)

    def test_start_timeout_is_not_retried(self):
        conn = Connection(fail=('write', g.REG_CTRL))
        with self.assertRaises(TimeoutError): controller(conn)[0].trigger(17, 31)
        self.assertEqual(conn.writes.count((g.REG_CTRL, 1)), 1)

    def test_clear_requires_idle_readback(self):
        conn = Connection()
        controller(conn)[0].clear()
        self.assertEqual(conn.writes, [(g.REG_CTRL, 2)])
        conn = Connection()
        conn.hook = lambda op, addr, value: conn.mem.update({g.REG_CTRL: 1}) if op == 'read' else None
        with self.assertRaises(RuntimeError): controller(conn)[0].clear()
        self.assertEqual(conn.writes.count((g.REG_CTRL, 2)), 1)

    def test_cancel_before_start_sends_only_explicit_clear(self):
        event = threading.Event()
        event.set()
        conn = Connection()
        obj, events = worker(conn, event=event)
        self.assertEqual(conn.writes, [(g.REG_CTRL, 2)])
        self.assertFalse(event.is_set())
        self.assertEqual(events[-1], '__IDLE__')

    def test_cancel_during_configuration_prevents_start(self):
        event = threading.Event()
        conn = Connection()
        conn.hook = lambda op, addr, value: event.set() if op == 'write' and addr == g.REG_DELAY else None
        obj, events = worker(conn, event=event)
        self.assertNotIn((g.REG_CTRL, 1), conn.writes)
        self.assertEqual(conn.writes.count((g.REG_CTRL, 2)), 1)

    def test_cancel_during_polling_clears_once(self):
        event = threading.Event()
        conn = Connection(statuses=[1])
        conn.hook = lambda op, addr, value: event.set() if op == 'read' and addr == g.REG_CTRL and conn.started else None
        obj, events = worker(conn, event=event)
        self.assertEqual(conn.writes.count((g.REG_CTRL, 1)), 1)
        self.assertEqual(conn.writes.count((g.REG_CTRL, 2)), 1)
        self.assertFalse(event.is_set())

    def test_clear_failure_does_not_schedule_auto_retry(self):
        event = threading.Event(); event.set()
        conn = Connection(fail=('write', g.REG_CTRL))
        obj, events = worker(conn, event=event)
        self.assertEqual(conn.writes, [(g.REG_CTRL, 2)])
        self.assertFalse(event.is_set())
        self.assertEqual(events[-1], '__IDLE__')

    def test_close_exception_always_restores_ui_notification(self):
        obj, events = worker(Connection(close_fail=True), 'clear')
        self.assertEqual(events[-1], '__IDLE__')
        self.assertTrue(any('关闭连接异常' in s for s in events))

    def test_status_never_writes(self):
        conn = Connection(initial=2)
        worker(conn, 'status')
        self.assertEqual(conn.writes, [])

    def test_connect_failure_restores_ui_notification(self):
        obj = g.TriggerGUI.__new__(g.TriggerGUI)
        obj.events = queue.Queue(); obj.clear_requested = threading.Event()
        with patch.object(g, 'FPGAConnection', side_effect=TimeoutError('connect timeout')):
            obj.work('trigger', dict(SETTINGS))
        self.assertEqual(list(obj.events.queue)[-1], '__IDLE__')


class Stream(io.BytesIO):
    def __init__(self, value, rc=0):
        super().__init__(value); self.channel = self; self.rc = rc; self.channel_closed = False
    def recv_exit_status(self): return self.rc
    def close(self): self.channel_closed = True; super().close()


class TransportTests(unittest.TestCase):
    def test_read_format_strict_and_range_checked(self):
        for text, value in [('0x00000007\n', 7), ('00000007', 7), ('4294967295', 0xffffffff)]:
            self.assertEqual(g.parse_register(text), value)
        for text in ('', '-1', '4294967296', '0x100000000', 'error 7', '0x1\n0x2', '0x1 warning'):
            with self.assertRaises(RuntimeError): g.parse_register(text)

    def test_command_format_exit_code_and_stderr(self):
        class SSH:
            rc = 0; diagnostic = b''
            def exec_command(self, cmd, timeout):
                self.cmd = cmd; self.out = Stream(b'0x00000007', self.rc)
                return None, self.out, Stream(self.diagnostic)
        conn = g.FPGAConnection.__new__(g.FPGAConnection); conn.tool = 'busybox devmem'; conn.ssh = SSH()
        self.assertEqual(conn.read(g.REG_DELAY), 7)
        self.assertTrue(conn.ssh.out.channel_closed)
        self.assertEqual(conn.ssh.cmd, 'busybox devmem 0x40700008 32')
        conn.write(g.REG_CTRL, 1)
        self.assertEqual(conn.ssh.cmd, 'busybox devmem 0x40700000 32 0x00000001')
        conn.ssh.rc = 1
        with self.assertRaises(RuntimeError): conn.read(g.REG_CTRL)
        conn.ssh.rc = 0; conn.ssh.diagnostic = b'devmem error'
        with self.assertRaises(RuntimeError): conn.read(g.REG_CTRL)

    def test_backend_rejects_unknown_addresses_and_dangerous_values(self):
        conn = g.FPGAConnection.__new__(g.FPGAConnection)
        with patch.object(conn, '_command') as command:
            for a, v in [(g.REG_DIO0, 0), (g.REG_DELAY, 0), (g.REG_DIO0, -1),
                         (g.REG_CTRL, 3), (g.REG_CTRL, True), (g.REG_DIO1, 5), (0, 1)]:
                with self.assertRaises(ValueError): conn.write(a, v)
            command.assert_not_called()
        with self.assertRaises(ValueError): conn._command(g.BASE + 16)

    def test_conversion_boundaries_and_10000_exact_counts(self):
        for n in range(1, 10001): self.assertEqual(g.ms_to_cycles(n / 125000), n)
        self.assertEqual(g.ms_to_cycles(34359.73836), 0xffffffff)
        for ms in (0, -1, .000001, 34360, float('nan'), float('inf'), float('-inf'), 1e100):
            with self.assertRaises((ValueError, OverflowError)): g.ms_to_cycles(ms)

    def test_constructor_closes_failed_connection(self):
        class SSH:
            closed = False
            def load_system_host_keys(self): pass
            def set_missing_host_key_policy(self, policy): pass
            def connect(self, *args, **kwargs): raise TimeoutError('injected')
            def close(self): self.closed = True
        ssh = SSH()
        with patch.object(g, 'paramiko') as paramiko:
            paramiko.SSHClient.return_value = ssh
            with self.assertRaises(TimeoutError): g.FPGAConnection('offline', 'root', '')
        self.assertTrue(ssh.closed)


class UIFlowTests(unittest.TestCase):
    def test_completion_race_keeps_clear_on_same_device(self):
        obj = g.TriggerGUI.__new__(g.TriggerGUI)
        obj.events = queue.Queue(); obj.events.put('__IDLE__')
        obj.running = True; obj.active_action = 'trigger'; obj.active_settings = dict(SETTINGS)
        obj.clear_requested = threading.Event(); obj.clear_requested.set()
        obj.root = type('Root', (), {'after': lambda *args: None})()
        obj.update_buttons = lambda: None
        calls = []; obj.launch_task = lambda action, settings: calls.append((action, settings))
        obj.flush_events()
        self.assertEqual(calls, [('clear', SETTINGS)])
        self.assertFalse(obj.clear_requested.is_set())

    def test_running_clear_is_queued_without_new_thread(self):
        obj = g.TriggerGUI.__new__(g.TriggerGUI)
        obj.running = True; obj.active_action = 'trigger'; obj.clear_requested = threading.Event()
        obj.log_message = lambda *args: None; obj.update_buttons = lambda: None
        with patch.object(g.threading, 'Thread') as thread:
            obj.start_task('clear')
            thread.assert_not_called()
        self.assertTrue(obj.clear_requested.is_set())


if __name__ == '__main__':
    unittest.main(verbosity=2)
