
# class SVDAccessType(Enum):
#     READ_ONLY = 'read-only'
#     WRITE_ONLY = 'write-only'
#     READ_WRITE = 'read-write'
#     WRITE_ONCE = 'writeOnce'
#     READ_WRITE_ONCE = 'read-writeOnce'

def convert(svd_xml):
    from cmsis_svd import SVDParser

    print(f'Parsing SVD file: {svd_xml}...')
    parser = SVDParser.for_xml_file(svd_xml)
    device = parser.get_device().to_dict()

    grouped_peripherals = {}
    for peripheral in device['peripherals']:
        if peripheral['group_name'] not in grouped_peripherals:
            grouped_peripherals[peripheral['group_name']] = [peripheral]
        else:
            grouped_peripherals[peripheral['group_name']].append(peripheral)

    # show(grouped_peripherals)
    generate(device, grouped_peripherals)

def show(grouped_peripherals):
    for group_name, peripherals in grouped_peripherals.items():
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

def generate(device, grouped_peripherals):
    import os
    import jinja2

    template_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'template')

    env = jinja2.Environment(
        loader = jinja2.FileSystemLoader(template_dir),
        autoescape = jinja2.select_autoescape(),
        trim_blocks = True,
        lstrip_blocks = True,
        keep_trailing_newline=True,
        undefined=jinja2.StrictUndefined
    )

    parameters = {
        'device': {
            'name': device['name'],
            'width': device['width'],
        },
        'groups': grouped_peripherals,
    }

    generate_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generated')
    if not os.path.exists(generate_dir):
        print(f'Creating directory {generate_dir}')
        os.makedirs(generate_dir)

    for template_file in os.listdir(template_dir):
        generated_file = os.path.join(generate_dir, os.path.basename(template_file.removesuffix('.jinja').replace('device', device['name'])))
        print(f'Generating {generated_file}...')
        rendered = env.get_template(os.path.basename(template_file)).render(parameters)
        with open(generated_file, 'w') as file:
            file.write(rendered)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(prog='svd2cpp', description='Convert CMSIS SVD to modern C++ interfaces')
    parser.add_argument('svd_file', type=str, help='Path to the SVD file to convert')
    args = parser.parse_args()

    print('Converting SVD file:', args.svd_file)

    convert(args.svd_file)

    print()
    print('All done!')

                
