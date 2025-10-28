
from functools import reduce
from diff_match_patch import diff_match_patch
_dmp = diff_match_patch()

def parse_svd(svd_file : str) -> dict:
    from cmsis_svd import SVDParser
    parser = SVDParser.for_xml_file(svd_file)
    device = parser.get_device().to_dict()
    return device

def group_peripherals(device):
    """
    Parse the SVD device (result of parse_svd()) and find all peripherals that have a matching group.
    Returns a list with, for each of these groups, a dictionary with the following properties:
     * name: the group name of all the peripherals in the group
     * registers: the registers of all the peripherals in the group
     * peripherals: a list of all peripherals belonging to the group, excluding their registers
    """
    groups = {}
    for peripheral in device['peripherals']:
        # Create a group with common registers and/or add peripheral to its corresponding group
        if peripheral['group_name'] not in groups:
            group = {
                'name': peripheral['group_name'],
                'registers': peripheral['registers'],
                'description': peripheral['description'],
                'peripherals': [peripheral],
            }
            groups[peripheral['group_name']] = group
        else:
            groups[peripheral['group_name']]['peripherals'].append(peripheral)
        # Delete the grouped items from this peripheral, only the common defintion should be used
        del peripheral['description']
        del peripheral['registers']
    return groups

def simplify_registers(groups):
    """
    Recursively remove 'meta_clusters' which are then replaced by their internal registers
    This simplifies the register strucutre
    """
    for group in groups.values():
        simplify_registers_list(group['registers'])

def clean_registers(groups):
    """
    Perform some cleanup operations on the register groups resulting from group_peripherals():
     - All registers are sorted by their address offset
     - All fields in the registers are sorted by their bit offset
     - All duplicate whitespace characters from descriptions are stripped and/or replaced by spaces
    """
    for group in groups.values():
        group['description'] = clean_description(group['description'])
        clean_registers_list(group['registers'])

def cluster_registers(groups, ignore_cluster_regex=''):
    """
    The input of this function is the result of group_peripherals().
    If the SVD file contains clusters, then these require to be
    For each group, try and find the largest run in registers that is repeating, and replace it by a cluster.
    A run of registers is any amount of subsequent registers.
    The run of x registers is repeating if the next x registers:
      - Have equal 'pre' string (group name) for all registers in the cluster
      - Have equal 'post' string (register name) for all registers between runs
      - Differ in address by a fixed increment between runs for each register in the run
      - May differ by description, the difference in description is returned as overlapping and non-overlapping parts
      - Are otherwise equal

    The ignore cluster regex argument can optionally be used to indicate which identified clusters should be ignored.
    By default all possible clusters are used.
    """
    import re
    cluster_ignore = re.compile(ignore_cluster_regex)
    for group in groups.values():
        cluster_registers_list(group['name'], group['registers'], cluster_ignore)

def ungroup_peripherals(device, groups):
    """
    Perform the inverse operation of 'group_peripherals()'
    """
    peripherals = []
    for group in groups.values():
        for peripheral in group['peripherals']:
            peripheral['registers'] = group['registers']
            peripheral['description'] = group['description']
            peripherals.append(peripheral)

    device['peripherals'] = peripherals

def simplify_registers_list(registers):
    """
    Performs the removal operations as defined in simplify_registers_list() based on a single list of registers
    """
    for idx, register in enumerate(registers):
        # All registers in can contain a 'meta_cluster', recursively replace the meta clusters by their registers
        if 'meta_cluster' in register:
            register = register['meta_cluster']
            register['registers'] = simplify_registers_list(register['registers'])
            registers[idx] = register

    return registers

def clean_registers_list(registers):
    """
    Performs the cleanup operations as defined in clean_registers() based on a single list of registers
    """
    # Strip newlines and duplicate whitespace characters from register and field descriptions
    for register in registers:
        register['fields'].sort(key=lambda x: x['bit_offset'])
        if register['description']:
            register['description'] = ' '.join(list(filter(len, register['description'].split())))
        for field in register['fields']:
            field['description'] = ' '.join(list(filter(len, field['description'].split())))

    registers.sort(key=lambda x: x['address_offset'])

def clean_description(description):
    return ' '.join(list(filter(len, description.split())))

def cluster_registers_list(print_name, registers, cluster_ignore):
    """
    Performs the cluster operations as defined in cluster_registers() based on a single list of registers
    """
    # Find all existing clusters within this list of registers, and recursively cluster, which reduces the search load
    for register in registers:
        if 'registers' in register:
            cluster_registers_list(f'{print_name}.{register['name']}', register['registers'], cluster_ignore)

    # Try to find new clusters
    clusters = []
    run_offset = 0
    while run_offset < len(registers):
        run_properties = find_run(registers, run_offset)
        if run_properties is not None:
            clusters.append(run_properties)
            run_offset = run_offset + run_properties['length'] * run_properties['repeat']
        else:
            run_offset = run_offset + 1

    cluster_names = [cluster['name'] for cluster in clusters]

    # Replace all registers in clusters by their cluster component
    # In reverse order of offset, to maintain correct offset values even when registers are removed
    for cluster in sorted(clusters, reverse=True, key=lambda x: x['offset']):
        # Ignore matching clusters
        if cluster_ignore.fullmatch(f'{print_name}.{cluster['name']}'):
            print(f'Rejecting ignored cluster in {print_name}.{cluster['name']}')
            continue
        # If multiple cluster items have duplicate cluster name, then they are invalid as they can't be addressed (and likely have overlapping registers as well)
        if cluster_names.count(cluster['name']) != 1:
            print(f'Rejecting cluster in {print_name} with duplicate name {cluster['name']} starting at register {registers[cluster['offset']]['name']}')
            continue
        # If the cluster has registers with equal name, then it is invalid as no unique cluster registers can be generated
        if len(cluster['post']) > 1 and all(post == cluster['post'][0] for post in cluster['post']):
            print(f'Rejecting cluster in {print_name} with non-unique registers {cluster['post']} starting at register {registers[cluster['offset']]['name']} ')
        # Extract the cluster registers
        cluster_before = registers[0:cluster['offset']]
        cluster_regs = registers[cluster['offset']:cluster['offset']+cluster['length']*cluster['repeat']]
        cluster_after = registers[cluster['offset']+cluster['length']*cluster['repeat']:]
        # Create cluster with properties
        cluster_address_offset = cluster_regs[0]['address_offset']
        # The description of each register in the cluster is a combination of all descriptions in that repeat. Take all common parts, and place the differentiating parts between [] divided by |.
        cluster_contents = []
        for idx in range(0, cluster['length']):
            cluster_description_overlap = find_string_overlap([x['description'] for x in cluster_regs[idx::cluster['length']] if x['description']])
            cluster_description = ""
            for part in range(0, len(cluster_description_overlap)):
                if part % 2 == 0:
                    cluster_description += cluster_description_overlap[part]
                else:
                    cluster_description += '[' + '|'.join(cluster_description_overlap[part]) + ']'
            cluster_contents.append(
                cluster_regs[idx] |
                {
                    'name': cluster['post'][idx],
                    'description': cluster_description,
                    'address_offset': cluster_regs[idx]['address_offset'] - cluster_address_offset,
                }
            )
        cluster_name = cluster['name'] + '[%s]'
        print(f'Found valid cluster {print_name}.{cluster['name']} of length {cluster['length']}, repeat {cluster['repeat']}, with increment {hex(cluster['increment'])} and index {cluster['index']}, starting at register {registers[cluster['offset']]['name']}')
        # Recursively cluster the registers in this cluster as well
        cluster_registers_list(f'{print_name}.{cluster_name}', cluster_contents, cluster_ignore)
        cluster_item = {
            'dim': cluster['repeat'],
            'dim_increment': cluster['increment'],
            'dim_index': cluster['index'],
            'name': cluster_name,
            'description': f'Cluster {print_name}.{cluster_name} generated by svd2cpp, array index by {cluster['index']}',
            'address_offset': cluster_address_offset,
            'size': cluster['repeat'] * cluster['increment'] * 8,
            'registers': cluster_contents
        }
        # Replace registers by cluster
        registers[:] = cluster_before + [cluster_item] + cluster_after

def find_run(registers, run_offset):
    # The run properties are:
    #  run_name: the starting portion of the name for all registers in the run
    #  run_index: the index of the run (i.e., usually a range of digits starting at 0 or 1)
    #  run_jump: the register jump for each register in the run, between each repeat of the run
    #  run_length: the amount of registers in the run before repetition starts
    #  run_repeat: the amount of times the run repeats (each time with increasing index)
    # Start trying with the longest possible run length, which is half the remaining registers (i.e., all the remaining registers is split in a run of two)
    # Start trying with the highest possible run repeat, which is the remaining registers divided by the run length (i.e., the run repeats as many times as possible), and at least 2 times
    for run_length in range((len(registers) - run_offset) // 2, 0, -1):
        for run_repeat in range((len(registers) - run_offset) // run_length, 1, -1):
            run_regs = registers[run_offset:(run_offset + run_length * run_repeat)]

            # A run of registers consists of a run name, followed by a digit
            # Make sure all registers have a matching string part up to a digit that may resemble the run name
            # Note that the run name may contain a digit as well, so this function does not actually calculate the run name, but is just to prevent a more expensive calculation
            start_string = None
            for i, c in enumerate(run_regs[0]['name']):
                if c.isdigit():
                    # This is the first digit, we have a start match if all registers in the run start with this same string
                    start_string = run_regs[0]['name'][0:i]
                    for reg in run_regs:
                        if not reg['name'].startswith(start_string):
                            start_string = None
                            break
                    break
            if not start_string:
                continue

            # Check if each of the registers in the run repeats 'run_repeat' amount of times and the jump for each repeat is the same
            # Additionally, the 'index' used must be equal for all registers
            run_name = None
            run_repeat_index = None
            run_repeat_post = [None] * run_length
            run_jump = None
            for run_idx in range(0, run_length):
                run_repeat_regs = [None] * run_repeat
                for repeat_idx in range(0, run_repeat):
                    run_repeat_regs[repeat_idx] = registers[run_offset + repeat_idx * run_length + run_idx]
                run_props = check_registers_repeat(run_repeat_regs, run_name, run_repeat_index, run_repeat_post[run_idx], run_jump)
                if run_props is None:
                    # These registers are not part of a run
                    break
                run_name, run_repeat_index, run_repeat_post[run_idx], run_jump = run_props
            if (run_length == 0) or (run_props is None):
                continue

            # Make sure run_name does not yet exist in this peripheral, otherwise a name clash would occur
            if run_name in [x['name'] for x in registers]:
                print(f'Potential run {run_name} clashes with register name, skipping')
                continue

            # We found a valid run!
            return {'offset': run_offset, 'name': run_name, 'index': run_repeat_index, 'increment': run_jump, 'length': run_length, 'repeat': run_repeat, 'post': run_repeat_post}
    return None

def check_registers_repeat(run_repeat_regs, run_name, repeat_index, repeat_post, run_jump):
    """
    Check if a list of registers is similar, they are if they meet the conditions for clustering (see cluster_registers)
    """
    if len(run_repeat_regs) < 2:
        raise ValueError('At least two registers must be provided')
    overlap = find_string_overlap([reg['name'] for reg in run_repeat_regs])
    try:
        # At least one part and at most two parts must be overlapping, and one part differentiating, and the first overlapping part must match the run name
        name = overlap[0]
        if (len(overlap) != 2) and (len(overlap) != 3) or ((run_name != None) and (name != run_name)):
            return None
        # The differentiating 'index' part must be equal for each repeat
        index = overlap[1]
        if ((repeat_index is not None) and (repeat_index != index)): # or not reduce(lambda x, y: x if ((x != False) and (x == y)) else False, overlap[1]):
            return None
        # The optional second overlap, the register name, must be equal for each repeat
        if len(overlap) < 3:
            post = None
        else:
            post = overlap[2]
            if (repeat_post is not None) and (repeat_post != post):
                return None
        # The jump in register address must be equal for all registers
        jump = run_repeat_regs[1]['address_offset'] - run_repeat_regs[0]['address_offset']
        if ((run_jump is not None) and (jump != run_jump)) or not reduce(lambda x, y: y if ((x != False) and ((y['address_offset'] - x['address_offset']) == jump)) else False, run_repeat_regs):
            return None
        # All sets of registers must be similar
        if not reduce(lambda x, y: y if ((x != False) and check_items_similar(x, y)) else False, run_repeat_regs):
            return None
        # These registers match in run, return the properties
        return (name, index, post, jump)
    except ValueError:
        # Was unable to convert overlap to an integer, no valid run
        pass
    return None

def check_items_similar(items1, items2, loose = True):
    """
    Check if the items of two dicts are similar, which is the case if they differ only in name, description, and address
    The check is recursive, and applied to the registers in a peripheral and the fields in a register as well
    """
    if items1.keys() != items2.keys():
        return False # Keys don't match, they are not similar
    for name, value in items1.items():
        if name == 'name':
            if loose: # Value may differ, ignore
                continue
            else: # Value must match except for an integer
                overlap = find_string_overlap([items1['name'], items2['name']])
                if (len(overlap) > 3) or ((len(overlap) != 1) and not (overlap[1][0].isdigit() and overlap[1][1].isdigit())):
                    return False # Difference is more than a digit, no match
                continue
        elif name in ['display_name', 'description', 'address_offset', 'enumerated_values', 'header_struct_name']:
            continue # Value may differ, ignore
        elif name in ['name', 'size', 'access', 'protection', 'reset_value', 'reset_mask', 'dim', 'dim_increment', 'dim_index', 'dim_name', 'dim_array_index', 'alternate_group', 'alternate_register', 'data_type', 'modified_write_values', 'write_constraint', 'read_action', 'derived_from', 'bit_offset', 'bit_width', 'lsb', 'msb', 'bit_range', 'alternate_cluster']:
            if value != items2[name]:
                # print(f'Found mismatch for key {name}')
                return False # Values don't match, they are not similar
        elif name in ['registers', 'fields', 'clusters']:
            if not value and not items2[name]:
                continue  # Two empty lists, no need to check further
            if len(value) != len(items2[name]):
                # print(f'Found mismatching length for key {name}')
                return False # Items have different lengths, never similar
            for subidx, subval in enumerate(value):
                if not check_items_similar(subval, items2[name][subidx], loose=(name != 'fields')):
                    # print(f'Found mismatch for key {name} at index {subidx}')
                    return False # Items are not recursively similar, then these are not similar
            # TODO: if the fields of the second item are all contained in the fields of the first, then it is OK?
            # TODO: Check if for all fields in the second items, a similar field is contained in the first
            # for _, subval2 in enumerate(items2[name]):
            #     for _, subval1 in enumerate(value):
            #         if check_items_similar(subval1, subval2, loose=True):
            #             break
            #     else:
            #         # print(f'Found mismatch for key {name}')
            #         return False # Items are not recursively similar, then these are not similar
        else:
            raise Exception(f'Unknown key in comparison {name}')
    return True

def find_string_overlap(input : list[str], start_only = False):
    """
    Finds the overlapping and differentiating parts of a list of strings.
    The result is a list, alternating between overlapping parts and differentiating parts.
    All even indices in the list are overlapping parts, and always of type 'str'.
    All uneven indices in the list are differentiating parts, and of type 'list(str, ...)', where the first item
    corresponds to additional characters in str1, the second item corresponds to additional characters in str2, etc.
    """
    ndiffs = []
    for idx in range(1, len(input)):
        ndiffs.append(_dmp.diff_main(input[0], input[idx]))

    result = []
    # Then loop over all diffs to gather overlapping and differentiating parts
    while next(filter(len, ndiffs), False):
        if len(result) % 2 == 0:
            # The overlapping part is the shortest string in all overlaps (marked with '0' symbol)
            overlap_len = min(len(diff[0][1]) if diff[0][0] == 0 else 0 for diff in ndiffs)
            # All strings are equal, so just get any overlapping part of said length
            overlap = ndiffs[0][0][1][0:overlap_len]
            if start_only:
                return overlap
            result.append(overlap)
            # Remove the overlapping part from all diffs
            for diff in ndiffs:
                if len(diff[0][1]) > overlap_len:
                    diff[0] = (diff[0][0], diff[0][1][overlap_len:])
                else:
                    diff.pop(0)
        else:
            # First count the longest streak of '0', followed by '+1' or '-1' without '0', and add up the lengths of '0' and '-1' to find the longest part of str0 to follow
            diff_res = [''] * len(input)
            max_streak = 0
            for ndiff in ndiffs:
                streak_len = 0
                diff_found = False
                for tag in ndiff:
                    if tag[0] != 0:
                        diff_found = True
                    elif diff_found:
                        break # end of streak
                    if (tag[0] == 0) or (tag[0] == -1):
                        streak_len = streak_len + len(tag[1])
                max_streak = max(max_streak, streak_len)
            # Build the first 'diff' by appending max_streak '0' or '-1' tags
            # and build the subsequent 'diff' by appending the same '0' and all '+1' tags
            # Stop when the maximum streak is reached, or all diffs are exhausted
            for idx, diff in enumerate(ndiffs):
                diff0 = ''
                diffn = ''
                while diff:
                    tag = diff[0]
                    if tag[0] == 1:
                        # Always append to diffn when possible and remove entire tag
                        diffn += tag[1]
                        diff.pop(0)
                    else:
                        if len(diff0) == max_streak: # We have to stop
                            break
                        streak_remain = max_streak - len(diff0)
                        if len(tag[1]) > streak_remain:
                            # Not the entirety of the tag should be used, use a substring and extract substring from diff
                            strpart = tag[1][:streak_remain]
                            diff[0] = (tag[0], tag[1][streak_remain:])
                        else:
                            strpart = tag[1]
                            diff.pop(0) # Entire tag exhausted, remove it
                        diff0 += strpart
                        if tag[0] == 0: # Matching string, use for both
                            diffn += strpart
                if idx == 0: # First result, just store diff0
                    diff_res[0] = diff0
                elif diff_res[0] != diff0: # Subsequent result, make sure all diff0 matches
                    raise ValueError('Difference in diff0, logic problem')
                diff_res[idx + 1] = diffn
            result.append(diff_res)
    return result
