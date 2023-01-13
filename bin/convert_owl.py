"""Convert OWL to FHIR"""
import json
import os
import subprocess
from argparse import ArgumentParser
from typing import Dict

import curies
import requests
from linkml_runtime.loaders import json_loader
from oaklib.converters.obo_graph_to_fhir_converter import OboGraphToFHIRConverter
from oaklib.datamodels.obograph import GraphDocument
from oaklib.interfaces.basic_ontology_interface import get_default_prefix_map
from urllib.parse import urlparse


# Vars
# - Vars: Static
BIN_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.join(BIN_DIR, '..')
CACHE_DIR = os.path.join(PROJECT_DIR, 'cache')
OUTDIR = os.path.join(PROJECT_DIR, 'output')
ROBOT_PATH = os.path.join(BIN_DIR, 'robot')
INTERMEDIARY_TYPES = ['obographs', 'semsql']

# - Vars: Config
# TODO: owl-on-fhir-content needs some configuration / setup instructions, or a git submodule
OWL_ON_FHIR_CONTENT_REPO_PATH = os.path.join(PROJECT_DIR, '..', 'owl-on-fhir-content')
# todo: consider 1+ changes: (i) external config JSON / env vars, (ii) accept overrides from CLI
FAVORITE_DEFAULTS = {
    'out_dir': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'output'),
    'intermediary_outdir': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input'),
    'include_all_predicates': True,
    'intermediary_type': 'obographs',
    'use_cached_intermediaries': True,
    'retain_intermediaries': True,
    'convert_intermediaries_only': True,
}
FAVORITE_ONTOLOGIES = {
    'mondo': {
        'url': 'https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.owl',
        'input_path': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input', 'mondo.owl'),
        'id': 'mondo',
    },
    'comp-loinc': {
        'url': 'https://github.com/loinc/comp-loinc/releases/latest/download/merged_reasoned_loinc.owl',
        'input_path': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input', 'comploinc.owl'),
        'id': 'comp-loinc',
    },
    'HPO': {
        'url': 'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp-full.owl',
        'input_path': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input', 'hpo.owl'),
        'id': 'HPO',
    },
    'rxnorm': {
        'url': 'https://data.bioontology.org/'
               'ontologies/RXNORM/submissions/23/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb',
        'input_path': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input', 'RXNORM.ttl'),
        'id': 'rxnorm',
    },
    'sequence-ontology': {
        'url': 'https://data.bioontology.org/'
               'ontologies/SO/submissions/304/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb',
        'input_path': os.path.join(OWL_ON_FHIR_CONTENT_REPO_PATH, 'input', 'so.owl'),
        'id': 'sequence-ontology',
    },
}


# Functions
def _run_shell_command(command: str, cwd_outdir: str = None) -> subprocess.CompletedProcess:
    """Runs a command in the shell, and handles some common errors"""
    args = command.split(' ')
    if cwd_outdir:
        result = subprocess.run(args, capture_output=True, text=True, cwd=cwd_outdir)
    else:
        result = subprocess.run(args, capture_output=True, text=True)
    stderr, stdout = result.stderr, result.stdout
    if stderr and 'Unable to create a system terminal, creating a dumb terminal' not in stderr:
        raise RuntimeError(stderr)
    elif stdout and 'error' in stdout or 'ERROR' in stdout:
        raise RuntimeError(stdout)
    elif stdout and 'make: Nothing to be done' in stdout:
        raise RuntimeError(stdout)
    elif stdout and ".db' is up to date" in stdout:
        raise FileExistsError(stdout)
    return result


def _preprocess_rxnorm(path: str) -> str:
    """Preprocess RXNORM
    If detects a Bioportal rxnorm TTL, makes some modifications to standardize it to work with OAK, etc.
    See: https://github.com/INCATools/ontology-access-kit/issues/427
    If using --use-cached-intermediaries or --retain-intermediaries, those are used for SemSQL or Obographs
    intermediaries, but not the intermediary created by this function.
    """
    if '-fixed' in path:
        return path
    print('INFO: RXNORM.ttl from Bioportal detected. Doing some preprocessing.')
    outpath = path.replace(".ttl", "-fixed.ttl")
    _run_shell_command(f'cp {path} {outpath}')
    command_str = f'perl -i {os.path.join(BIN_DIR, "convert_owl_ncbo2owl.pl")} {outpath}'
    _run_shell_command(command_str)
    return outpath


def download(url: str, path: str, download_if_cached=True):
    """Download file at url to local path

    :param download_if_cached: If True and file at `path` already exists, download anyway."""
    _dir = os.path.dirname(path)
    if not os.path.exists(_dir):
        os.makedirs(_dir)
    if download_if_cached or not os.path.exists(path):
        with open(path, 'wb') as f:
            response = requests.get(url, verify=False)
            f.write(response.content)


def owl_to_semsql(inpath: str, use_cache=False) -> str:
    """Converts OWL (or RDF, I think) to a SemanticSQL sqlite DB.
    Docs: https://incatools.github.io/ontology-access-kit/intro/tutorial07.html?highlight=semsql
    - Had to change "--rm -ti"  --> "--rm"
    todo: consider using linkml/semantic-sql image which is more up-to-date instead
      https://github.com/INCATools/semantic-sql
      docker run  -v $PWD:/work -w /work -ti linkml/semantic-sql semsql make foo.db
    todo: RDF also supported? not just OWL? (TTL not supported)
    """
    # Vars
    _dir = os.path.dirname(inpath)
    output_filename = os.path.basename(inpath).replace('.owl', '.db').replace('.rdf', '.db').replace('.ttl', '.db')
    outpath = os.path.join(_dir, output_filename)
    command_str = f'docker run -w /work -v {_dir}:/work --rm obolibrary/odkfull:dev semsql make {output_filename}'

    # Convert
    if use_cache and os.path.exists(outpath):
        return outpath
    try:
        _run_shell_command(command_str, cwd_outdir=_dir)
    except FileExistsError:
        if not use_cache:
            os.remove(outpath)
            _run_shell_command(command_str, cwd_outdir=_dir)
    return outpath


def owl_to_obograph(inpath: str, use_cache=False) -> str:
    """Convert OWL to Obograph
    # todo: TTL and RDF also supported? not just OWL?"""
    # Vars
    outpath = os.path.join(CACHE_DIR, inpath + '.obographs.json')
    outdir = os.path.dirname(outpath)
    command = f'java -jar {ROBOT_PATH}.jar convert -i {inpath} -o {outpath} --format json'

    # Convert
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    if use_cache and os.path.exists(outpath):
        return outpath
    # todo: Switch back to `bioontologies` when complete: https://github.com/bioprag    matics/bioontologies/issues/9
    # from bioontologies import robot
    # parse_results: robot.ParseResults = robot.convert_to_obograph_local(inpath)
    # graph = parse_results.graph_document.graphs[0]
    _run_shell_command(command)

    # todo: might want to add this patch back and open up an issue, because nico said in issue below shouldn't happen
    #  - issue would be in OAK, regarding the 'cooked' error
    # Patch missing roots / etc issue (until resolved: https://github.com/ontodev/robot/issues/1082)
    # ! - Deactivated this because I was getting an error about the very same IDs that Chris R was asking for
    #     Try uploading and see if it works.
    #
    # - This appears to be mostly a problem in FHIR (and maybe just Obographs) if subClassOf or variation missing, but
    #   not 100% sure
    #
    # missing_nodes_from_important_edge_preds = [
    #     'is_a',
    #     'http://purl.bioontology.org/ontology/RXNORM/isa',
    #     'rdfs:subClassOf',
    #     'http://www.w3.org/2000/01/rdf-schema#subClassOf'
    # ]
    # with open(outpath, 'r') as f:
    #     data = json.load(f)
    # nodes = data['graphs'][0]['nodes']
    # node_ids = set([node['id'] for node in nodes])
    # edges = data['graphs'][0]['edges']
    # edges = [x for x in edges if x['pred'] in missing_nodes_from_important_edge_preds]
    # edge_subs = set([edge['sub'] for edge in edges])
    # edge_objs = set([edge['obj'] for edge in edges])
    # edge_ids = edge_subs.union(edge_objs)
    # missing = set([x for x in edge_ids if x not in node_ids])

    # Edge case exclusions
    # - This was causing the following error in OAK (I have not made a GH issue):
    # - This example was from Mondo
    # cooked_entry = Node(id="JsonObj(id='http://www.geneontology.org/formats/oboInOwl#Subset')", ...
    #         if cooked_entry[key_name] != key:
    # >           raise ...
    # E           ValueError: Slot: nodes - attribute id value (JsonObj(
    # id='http://www.geneontology.org/formats/oboInOwl#Subset'))
    # does not match key (http://www.geneontology.org/formats/oboInOwl#Subset)
    #
    # Method A: Remove cases
    # id_exclusions = [
    #     'http://www.geneontology.org/formats/oboInOwl#Subset'
    # ]
    # uri_stem_exclusions = [
    #     'http://purl.obolibrary.org/obo/CARO_'
    # ]
    # for case in id_exclusions:
    #     if case in missing:
    #         missing.remove(case)
    # missing2 = []
    # for node_id in missing:
    #     if not any([node_id.startswith(x) for x in uri_stem_exclusions]):
    #         missing2.append(node_id)
    #
    # Method B: Keep only dominant IDs
    # - Opted not to do

    # if missing2:
    #     print(f'INFO: The following nodes were found in Obographs edges, but not nodes. Adding missing declarations: '
    #           f'{missing}')
    #     for node_id in missing:
    #         nodes.append({'id': node_id})
    #     with open(outpath, 'w') as f:
    #         json.dump(data, f)

    return outpath


# todo: This doesn't work until following Obographs issues solved. Moved to semsql intermediary for now.
#  - https://github.com/linkml/linkml/issues/1156
#  - https://github.com/ontodev/robot/issues/1079
#  - https://github.com/geneontology/obographs/issues/89
def obograph_to_fhir(inpath: str, out_dir: str, out_filename: str = None, include_all_predicates=False) -> str:
    """Convert Obograph to FHIR"""
    converter = OboGraphToFHIRConverter()
    converter.curie_converter = curies.Converter.from_prefix_map(get_default_prefix_map())
    gd: GraphDocument = json_loader.load(inpath, target_class=GraphDocument)
    out_path = os.path.join(out_dir, out_filename)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    converter.dump(gd, out_path, include_all_predicates=include_all_predicates)
    return out_path


def semsql_to_fhir(inpath: str, out_dir: str, out_filename: str = None, include_all_predicates=False) -> str:
    """Convert SemanticSQL sqlite DB to FHIR"""
    # todo: any way to do this using Python API?
    # todo: do I need some way of supplying prefix_map? check: are outputs all URIs?
    # converter.curie_converter = curies.Converter.from_prefix_map(get_default_prefix_map())
    out_path = os.path.join(out_dir, out_filename)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    preds_flag = ' --include-all-predicates' if include_all_predicates else ''
    command_str = f'runoak -i sqlite:{inpath} dump -o {out_path} -O fhirjson{preds_flag}'
    _run_shell_command(command_str)
    return out_path  # todo: When OAK changes to save multiple files, return out_dir


def owl_to_fhir(
    input_path_or_url: str, out_dir: str = OUTDIR, out_filename: str = None, include_all_predicates=False,
    retain_intermediaries=False, intermediary_type=['obographs', 'semsql'][0], use_cached_intermediaries=False,
    intermediary_outdir: str = None, convert_intermediaries_only=False
) -> str:
    """Run conversion"""
    # Download if necessary & determine outpaths
    intermediary_outdir = intermediary_outdir if intermediary_outdir else out_dir
    input_path = input_path_or_url
    url = None
    maybe_url = urlparse(input_path_or_url)
    if maybe_url.scheme and maybe_url.netloc:
        url = input_path_or_url
    if not out_filename and not url:
        _id = '.'.join(os.path.basename(input_path).split('.')[0:-1])  # removes file extension
        out_filename = f'CodeSystem-{_id}.json'
    elif not out_filename and url:
        out_filename = 'CodeSystem.json'
    if url:
        input_path = os.path.join(CACHE_DIR, out_filename.replace('.json', '.owl'))
        download(url, input_path)

    # Preprocessing: Special cases
    if 'rxnorm' in input_path.lower() or 'rxnorm' in out_filename.lower():
        input_path = _preprocess_rxnorm(input_path)

    # Convert
    if intermediary_type == 'obographs' or input_path.endswith('.ttl'):  # semsql only supports .owl
        intermediary_path = owl_to_obograph(input_path, use_cached_intermediaries)
        obograph_to_fhir(
            inpath=intermediary_path,
            out_dir=intermediary_outdir,
            out_filename=out_filename,
            include_all_predicates=include_all_predicates)
    else:  # semsql
        intermediary_path = owl_to_semsql(input_path, use_cached_intermediaries)
        semsql_to_fhir(
            inpath=intermediary_path,
            out_dir=intermediary_outdir,
            out_filename=out_filename,
            include_all_predicates=include_all_predicates)
    if convert_intermediaries_only:
        return intermediary_path

    # Cleanup
    indir = os.path.dirname(input_path)
    template_db_path = os.path.join(indir, '.template.db')
    if os.path.exists(template_db_path):
        os.remove(template_db_path)
    if not retain_intermediaries:
        # noinspection PyUnboundLocalVariable
        os.remove(intermediary_path)
        if intermediary_type == 'semsql':
            # More semsql intermediaries
            intermediary_filename = os.path.basename(intermediary_path)
            os.remove(os.path.join(indir, intermediary_filename.replace('.db', '-relation-graph.tsv.gz')))
    return os.path.join(out_dir, out_filename)


def _run_favorites(
    use_cached_intermediaries=FAVORITE_DEFAULTS['use_cached_intermediaries'],
    retain_intermediaries=FAVORITE_DEFAULTS['retain_intermediaries'],
    include_all_predicates=FAVORITE_DEFAULTS['include_all_predicates'],
    intermediary_type=FAVORITE_DEFAULTS['intermediary_type'], out_dir=FAVORITE_DEFAULTS['out_dir'],
    intermediary_outdir=FAVORITE_DEFAULTS['intermediary_outdir'],
    convert_intermediaries_only=FAVORITE_DEFAULTS['convert_intermediaries_only'], favorites: Dict = FAVORITE_ONTOLOGIES
):
    """Convert favorite ontologies"""
    fails = []
    successes = []
    n = len(favorites)
    i = 0
    for d in favorites.values():
        print('Converting {} of {}: {}'.format(i, n, d['id']))
        try:
            owl_to_fhir(
                out_filename=f'CodeSystem-{d["id"]}.json',
                input_path_or_url=d['input_path'] if d['input_path'] else d['url'],
                use_cached_intermediaries=use_cached_intermediaries, retain_intermediaries=retain_intermediaries,
                include_all_predicates=include_all_predicates, intermediary_type=intermediary_type,
                intermediary_outdir=intermediary_outdir, out_dir=out_dir,
                convert_intermediaries_only=convert_intermediaries_only)
            successes.append(d['id'])
        except Exception as e:
            fails.append(d['id'])
            print('Failed to convert {}: \n{}'.format(d['id'], e))
    print('SUMMARY')
    print('Successes: ' + str(successes))
    print('Failures: ' + str(fails))


def cli():
    """Command line interface."""
    package_description = 'Convert OWL to FHIR.'
    parser = ArgumentParser(description=package_description)
    parser.add_argument('-i', '--input-path-or-url', required=False, help='URL or path to OWL file to convert.')
    parser.add_argument(
        '-o', '--out-dir', required=False, default=OUTDIR, help='The directory where results should be saved.')
    parser.add_argument(
        '-n', '--out-filename', required=False, help='Filename for the primary file converted, e.g. CodeSystem.')
    parser.add_argument(
        '-p', '--include-all-predicates', action='store_true', required=False, default=False,
        help='Include all predicates in CodeSystem.property and CodeSystem.concept.property, or just is_a/parent?')
    parser.add_argument(
        '-t', '--intermediary-type', choices=INTERMEDIARY_TYPES, default='obographs', required=False,
        help='Which type of intermediary to use? First, we convert OWL to that intermediary format, and then we '
             'convert that to FHIR.')
    parser.add_argument(
        '-c', '--use-cached-intermediaries', action='store_true', required=False, default=False,
        help='Use cached intermediaries if they exist?')
    parser.add_argument(
        '-r', '--retain-intermediaries', action='store_true', default=False, required=False,
        help='Retain intermediary files created during conversion process (e.g. Obograph JSON)?')
    parser.add_argument(
        '-I', '--convert-intermediaries-only', action='store_true', default=False, required=False,
        help='Convert intermediaries only?')
    parser.add_argument(
        '-f', '--favorites', action='store_true', default=False, required=False,
        help='If present, will run all favorite ontologies found in `FAVORITE_ONTOLOGIES`. If using this option, the '
             'other CLI flags are not relevant. Instead, edit the following config: `FAVORITE_DEFAULTS`.')

    d: Dict = vars(parser.parse_args())
    if d['favorites']:
        _run_favorites(**{**FAVORITE_DEFAULTS, **{'favorites': FAVORITE_ONTOLOGIES}})
    owl_to_fhir(**d)


# Execution
if __name__ == '__main__':
    cli()
