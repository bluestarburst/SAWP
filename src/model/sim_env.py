from device import Device
from grid import GridLayout
from config import GRID_SIZE

class SimEnvironment():
    def __init__(self, positions, verbose=False, landmarks=None):
        self.layout = GridLayout(positions)
        # Share which devices are landmarks and let messages build the member list
        self.landmarks = self.layout.landmarks() if landmarks is None else frozenset(landmarks)
        if not self.landmarks <= positions.keys():
            raise ValueError("Landmarks must have configured positions")
        self.group_round = 0
        self.device_list: list[Device] = []
        self._devices_by_id = {}
        self.verbose = verbose
        # Store waiting messages for each receiving device
        self.message_FIFOs = {}

        if verbose:
            print("Grid layout:")
            self.layout.print_grid()
            print()

    def update_device_on_sim_step(self, step):
        #for d in devices, call d.update or smthn
        for d in self.device_list:
            d.sim_step_changed(step)

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
        

    def advance_simulation_message_broadcasts(self):

        # the actual simulation
        # Take a step while any device has messages waiting

        #NOTE: We retrofitted this to take one simulation step at a time
        #while any(self.message_FIFOs.values()):

        # Copy the waiting lists so new messages wait until the next step
        round_FIFOs = self.message_FIFOs
        self.message_FIFOs = {ID: [] for ID in round_FIFOs}

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


    # def form_group(self, leader_id=None, survey_ttl=3):
    #     # Run the group steps separately from the message loop
    #     return form_group(self, leader_id, survey_ttl)

    def run(self, sim_bound=100):

        current_sim_step = 0

        # tell someone to do something
        self.device_list[0].Group_Membership.form_group()

        while current_sim_step < sim_bound:
            self.advance_simulation_message_broadcasts()
            self.update_device_on_sim_step(current_sim_step)
            current_sim_step += 1
            # print("\t", current_sim_step)

        # check if the thing got done;;;
        for d in self.device_list:
            if d.Group_Membership.group_valid_flag:
                print(f"{str(d)} in Group")

        print("Simulation Done !OwO!")

        

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
    # This five by five grid puts landmarks at the four corners and the center
    positions = sim_device_positions(GRID_SIZE)
    test_env = SimEnvironment(positions, verbose=True)
    for device_id in positions:
        channel = test_env.layout.channel(device_id)
        # get very center (offset -2 mod 4)

        recovered_x = positions[device_id][0]
        recovered_y = positions[device_id][1]

        is_landmark = (recovered_x % 4 == 0 and recovered_y % 4 == 0) or (recovered_x % 4 == 2 and recovered_y % 4 == 2)
        is_center_landmark = (recovered_x % 4 == 2) and (recovered_y % 4 == 2)
        print(f"Device {device_id}: ({recovered_x}, {recovered_y}) - Landmark: {is_landmark}, Center: {is_center_landmark}")
        test_env.add_device(Device(device_ID=device_id, sim_tx_callback=test_env.outgoing_message, assigned_channel=channel, is_center_landmark=is_center_landmark, is_landmark=is_landmark))

    # Run the group example here and keep the old normal message example available
    print("Landmarks:", sorted(test_env.landmarks))
    # print("Group members:", sorted(test_env.form_group()))
    
    test_env.run()

    #NOTE: Now we can check device.received_messages to check for correctness
    #      If an initated message isn't in there when the sim settles, it was lost
