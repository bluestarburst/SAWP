import io
import unittest
from contextlib import redirect_stdout

from device import Device
from message import Message, MessageType
from sim_env import SimEnvironment, sim_device_positions


def make_environment(positions, missing=(), landmarks=None, traffic=None):
    env = SimEnvironment(positions, landmarks=landmarks)

    def transmit(messages, channel):
        if traffic is not None:
            traffic.extend(message for message in messages if not message.is_NULL_message())
        env.outgoing_message(messages, channel)

    for ID in reversed(positions):
        if ID not in missing:
            device = Device(ID, transmit, env.layout.channel(ID))
            # Lose the first of the two attempts each time
            device.AB_protocol.f_prob = 1
            env.add_device(device)
    return env


class MembershipTests(unittest.TestCase):
    def test_grid_generator_and_corner_center_landmarks(self):
        env = make_environment(sim_device_positions(5))
        self.assertEqual(len(env.layout.positions), 25)
        self.assertEqual(env.landmarks, {0, 4, 12, 20, 24})

        for device in env.device_list:
            self.assertEqual(device.is_landmark, device.ID in env.landmarks)
            self.assertEqual(device.landmarks, env.landmarks)

        positions = sim_device_positions(5)
        shifted = {ID: (x - 7, y - 9) for ID, (x, y) in reversed(list(positions.items()))}
        gaps = {ID: cell for ID, cell in positions.items() if ID not in {0, 12}}
        cases = [(shifted, {0, 4, 12, 20, 24}),
                 (gaps, {1, 4, 7, 20, 24}),
                 (sim_device_positions(4), {0, 3, 5, 12, 15}),
                 ({99: (-2, -3)}, {99}),
                 ({}, set())]
        for layout, expected in cases:
            with self.subTest(positions=layout):
                self.assertEqual(make_environment(layout).landmarks, expected)

    def test_groups_converge_from_delivered_routes_and_missing_node_joins(self):
        cells = [(x, y) for y in range(-3, 4) for x in range(-3, 4)
                 if (x, y) not in {(-1, 0), (0, 0), (1, 1)}]
        cases = [
            (sim_device_positions(4), (), None, None),
            (sim_device_positions(5), (), {0, 12}, None),
            (sim_device_positions(5), {0, 6, 12, 24}, None, 4),
            ({100 + i * 7: cell for i, cell in enumerate(cells)}, (), None, None),
        ]
        for positions, missing, landmarks, leader in cases:
            with self.subTest(size=len(positions), missing=missing, landmarks=landmarks):
                traffic = []
                env = make_environment(positions, missing, landmarks, traffic)
                # One hop leaves most devices out of the first surveys
                expected = set(positions) - set(missing)
                self.assertEqual(env.form_group(leader, survey_ttl=1), expected)
                
                for device in env.device_list:
                    self.assertEqual(device.group_members, expected)
                    self.assertTrue(device.group_announced)
                    for origin, route in device.survey_routes.items():
                        self.assertEqual(route[0], origin)
                        self.assertEqual(route[-1], device.ID)
                        self.assertLessEqual(len(route), 2)
                        self.assertTrue(set(route) <= expected)
                kinds = {message.kind for message in traffic}
                self.assertEqual(kinds, set(MessageType) - {MessageType.NORMAL})
                self.assertFalse(any(env.message_FIFOs.values()))

    def test_default_surveys_record_real_landmark_to_landmark_paths(self):
        env = make_environment(sim_device_positions(5))
        self.assertEqual(env.form_group(), set(range(25)))
        for device in env.device_list:
            if not device.is_landmark:
                continue
            self.assertTrue(set(device.survey_routes) - {device.ID})
            for origin, route in device.survey_routes.items():
                self.assertEqual(route[0], origin)
                self.assertEqual(route[-1], device.ID)
                self.assertLessEqual(len(route), 4)
                self.assertEqual(len(route), len(set(route)))
                for source, target in zip(route, route[1:]):
                    self.assertIn(target, env.layout.neighbors(source))

    def test_ttl_and_duplicate_suppression_allow_multiple_messages(self):
        traffic = []
        env = make_environment({i: (i, 0) for i in range(4)}, traffic=traffic)
        sender = next(d for d in env.device_list if d.ID == 0)
        sender.send_message(Message(0, -1, 0, "one hop", ttl=1))
        sender.send_message(Message(0, -1, 0, "three hops", ttl=3))

        with redirect_stdout(io.StringIO()):
            env.drain()
        for device in env.device_list:
            self.assertEqual((0, 0) in device.received_messages, device.ID <= 1)
            self.assertEqual(device.received_messages[(0, 1)], "three hops")

        # Each device sends one successful copy of each message it passes on
        self.assertEqual(sorted((m.src, m.msg_ID, m.ttl) for m in traffic),
                         [(0, 0, 1), (0, 1, 3), (1, 1, 2), (2, 1, 1)])
        sender.send_message(Message(0, -1, 0, "expired", ttl=0))
        env.drain()
        self.assertEqual(len(traffic), 4)

    def test_directed_message_stops_at_destination(self):
        env = make_environment({i: (i, 0) for i in range(4)})
        sender = next(d for d in env.device_list if d.ID == 0)
        sender.send_message(Message(0, 2, 0, "directed", ttl=3))

        with redirect_stdout(io.StringIO()):
            env.drain()

        recipients = {d.ID for d in env.device_list if (0, 0) in d.received_messages}
        self.assertEqual(recipients, {0, 2})

    def test_new_round_discards_old_views_and_ignores_delayed_announcements(self):
        env = make_environment(sim_device_positions(4), missing={15})
        self.assertEqual(env.form_group(), set(range(15)))
        leader = next(d for d in env.device_list if d.ID == 0)
        old_group = leader.group_id
        late = Device(15, env.outgoing_message, env.layout.channel(15))
        env.add_device(late)

        for device in env.device_list:
            device.group_members.add(999)

        self.assertEqual(env.form_group(), set(range(16)))
        leader.send_control(MessageType.GROUP_ANNOUNCE, 15, group_id=old_group, members=[999])
        env.drain()

        for device in env.device_list:
            self.assertEqual(device.group_members, set(range(16)))
            self.assertGreater(device.group_id, old_group)

    def test_partition_and_absent_leader_do_not_claim_convergence(self):
        env = make_environment({0: (0, 0), 9: (10, 10)})

        with self.assertRaisesRegex(RuntimeError, "did not converge"):
            env.form_group()

        isolated = next(d for d in env.device_list if d.ID == 9)
        self.assertFalse(isolated.group_announced)
        self.assertEqual(isolated.group_members, set())
        env = make_environment(sim_device_positions(4), missing={0})

        with self.assertRaisesRegex(ValueError, "registered landmark"):
            env.form_group()

        self.assertEqual(env.form_group(leader_id=3), set(range(1, 16)))

    def test_colliding_channels_do_not_claim_convergence(self):
        env = make_environment(sim_device_positions(5))
        for device in env.device_list:
            device.AB_protocol.channel_ID = 0

        with self.assertRaisesRegex(RuntimeError, "did not converge"):
            env.form_group()

        self.assertTrue(any(not d.group_announced for d in env.device_list))


if __name__ == "__main__":
    unittest.main()
