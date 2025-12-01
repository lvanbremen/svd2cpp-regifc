
def convert(svd_file, ignore_cluster_regex):
    import svd_cleanup

    print(f'Parsing SVD file: {svd_file}...')
    device = svd_cleanup.parse_svd(svd_file)

    # Group, clean and cluster registers
    groups = svd_cleanup.group_peripherals(device)
    svd_cleanup.simplify_registers(groups)
    svd_cleanup.clean_registers(groups)
    svd_cleanup.cluster_registers(groups, ignore_cluster_regex)
    # Indicate that the device file has been modified
    device['description'] = svd_cleanup.clean_description(device['description']) + f', cleaned and clustered by svd_cleanup with arguments "--ignore_cluster \'{ignore_cluster_regex}\'"'
    interrupts = list_interrupts(device)

    # TODO: update generate to accomodate for:
    # - Allow a subset of registers to be clustered, and generate the overlapping registers, e.g., if the first register in the cluster has an additional 'enable' bit
    # - Check SVDAccessType and maybe improve the register interface based on that (e.g., read-only fields do not get the 'write()' function)
    generate(device, groups, interrupts)

def list_interrupts(device):
    # List all interrupts to be able to sort them
    interrupts = {}
    for peripheral in device['peripherals']:
        if peripheral['interrupts']:
            for interrupt in peripheral['interrupts']:
                interrupts[interrupt['value']] = {'name': interrupt['name'], 'value': interrupt['value'], 'description': ' '.join(list(filter(len, interrupt['description'].split())))}
    return interrupts

def generate(device, groups, interrupts):
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

    def cvar(var_name):
        import re
        var_name = re.sub('[^A-Za-z0-9_]+', '_', str(var_name))
        if var_name[0].isdigit():
            var_name = '_' + var_name
        return var_name
    env.filters["cvar"] = cvar

    def raise_helper(msg):
        raise Exception(msg)
    env.globals['raise'] = raise_helper

    def find_common_prefix(names):
        if not names:
            return '', []

        prefix = names[0]
        for name in names[1:]:
            while not name.startswith(prefix):
                prefix = prefix[:-1]
                if not prefix:
                    raise Exception("No common prefix found")
        prefix = prefix.rstrip('_')
        
        stripped_names = []
        for name in names:
            stripped_name = name[len(prefix):].lstrip('_')
            # if the stripped name starts with a digit, prefix with underscore
            if (stripped_name[0].isdigit()):
                stripped_name = '_' + stripped_name
            stripped_names.append(stripped_name)
        print(f'Common prefix: "{prefix}" for names: {names} -> stripped names: {stripped_names}')
        return prefix, stripped_names
    env.globals['find_common_prefix'] = find_common_prefix

    parameters = {
        'device': device,
        'groups': groups,
        'interrupts': sorted(interrupts.values(), key=lambda x: x['value']),
    }

    # Make sure output directory exists
    generate_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generated')
    if not os.path.exists(generate_dir):
        print(f'Creating directory {generate_dir}')
        os.makedirs(generate_dir)

    # Copy in license files for distribution
    import shutil
    for license_file in ['LICENSE', 'LICENSE.spdx']:
        shutil.copyfile(license_file, os.path.join(generate_dir, license_file))

    # Generate template files
    for template_file in os.listdir(template_dir):
        generated_file = os.path.join(generate_dir, os.path.basename(template_file.removesuffix('.jinja').replace('device', device['name'].lower())))
        print(f'Generating {generated_file}...')
        rendered = env.get_template(os.path.basename(template_file)).render(parameters)
        with open(generated_file, 'w') as file:
            file.write(rendered)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(prog='svd2cpp', description='Convert CMSIS SVD to modern C++ interfaces')
    parser.add_argument('svd_file', type=str, help='Path to the SVD file to convert')
    parser.add_argument('--ignore_cluster', type=str, help='Regex indicating which clusters to ignore, passed to svd_cleanup', default='')
    args = parser.parse_args()

    print('Converting SVD file:', args.svd_file)

    convert(args.svd_file, args.ignore_cluster)

    print()
    print('All done!')

                
