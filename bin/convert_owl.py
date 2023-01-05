"""Convert OWL to FHIR"""
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
BIN_DIR = os.path.dirname(os.path.realpath(__file__))
PROJECT_DIR = os.path.join(BIN_DIR, '..')
CACHE_DIR = os.path.join(PROJECT_DIR, 'cache')
OUTDIR = os.path.join(PROJECT_DIR, 'output')
ROBOT_PATH = os.path.join(BIN_DIR, 'robot')
INTERMEDIARY_TYPES = ['obographs', 'semsql']
FAVORITE_ONTOLOGY_URLS = {
    'mondo': 'https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.owl',
    'comploinc': 'https://github.com/loinc/comp-loinc/releases/latest/download/merged_reasoned_loinc.owl',
    'hpo': 'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp-full.owl',
    'rxnorm': 'https://data.bioontology.org/'
              'ontologies/RXNORM/submissions/23/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb',
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
    # todo: Switch back to `bioontologies` when complete: https://github.com/biopragmatics/bioontologies/issues/9
    # from bioontologies import robot
    # parse_results: robot.ParseResults = robot.convert_to_obograph_local(inpath)
    # graph = parse_results.graph_document.graphs[0]
    _run_shell_command(command)

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
    retain_intermediaries=False, intermediary_type=['obographs', 'semsql'][0], use_cached_intermediaries=False
) -> str:
    """Run conversion"""
    # Download if necessary & determine outpath
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
            out_dir=out_dir,
            out_filename=out_filename,
            include_all_predicates=include_all_predicates)
    elif intermediary_type == 'semsql':
        intermediary_path = owl_to_semsql(input_path, use_cached_intermediaries)
        semsql_to_fhir(
            inpath=intermediary_path,
            out_dir=out_dir,
            out_filename=out_filename,
            include_all_predicates=include_all_predicates)

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


def cli():
    """Command line interface."""
    package_description = 'Convert OWL to FHIR.'
    parser = ArgumentParser(description=package_description)
    parser.add_argument('-i', '--input-path-or-url', required=True, help='URL or path to OWL file to convert.')
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

    kwargs_dict: Dict = vars(parser.parse_args())
    owl_to_fhir(**kwargs_dict)


# Execution
if __name__ == '__main__':
    cli()
