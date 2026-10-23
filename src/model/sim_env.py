from device import Device
from grid import GridLayout

class SimEnvironment():
    def __init__(self, positions, verbose=False):
        self.layout = GridLayout(positions)
        self.device_list = []
        self._devices_by_id = {}
        self.verbose = verbose
        # Incoming messages waiting to be delivered, keyed by receiving device ID
        self.message_FIFOs = {}

        if verbose:
            print("Grid layout:")
            self.layout.print_grid()
            print()

    def add_device(self, d):
        if d.ID not in self.layout.positions:
            raise KeyError(d.ID)
        if d.ID in self._devices_by_id:
            raise ValueError("Device ID already registered")
        self.device_list.append(d)
        self._devices_by_id[d.ID] = d
        self.message_FIFOs[d.ID] = []
        return d

    def outgoing_message(self, msg_list, channel_ID):
        # Queue each message on the FIFO of every neighbor of its sender
        reached = set()
        for msg in msg_list:
            for n in self.get_neighbors(msg.src):
                self.message_FIFOs[n.ID].append((msg, channel_ID))
                reached.add(n.ID)

        if self.verbose:
            real_msgs = [m for m in msg_list if not m.is_NULL_message()]
            if not real_msgs:
                print(f"Channel {channel_ID}: None valid")
                return
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

        step = 0

        # the actual simulation
        #   If any device has messages to recieve, we take a simulation step
        while any(self.message_FIFOs.values()):
            # we snapshot the message queues so rebroadcasts don't appear in the same sim step
            round_FIFOs = self.message_FIFOs
            self.message_FIFOs = {ID: [] for ID in round_FIFOs}

            step += 1

            if self.verbose:
                print(f"Simulation Step {step}")

            for ID, FIFO in round_FIFOs.items():
                # We now group messages by channel and then source ot find any collisions
                channel_bursts = {}
                for i, (msg, channel_ID) in enumerate(FIFO):
                    channel_bursts.setdefault(channel_ID, {}).setdefault(msg.src, []).append(i)

                # Messages from different sources on the same channel collide and are dropped
                # as groups since we can have n-way collisions.
                # We do this till there is only one source per channel-message group

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

def sim_device_positions(n=4):
    #TODO:  Perhaps we try out different configurations:
    #       Like diagonals ///
    #       Or radiating from center
    #
    # This would be to reduce the bound on how long a AB takes--if it does
    return {y * 4 + x: (x, y) for y in range(4) for x in range(4)}

if __name__ == "__main__":
    # IDs 0-15, left to right across each row.
    positions = sim_device_positions()
    test_env = SimEnvironment(positions, verbose=True)
    for device_id in positions:
        test_env.add_device(Device(device_ID=device_id, sim_tx_callback=test_env.outgoing_message))

    test_env.simulate()

    #NOTE: Now we can check device.received_messages to check for correctness
    #      If an initated message isn't in there when the sim settles, it was lost
