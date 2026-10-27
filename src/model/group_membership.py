"""Group code kept separate from devices and radios"""

from message import MessageType


def receive_control(device, message):
    data = message.get_encapsulated_msg()
    group_id = data["group_id"]  # Round number and leader ID
    origin = message.get_original_src()
    if message.kind == MessageType.GROUP_REQUEST:
        if origin != group_id[1] or origin not in device.landmarks:
            return
        if device.group_id is None or group_id > device.group_id:
            device.group_id = group_id
            device.group_members.clear()
            device.survey_routes.clear()
            device.group_announced = False
        return
    if group_id != device.group_id:
        return  # Ignore messages from a different group
    if message.kind == MessageType.LANDMARK_SURVEY and device.is_landmark and origin in device.landmarks:
        route = message.get_msg_route()
        if route[-1] != device.ID:
            route.append(device.ID)
        # Keep only the first route from each landmark
        device.survey_routes.setdefault(origin, tuple(route))
    elif message.kind == MessageType.LANDMARK_REPORT and device.ID == group_id[1] and origin in device.landmarks:
        device.group_members.update(data["members"])
    elif message.kind == MessageType.GROUP_ANNOUNCE and origin == group_id[1]:
        device.group_members = set(data["members"])
        device.group_announced = True
    elif message.kind == MessageType.GROUP_JOIN and device.group_announced:
        device.group_members.add(origin)


def form_group(env, leader_id=None, survey_ttl=3):
    """Request a group then collect routes and add any missing devices"""
    if not env.landmarks:
        raise ValueError("Configure at least one landmark")
    if survey_ttl < 1:
        raise ValueError("Survey TTL must be positive")
    leader_id = min(env.landmarks) if leader_id is None else leader_id
    if leader_id not in env.landmarks or leader_id not in env._devices_by_id:
        raise ValueError("Choose a registered landmark as leader")
    env.drain()
    env.group_round += 1
    group_id = (env.group_round, leader_id)
    leader = env._devices_by_id[leader_id]
    # The longest route without loops has one fewer hop than the number of devices
    ttl = max(1, len(env.layout.positions) - 1)
    leader.send_control(MessageType.GROUP_REQUEST, ttl, group_id=group_id)
    env.drain()

    # Give landmarks turns in ID order and skip quiet ones
    landmarks = [env._devices_by_id[ID] for ID in sorted(env.landmarks)
                 if ID in env._devices_by_id and env._devices_by_id[ID].group_id == group_id]
    for device in landmarks:
        device.send_control(MessageType.LANDMARK_SURVEY, survey_ttl)
        env.drain()
    for device in landmarks:
        observed = {device.ID}
        for route in device.survey_routes.values():
            observed.update(route)
        device.send_control(MessageType.LANDMARK_REPORT, ttl,
                            destination=leader_id, members=sorted(observed))
        env.drain()

    # Build the first member list only from received reports
    leader.send_control(MessageType.GROUP_ANNOUNCE, ttl,
                        members=sorted(leader.group_members))
    env.drain()
    for device in sorted(env.device_list, key=lambda d: d.ID):
        if device.group_id == group_id and device.group_announced and device.ID not in device.group_members:
            device.send_control(MessageType.GROUP_JOIN, ttl)
            env.drain()

    members = frozenset(leader.group_members)
    if any(d.group_id != group_id or not d.group_announced or
           d.group_members != members or d.ID not in members for d in env.device_list):
        raise RuntimeError("Group did not converge: check connectivity, channels, and delivery")
    return members
