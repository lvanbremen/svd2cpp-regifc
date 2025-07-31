
# class SVDAccessType(Enum):
#     READ_ONLY = 'read-only'
#     WRITE_ONLY = 'write-only'
#     READ_WRITE = 'read-write'
#     WRITE_ONCE = 'writeOnce'
#     READ_WRITE_ONCE = 'read-writeOnce'

if __name__ == "__main__":
    from cmsis_svd import SVDParser

    parser = SVDParser.for_xml_file('STM32U595.svd')
    device = parser.get_device().to_dict()
    print(device['name'], device['width'])

    groups = {}
    for peripheral in device['peripherals']:
        if peripheral['group_name'] not in groups:
            groups[peripheral['group_name']] = [peripheral]
        else:
            groups[peripheral['group_name']].append(peripheral)

    for group_name, peripherals in groups.items():
        print(f'Group: {group_name}')
        for idx, peripheral in enumerate(peripherals):
            # Only generate the registers once per group
            if idx == 0:
                for register in peripheral['registers']:
                    # TODO: if 'derived_from' is set, then don't generate a new interface, just generate the accessor functions, or group peripherals by group_name
                    # register.display_name: register.description TODO strip newlines and duplicate whitespace characters
                    print('    ', register['name'], register['size'], register['reset_value'], register['access'])
                    for field in register['fields']:
                        if field['access'] not in ['read-only', 'write-only', 'read-write']:
                            print(f'Unsupported accessor "{field['access']}" for field "{field['name']}" of register "{register['name']}" of peripheral "{peripheral['name']}"')
                            exit(0)

                        # TODO: check SVDAccessType
                        # field.name: field.description TODO strip newlines and duplicate whitespace characters
                        print('      ', field['name'], field['bit_offset'], field['bit_width'], field['access'])
                        # if field['is_enumerated_type']:
                        #     # Note, enumerated values could be added to the interface, but the contents in the STM SVD files is worthless...
                        #     enumerated_values = field['enumerated_values'][0]['enumerated_values']
                            # for enum_val in enumerated_values:
                            #     print('        ', enum_val['name'], enum_val['value'], enum_val['description'])

            # List all peripherals belonging to this group
            print('  ', peripheral['name'], peripheral['base_address'])
                
