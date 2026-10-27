from device import Device
from grid import GridLayout
from group_membership import form_group

class SimEnvironment():
    def __init__(self, positions, verbose=False, landmarks=None):
        self.layout = GridLayout(positions)
        # Share which devices are landmarks and let messages build the member list
        self.landmarks = self.layout.landmarks() if landmarks is None else frozenset(landmarks)
        if not self.landmarks <= positions.keys():
            raise ValueError("Landmarks must have configured positions")
        self.group_round = 0
        self.device_list = []
        self._devices_by_id = {}
        self.verbose = verbose
        # Store waiting messages for each receiving device
        self.message_FIFOs = {}

        if verbose:
            print("Grid layout:")
            self.layout.print_grid()
            print()

    def did_receive_message(self, message_tag: tuple[int, int]):
        for dv in self.device_list:
            if not message_tag in dv.received_messages:
                return False
        else:
            return True

    def add_device(self, d):
        if d.ID not in self.layout.positions:
            raise KeyError(d.ID)
        if d.ID in self._devices_by_id:
            raise ValueError("Device ID already registered")
        self.device_list.append(d)
        self._devices_by_id[d.ID] = d
        d.landmarks = self.landmarks
        self.message_FIFOs[d.ID] = []
        return d

    def outgoing_message(self, msg_list, channel_ID):
        # Add each message to the waiting list of every neighbor of its sender
        reached = set()
        for msg in msg_list:
            for n in self.get_neighbors(msg.src):
                self.message_FIFOs[n.ID].append((msg, channel_ID))
                reached.add(n.ID)

        if self.verbose:
            real_msgs = [m for m in msg_list if not m.is_NULL_message()]
            if not real_msgs:
                print(f"Channel {channel_ID}: None valid")
                raise Exception("Atomic Broadcast failed to guarantee message sending.")
                
            src, dst = real_msgs[0].src, real_msgs[0].dst
            if dst == -1:
                print(f"Channel {channel_ID}: src={src} (broadcast), reached={sorted(reached)}")
            else:
                print(f"Channel {channel_ID}: src={src} dst={dst}")

    def get_neighbors(self, source_ID):
        if source_ID is None:
            return []
        return [self._devices_by_id[ID] for ID in self.layout.neighbors(source_ID)
                if ID in self._devices_by_id]
        
    def simulate(self, start_idx=0):
        # our funny starting point
        self.device_list[start_idx].work()
        self.drain()

    def drain(self):
        # Finish waiting messages before starting the next group step
        step = 0

        # the actual simulation
        # Take a step while any device has messages waiting
        while any(self.message_FIFOs.values()):
            # Copy the waiting lists so new messages wait until the next step
            round_FIFOs = self.message_FIFOs
            self.message_FIFOs = {ID: [] for ID in round_FIFOs}

            step += 1

            if self.verbose:
                print(f"Simulation Step {step}")

            for ID, FIFO in round_FIFOs.items():
                # Group messages by channel and sender to find collisions
                channel_bursts = {}
                for i, (msg, channel_ID) in enumerate(FIFO):
                    channel_bursts.setdefault(channel_ID, {}).setdefault(msg.src, []).append(i)

                # Different senders on the same channel cause collisions
                # Drop their attempts together until only one sender has attempts left

                # just loop through and tag messages as dropped or not
                dropped = [False] * len(FIFO)
                for bursts in channel_bursts.values():
                    remaining = list(bursts.values())
                    while len(remaining) > 1:
                        for b in remaining:
                            dropped[b.pop(0)] = True
                        remaining = [b for b in remaining if b]

                if self.verbose:
                    # keep track of all that collided
                    drops = {}
                    for (msg, channel_ID), is_dropped in zip(FIFO, dropped):
                        if is_dropped:
                            by_src = drops.setdefault(channel_ID, {})
                            by_src[msg.src] = by_src.get(msg.src, 0) + 1
                    for channel_ID, by_src in drops.items():
                        summary = ", ".join(f"{n} from src {src}" for src, n in sorted(by_src.items()))
                        print(f"Collision at device {ID}, channel {channel_ID}: dropped {summary}")

                for (msg, _), is_dropped in zip(FIFO, dropped):
                    if not is_dropped:
                        self._devices_by_id[ID].sim_receive_broadcast(msg)

        for d in self.device_list:
            d.AB_protocol.new_event()

    def form_group(self, leader_id=None, survey_ttl=3):
        # Run the group steps separately from the message loop
        return form_group(self, leader_id, survey_ttl)

def sim_device_positions(n=5):
    # Future layouts could use diagonal lines or spread from the center
    #
    # Compare layouts to find faster ways to send messages
    # Use the grid size so larger grids do not reuse device IDs
    return {y * n + x: (x, y) for y in range(n) for x in range(n)}

# L . . . L
# . . . . .
# . . L . .
# . . . . .
# L . . . L
#The device(s) need to know if they are a landmark node
#       + all other landmark nodes (or just nearby ones?)
#
#       Do the protocol
#
#       Message TTL property/field + handling
#
#       Introduce special message types:
#           New group request
#           Landmark-landmark node survey message (just to get routes)
#           Announce nascent group
#           Add yourself to group cus you got left out, loser
#       
#           Normal/default/general broadcast

if __name__ == "__main__":
    # The old four by four example used IDs zero through fifteen in row order
    # This five by five grid puts landmarks at every third row and column
    positions = sim_device_positions()
    test_env = SimEnvironment(positions, verbose=True)
    for device_id in positions:
        channel = test_env.layout.channel(device_id)
        test_env.add_device(Device(device_ID=device_id, sim_tx_callback=test_env.outgoing_message, assigned_channel=channel))

    # Run the group example here and keep the old normal message example available
    print("Landmarks:", sorted(test_env.landmarks))
    print("Group members:", sorted(test_env.form_group()))

    #NOTE: Now we can check device.received_messages to check for correctness
    #      If an initated message isn't in there when the sim settles, it was lost
