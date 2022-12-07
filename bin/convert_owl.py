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
FAVORITE_ONTOLOGY_URLS = {
    'mondo': 'https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.owl',
    'comploinc': 'https://github.com/loinc/comp-loinc/releases/latest/download/merged_reasoned_loinc.owl',
    'hpo': 'https://github.com/obophenotype/human-phenotype-ontology/releases/latest/download/hp-full.owl',
    'rxnorm': 'https://data.bioontology.org/ontologies/RXNORM/submissions/23/download?apikey=8b5b7825-538d-40e0-9e9e-5ab9274a9aeb',
}


# Functions
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


def owl_to_obograph(inpath: str, outpath: str):
    """Convert OWL to Obograph"""
    outdir = os.path.dirname(outpath)
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    # todo: Switch back to `bioontologies` when complete: https://github.com/biopragmatics/bioontologies/issues/9
    # from bioontologies import robot
    # parse_results: robot.ParseResults = robot.convert_to_obograph_local(inpath)
    # graph = parse_results.graph_document.graphs[0]
    args = ['java', '-jar', ROBOT_PATH + '.jar', 'convert', '-i', inpath, '-o', outpath, '--format', 'json']
    result = subprocess.run(args, capture_output=True, text=True)
    stderr, stdout = result.stderr, result.stdout
    if stderr:
        raise RuntimeError(stderr)
    elif stdout and 'error' in stdout or 'ERROR' in stdout:
        raise RuntimeError(stdout)


# TODO: Switch from Obograph intermediary to sqlite so that OAK can use. currently running into obograph error:
#  - https://github.com/linkml/linkml/issues/1156
#  - https://github.com/ontodev/robot/issues/1079
# todo: When https://github.com/INCATools/ontology-access-kit/pull/374 is merged, can add include_all_predicates
def obograph_to_fhir(inpath: str, out_dir: str, out_filename: str = None, include_all_predicates=False):
    """Convert Obograph to FHIR"""
    converter = OboGraphToFHIRConverter()
    converter.curie_converter = curies.Converter.from_prefix_map(get_default_prefix_map())
    gd: GraphDocument = json_loader.load(inpath, target_class=GraphDocument)
    out_path = os.path.join(out_dir, out_filename)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    # converter.dump(gd, out_path, include_all_predicates=True)
    converter.dump(gd, out_path)


def owl_to_fhir(
    input_path_or_url: str, out_dir: str = OUTDIR, out_filename: str = None, predicates_is_a_only=False,
    retain_intermediaries=False
):
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


    # Convert to Obograph
    obograph_path = os.path.join(CACHE_DIR, out_filename.replace('.json', '.obographs.json'))
    owl_to_obograph(input_path, outpath=obograph_path)

    # Convert to FHIR
    obograph_to_fhir(
        inpath=obograph_path,
        out_dir=out_dir,
        out_filename=out_filename,
        include_all_predicates=not predicates_is_a_only)

    # Cleanup
    if not retain_intermediaries:
        os.remove(obograph_path)


def cli():
    """Command line interface."""
    package_description = 'Convert OWL to FHIR.'
    parser = ArgumentParser(description=package_description)
    parser.add_argument('-i', '--input-path-or-url', required=True, help='URL or path to OWL file to convert.')
    parser.add_argument(
        '-o', '--out-dir', required=False, default=OUTDIR, help='The directory where results should be saved.')
    parser.add_argument(
        '-n', '--out-filename', required=False, help='Filename for the primary file converted, e.g. CodeSystem.')
    # todo: When https://github.com/INCATools/ontology-access-kit/pull/374 is merged, can add include_all_predicates
    # parser.add_argument(
    #     '-p', '--predicates-is-a-only', action='store_true', default=False,
    #     help='Include all predicates in CodeSystem.property and CodeSystem.concept.property, or just is_a/parent?')
    # @Shahim: I felt it made sense to invert the 'include-all-predicates' flag for our purposes, but I can keep it
    #   if you want.
    # parser.add_argument('-p', '--include-all-predicates', action='store_true', default=False,
    #     help='Include all predicates in CodeSystem.property and CodeSystem.concept.property, or just is_a/parent?')
    parser.add_argument(
        '-r', '--retain-intermediaries', action='store_true', default=False, required=False,
        help='Retain intermediary files created during conversion process (e.g. Obograph JSON)?')

    kwargs_dict: Dict = vars(parser.parse_args())
    owl_to_fhir(**kwargs_dict)


# Execution
if __name__ == '__main__':
    cli()
