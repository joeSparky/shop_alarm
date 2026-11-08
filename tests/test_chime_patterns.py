"""Offline execution of the chime YAML; no Home Assistant API or GPIO access.

The small runner implements only the actions used here. Restart cancellation
follows HA's documented automation mode; this is not a full HA runtime test.
"""
from pathlib import Path
from types import SimpleNamespace as NS
import re

from jinja2 import Environment, StrictUndefined
import pytest
import yaml


class PackageLoader(yaml.SafeLoader):
    pass


PackageLoader.add_constructor('!secret', lambda loader, node: loader.construct_scalar(node))
PACKAGE = yaml.load((Path(__file__).parents[1] / 'homeassistant/shop_alarm.yaml').read_text(), Loader=PackageLoader)
CHIME = next(a for a in PACKAGE['automation'] if a['id'] == 'shop_alarm_chime')


class Runner:
    def __init__(self, state='Disarmed', tenths=3):
        self.state, self.tenths = state, tenths
        self.time = self.started = 0.0
        self.commands = []
        self.pending = None
        self.due = float('inf')
        self.env = Environment(undefined=StrictUndefined)
        self.env.tests['match'] = lambda value, pattern: re.match(pattern, value)

    def render(self, value, variables):
        if not isinstance(value, str):
            return value
        states = lambda entity: self.state if entity.startswith('input_select.') else self.tenths
        states.input_select = NS(shop_alarm_state=NS(last_changed=self.started))
        return self.env.from_string(value).render(
            states=states, is_state=lambda entity, state: self.state == state,
            as_timestamp=lambda value: float(value), now=lambda: self.time,
            label_entities=lambda label: ['switch.buzzer', 'sensor.unrelated'],
            label_id=lambda label: label, labels=lambda entity: ['Chime on Open', 'Chime on Close'],
            **variables).strip()

    def truth(self, value, variables):
        if isinstance(value, list):
            return all(self.truth(v['value_template'], variables) for v in value)
        return self.render(value, variables).lower() == 'true'

    def sequence(self, actions, variables):
        for action in actions:
            if 'variables' in action:
                for key, value in action['variables'].items():
                    variables[key] = self.render(value, variables)
            elif 'choose' in action:
                for choice in action['choose']:
                    if self.truth(choice['conditions'], variables):
                        yield from self.sequence(choice['sequence'], variables)
                        break
            elif 'repeat' in action:
                repeat = action['repeat']
                while self.truth(repeat['while'], variables):
                    yield from self.sequence(repeat['sequence'], variables)
            elif 'delay' in action:
                delay = action['delay']
                yield sum(float(self.render(v, variables)) * (0.001 if k == 'milliseconds' else 1)
                          for k, v in delay.items())
            else:
                assert action['action'] in ('switch.turn_on', 'switch.turn_off')
                assert self.render(action['target']['entity_id'], variables) == "['switch.buzzer']"
                self.commands.append((self.time, action['action']))

    def resume(self):
        try:
            self.due = self.time + next(self.pending)
        except StopIteration:
            self.pending, self.due = None, float('inf')

    def fire(self, kind='alarm_state', old='off', new='on', entity='binary_sensor.door'):
        trigger = NS(id=kind, event=NS(data=NS(entity_id=entity, old_state=NS(state=old), new_state=NS(state=new))))
        variables = {'trigger': trigger}
        if not self.truth(CHIME['conditions'], variables):
            return
        assert CHIME['mode'] == 'restart'
        self.pending = self.sequence(CHIME['actions'], variables)
        self.resume()

    def advance(self, end):
        while self.due <= end:
            self.time = self.due
            self.resume()
        self.time = end

    def transition(self, state):
        self.state, self.started = state, self.time
        self.fire()


@pytest.mark.parametrize('state,slow,fast', [('Exit Delay', 1.85, .35), ('Entry Delay', .85, .10)])
@pytest.mark.parametrize('tenths', [1, 3, 30, 50])
def test_pulse_duration_and_off_intervals(state, slow, fast, tenths):
    r = Runner(state, tenths)
    r.fire()
    r.advance(29.9)
    commands = r.commands[1:]  # initial cleanup
    for on, off in zip(commands[::2], commands[1::2]):
        assert off[0] - on[0] == pytest.approx(tenths / 10)
    for off, on in zip(commands[1::2], commands[2::2]):
        assert on[0] - off[0] == pytest.approx(fast if off[0] >= 20 else slow)


@pytest.mark.parametrize('state', ['Exit Delay', 'Entry Delay'])
@pytest.mark.parametrize('destination', ['Disarmed', 'Armed Away', 'Armed Sleep', 'Fault', 'Alarm'])
@pytest.mark.parametrize('at', [.05, .4])  # interrupt ON and OFF
def test_state_exit_interrupts_immediately(state, destination, at):
    r = Runner(state)
    r.fire()
    r.advance(at)
    r.transition(destination)
    assert r.commands[-1] == (at, 'switch.turn_off')
    count = len(r.commands)
    r.advance(60)
    assert len(r.commands) == count


@pytest.mark.parametrize('state', ['Exit Delay', 'Entry Delay'])
def test_door_events_do_not_interrupt_delay(state):
    baseline, noisy = Runner(state), Runner(state)
    baseline.fire()
    noisy.fire()
    for at in [.1, .5, 19.9, 20.1, 28]:
        noisy.advance(at)
        noisy.fire('door')
        noisy.fire('door', old='on', new='off')
    baseline.advance(29)
    noisy.advance(29)
    assert noisy.commands == baseline.commands


@pytest.mark.parametrize('old,new', [('off', 'on'), ('on', 'off')])
def test_door_chimes_keep_duration_and_restart(old, new):
    r = Runner(tenths=30)
    r.fire('door', old, new)
    r.advance(1)
    r.fire('door', old, new)
    r.advance(4)
    assert r.commands[-1] == (4, 'switch.turn_off')


def test_transition_between_delays_resets_cadence():
    r = Runner('Exit Delay')
    r.fire()
    r.advance(25)
    r.transition('Entry Delay')
    assert r.commands[-2:] == [(25, 'switch.turn_off'), (25, 'switch.turn_on')]
    r.advance(26.16)
    assert r.commands[-1] == (pytest.approx(26.15), 'switch.turn_on')


def test_startup_cleans_output_and_state_trigger_ignores_attributes():
    r = Runner()
    r.fire('startup')
    assert r.commands == [(0, 'switch.turn_off')]
    trigger = next(t for t in CHIME['triggers'] if t['id'] == 'alarm_state')
    assert 'to' in trigger and trigger['to'] is None
    assert trigger['entity_id'] == 'input_select.shop_alarm_state'


def test_unrelated_events_cannot_restart_chime():
    r = Runner()
    r.fire('door', entity='switch.buzzer')
    r.fire('door', old='off', new='off')
    assert r.commands == []



def test_chime_helper_and_single_output_owner():
    # An initial value would override the saved duration on every restart.
    assert 'initial' not in PACKAGE['input_number']['shop_alarm_chime_tenths']
    assert PACKAGE['input_number']['shop_alarm_chime_tenths'] == {
        'name': 'Chime Duration', 'min': 1, 'max': 50, 'step': 1,
        'mode': 'box', 'icon': 'mdi:timer-outline',
    }
    # No second automation/script can issue a competing chime command.
    for automation in PACKAGE['automation']:
        if automation['id'] != 'shop_alarm_chime':
            assert 'Chime Output' not in str(automation)
    assert 'Chime Output' not in str(PACKAGE['script'])


@pytest.mark.parametrize('state,slow,fast', [('Exit Delay', 1.85, .35), ('Entry Delay', .85, .10)])
def test_exact_twenty_second_boundary(state, slow, fast):
    r = Runner(state)
    template = CHIME['actions'][2]['choose'][0]['sequence'][0]['repeat']['sequence'][3]['delay']['seconds']
    for elapsed, expected in [(19.999, slow), (20, fast), (29.999, fast)]:
        r.time = elapsed
        assert float(r.render(template, {'delay_state': state, 'delay_started': 0})) == expected


def test_actual_state_controls_end_not_thirty_second_timer():
    r = Runner('Entry Delay')
    r.fire()
    r.advance(32)
    assert r.pending is not None
    r.transition('Alarm')
    assert r.pending is None
