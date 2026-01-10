_SVD2CPP_VERSION = '1.1'

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

    return device['name'], groups.keys()

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
                    raise Exception("No common prefix found in names: " + ', '.join(names))
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
        'svd2cpp_version': _SVD2CPP_VERSION,
        'device': device,
        'groups': groups,
        'interrupts': sorted(interrupts.values(), key=lambda x: x['value']),
    }

    # Make sure output directory exists
    generate_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generated', device['name'].lower())
    if not os.path.exists(generate_dir):
        print(f'Creating directory {generate_dir}')
        os.makedirs(generate_dir)

    # Copy in license files for distribution
    import shutil
    for license_file in ['LICENSE', 'LICENSE.spdx']:
        shutil.copyfile(license_file, os.path.join(generate_dir, license_file))

    # Generate common template files
    for template_file in os.listdir(os.path.join(template_dir, "common")):
        template_file = os.path.join("common", template_file)
        generated_file = os.path.join(generate_dir, os.path.basename(template_file.removesuffix('.jinja').replace('device', device['name'].lower())))
        print(f'Generating {generated_file}...')
        print(f'Template file: {template_file}')
        rendered = env.get_template(template_file).render(parameters)
        with open(generated_file, 'w') as file:
            file.write(rendered)
    
    # Generate group-specific template files
    for template_file in os.listdir(os.path.join(template_dir, "group")):
        template_file = os.path.join("group", template_file)

        # Generate for each group
        for group_name, group in groups.items():
            generate_base_name = f'{device['name'].lower()}-{os.path.basename(template_file.removesuffix('.jinja').replace('group', group_name.lower()))}'
            generated_file = os.path.join(generate_dir, generate_base_name)
            print(f'Generating {generated_file}...')
            rendered = env.get_template(template_file).render({**parameters, 'group': group})
            
            with open(generated_file, 'w') as file:
                file.write(rendered)

def convert_entries(device_names, group_names):
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

    # Generate list of include files
    svds = [{'filename': name.lower(), 'define': name.upper()} for name in device_names]

    parameters = {
        'svd2cpp_version': _SVD2CPP_VERSION,
        'include_def': '',
        'include_file': '',
        'svds': svds,
    }

    # Detect which common entry files have to be generated
    filenames = [filename for filename in os.listdir(os.path.join(template_dir, "common")) if os.path.basename(filename).startswith('device')]
    
    generate_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generated')
    template_file = os.path.join("entry", "entry.h.jinja")
    for filename in filenames:
        generated_file = os.path.join(generate_dir, filename.removesuffix('.jinja').replace('device-', '').replace('device_', ''))
        base_file = os.path.basename(generated_file)
        include_name = os.path.basename(generated_file).replace('.', '_').replace('-', '_')

        parameters['include_def'] = base_file.replace('.', '_').replace('-', '_')
        parameters['include_file'] = base_file

        print(f'Generating entry common {generated_file}...')
        rendered = env.get_template(template_file).render(parameters)
        with open(generated_file, 'w') as file:
                file.write(rendered)

    # Generate entry files for all groups
    filenames = [f'{group_name.lower()}.hpp' for group_name in group_names]

    group_generate_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'generated', 'group')
    if not os.path.exists(group_generate_dir):
        print(f'Creating directory {group_generate_dir}')
        os.makedirs(group_generate_dir)

    for filename in filenames:
        generated_file = os.path.join(group_generate_dir, filename.removesuffix('.jinja').replace('device-', '').replace('device_', ''))
        base_file = os.path.basename(generated_file)
        include_name = os.path.basename(generated_file).replace('.', '_').replace('-', '_')

        parameters['include_def'] = base_file.replace('.', '_').replace('-', '_')
        parameters['include_file'] = base_file

        print(f'Generating entry group {generated_file}...')
        
        rendered = env.get_template(template_file).render(parameters)
        with open(generated_file, 'w') as file:
                file.write(rendered)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog='svd2cpp', description='Convert CMSIS SVD to modern C++ interfaces')
    parser.add_argument('svd_files', nargs="+", type=str, help='Path to the SVD file to convert')
    parser.add_argument('--ignore_cluster', type=str, help='Regex indicating which clusters to ignore, passed to svd_cleanup', default='')
    args = parser.parse_args()

    device_names = []
    total_group_names = set()
    for svd_file in args.svd_files:
        print('Converting SVD file:', svd_file)

        device_name, group_names = convert(svd_file, args.ignore_cluster)
        device_names.append(device_name)
        total_group_names.update(group_names)

    print("Generating entry files for converted SVD files: ", ', '.join(device_names))
    convert_entries(device_names, total_group_names)

    print()
    print('All done!')
